"""Ajustes v3: conjunção nutricional, ausência explícita e preservação da v2."""

import hashlib
import io
import tempfile
import unittest
import zipfile

import nbformat
import numpy as np
import pandas as pd

from scripts import analise_sobreposicao_v2 as v2
from scripts import analise_sobreposicao_v3 as analysis
from scripts.gerar_notebook_sobreposicao_v2 import payload_bytes
from scripts.gerar_notebook_sobreposicao_v3 import ROOT, ORIGINAL, NOTEBOOK, analysis_source, build
from tests import test_analise_sobreposicao_v2 as fixtures


class CombinedDimensionTests(unittest.TestCase):
    sample = fixtures.DimensionsTests.sample

    def test_exact_boundaries(self):
        frame = self.sample()
        frame.loc[0, "dpi_pct"] = 1.799
        frame.loc[1, "dai_pct"] = 6.699
        frame.loc[2, "avaliados_peso"] = 19
        frame.loc[3, "avaliados_altura"] = 19
        frame.loc[4, "idhm"] = 0.600
        frame.loc[5, "ivs"] = 0.400
        result, cuts = analysis.classify(frame)
        self.assertFalse(result.loc[0, "dim_nutricional"])
        self.assertTrue(result.loc[0, "dim_nutricional_dai"])
        self.assertTrue(result.loc[0, "convergencia_total_dai"])
        self.assertFalse(result.loc[0, "convergencia_total"])
        self.assertFalse(result.loc[1, "dim_nutricional"])
        self.assertTrue(result.loc[2:3, "dim_nutricional"].isna().all())
        self.assertTrue(result.loc[2, "convergencia_total_dai"])
        self.assertTrue(result.loc[2:3, "convergencia_total"].isna().all())
        self.assertFalse(result.loc[4:5, "dim_social"].any())
        self.assertTrue(result.loc[6:, "convergencia_total"].all())
        self.assertEqual(cuts.set_index("indicador").loc["dpi", "corte"], 1.8)

    def test_missing_even_with_other_component_negative(self):
        frame = self.sample()
        for i, column in enumerate(["dai_pct", "dpi_pct", "avaliados_altura", "avaliados_peso",
                                     "ivs", "idhm", "cadinsan_pct_com_PBF"]):
            frame.loc[i, column] = np.nan
        frame.loc[0, "dpi_pct"] = 0
        frame.loc[1, "dai_pct"] = 0
        frame.loc[4, "idhm"] = 0.9
        result, _ = analysis.classify(frame)
        self.assertTrue(result.loc[:6, "convergencia_total"].isna().all())
        self.assertTrue(result.loc[:6, "n_dimensoes_desfavoraveis"].isna().all())
        self.assertTrue(result.loc[:6, "classe_convergencia"].eq("dados insuficientes").all())
        self.assertTrue(result.loc[:3, "dim_nutricional"].isna().all())
        self.assertTrue(result.loc[:6, "motivo_nao_classificacao"].str.len().gt(0).all())
        self.assertTrue(pd.isna(result.loc[4, "dim_social"]))

    def test_classes_zero_to_three_and_no_normative_labels(self):
        frame = self.sample()
        frame["cadinsan_pct_com_PBF"] = [0, 0, 0, 100, 0, 0, 0, 100]
        frame.loc[:1, "ivs"] = 0.2
        frame.loc[0, "dpi_pct"] = 0
        result, _ = analysis.classify(frame)
        self.assertEqual(result.loc[:3, "n_dimensoes_desfavoraveis"].tolist(), [0, 1, 2, 3])
        self.assertEqual(result.loc[:3, "classe_convergencia"].tolist(), list(analysis.CONVERGENCE_LABELS.values()))
        self.assertFalse(any("prioridade" in c for c in result))

    def test_nullable_missing_denominators_never_raise_or_turn_negative(self):
        frame = self.sample()
        for column in ["avaliados_altura", "avaliados_peso", "familias_cadinsan"]:
            frame[column] = frame[column].astype("Int64")
        frame.loc[0, "avaliados_altura"] = pd.NA
        frame.loc[1, "avaliados_peso"] = pd.NA
        frame.loc[2, "familias_cadinsan"] = pd.NA
        result, _ = analysis.classify(frame)
        self.assertTrue(result.loc[:2, "convergencia_total"].isna().all())
        self.assertTrue(result.loc[:2, "motivo_nao_classificacao"].str.len().gt(0).all())

    def test_sensitivity_both_minima_and_alternative(self):
        frame = self.sample()
        frame["avaliados_peso"] = [20, 49, 50, 99, 100, 200, 300, 400]
        frame["avaliados_altura"] = 400
        reference, _ = analysis.classify(frame)
        table, stability = analysis.sensitivity(frame, reference)
        self.assertEqual(len(table), 72)
        rows = table.loc[table.cenario.eq("com_PBF") & table.quantil.eq(0.75) & table.referencia_dai.eq("6.7")]
        self.assertEqual(rows.convergencia_total.tolist(), [8, 6, 4])
        self.assertEqual(rows.convergencia_total_dai.tolist(), [8, 8, 8])
        self.assertEqual(rows.saem_vs_principal.tolist(), [0, 2, 4])
        self.assertTrue(table.corte_dpi_pct.eq(1.8).all())
        self.assertTrue(stability.cenarios_testados.eq(72).all())

    def test_custom_dpi_cut_propagates_to_sensitivity_and_rounding(self):
        frame = self.sample()
        frame.loc[:3, "dpi_pct"] = 2.9
        frame.loc[4:, "dpi_pct"] = 3.0
        reference, _ = analysis.classify(frame, dpi_cutoff=3.0)
        table, _ = analysis.sensitivity(frame, reference, quantiles=[0.75], minima=[20],
                                         scenarios=["com_PBF"], dai_cuts=[6.7], dpi_cutoff=3.0)
        comparison, _ = analysis.compare_rounding(frame, reference, dpi_cutoff=3.0)
        self.assertEqual(table.convergencia_total.tolist(), [4])
        self.assertEqual(int(comparison.selecionado_percentual_csv.sum()), 4)

    def test_comparison_common_universe(self):
        frame = self.sample()
        frame.loc[0, "dpi_pct"] = 0
        frame.loc[1, "dpi_pct"] = np.nan
        result, _ = analysis.classify(frame)
        table = analysis.nutrition_comparison(result)
        self.assertEqual(table.dai_isolado.tolist(), [8, 7])
        self.assertEqual(table.dai_e_dpi.tolist(), [6, 6])
        self.assertEqual(table.convergencia_dai.tolist(), [8, 7])
        self.assertEqual(table.convergencia_dai_dpi.tolist(), [6, 6])


class PreservationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from pathlib import Path
        cls.temporary = tempfile.TemporaryDirectory()
        cls.directory = Path(cls.temporary.name)
        with zipfile.ZipFile(io.BytesIO(payload_bytes())) as archive:
            archive.extractall(cls.directory)
        cls.base, _, _ = analysis.prepare_base(cls.directory)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def test_new_primary_equals_previous_combined_and_alternative_equals_v2(self):
        before, _ = v2.classify(self.base)
        after, _ = analysis.classify(self.base)
        pd.testing.assert_series_equal(before.convergencia_total_dai_dpi, after.convergencia_total, check_names=False)
        pd.testing.assert_series_equal(before.convergencia_total, after.convergencia_total_dai, check_names=False)
        self.assertEqual(int(after.convergencia_total.sum()), 508)
        self.assertEqual(int(after.convergencia_total_dai.sum()), 548)
        self.assertEqual(int(after.elegivel_principal.sum()), 5561)
        self.assertEqual(len(self.base), 5571)

    def test_embedded_code_and_payload_preserved(self):
        namespace = {}
        source = analysis_source()
        self.assertNotIn("from scripts", source)
        self.assertNotIn("prioridade", source.lower())
        exec(compile(source, "<v3-autossuficiente>", "exec"), namespace)
        embedded, _, _ = namespace["prepare_base"](self.directory)
        pd.testing.assert_frame_equal(self.base, embedded)
        a, _ = analysis.classify(self.base)
        b, _ = namespace["classify"](embedded)
        pd.testing.assert_frame_equal(a, b)

    def test_generator_preserves_v2_and_untouched_cells(self):
        before = hashlib.sha256(ORIGINAL.read_bytes()).hexdigest()
        # Não apaga outputs de um notebook já executado ao testar o gerador.
        existing = NOTEBOOK.read_bytes() if NOTEBOOK.exists() else None
        try:
            build()
            previous = nbformat.read(ORIGINAL, 4)
            new = nbformat.read(NOTEBOOK, 4)
            self.assertEqual(len(previous.cells), len(new.cells))
            self.assertEqual(previous.cells[6].source, new.cells[6].source)
            for i in [1, 4, 11, 12, 17, 20, 22, 27, 29]:
                self.assertEqual(previous.cells[i].source, new.cells[i].source)
            self.assertEqual(before, hashlib.sha256(ORIGINAL.read_bytes()).hexdigest())
            self.assertFalse(any("prioridade alta" in c.source.lower() for c in new.cells))
        finally:
            if existing is not None:
                # Notebook é um artefato gerado; restauração mecânica para preservar outputs.
                NOTEBOOK.write_bytes(existing)


if __name__ == "__main__":
    unittest.main()
