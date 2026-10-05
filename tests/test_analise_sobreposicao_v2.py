"""Limites metodológicos e preservação das entradas da segunda versão."""

import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

from scripts import analise_sobreposicao_v2 as analysis
from scripts.gerar_notebook_sobreposicao_v2 import ROOT, analysis_source, payload_bytes


class DimensionsTests(unittest.TestCase):
    def sample(self):
        return pd.DataFrame({
            "codigo_ibge_6": [f"11000{i}" for i in range(8)],
            "municipio": [f"Município {i}" for i in range(8)], "uf": "RO", "regiao": "Norte",
            "ivs": [0.5] * 8, "idhm": [0.5] * 8,
            "familias_cadinsan": [100] * 8,
            "cadinsan_pct_com_PBF": [80.0] * 8, "cadinsan_pct_sem_PBF": [90.0] * 8,
            "cadinsan_pct_com_PBF_arquivo": [80.0] * 8,
            "cadinsan_pct_sem_PBF_arquivo": [90.0] * 8,
            "cadinsan_n_com_PBF": [80] * 8, "cadinsan_n_sem_PBF": [90] * 8,
            "avaliados_altura": [20] * 8, "dai_pct": [6.7] * 8,
            "avaliados_peso": [20] * 8, "dpi_pct": [1.8] * 8,
        })

    def test_default_thresholds_and_separate_social_dimension(self):
        result, cuts = analysis.classify(self.sample())
        self.assertTrue(result.convergencia_total.all())
        self.assertTrue(result.n_dimensoes_desfavoraveis.eq(3).all())
        self.assertTrue(result.nutricional_mapa_insan.all())
        indexed = cuts.set_index("indicador")
        self.assertEqual(indexed.loc["dai", "corte"], 6.7)
        self.assertEqual(indexed.loc["dpi", "corte"], 1.8)
        self.assertNotIn("quantil", indexed.loc["dai", "metodo"])
        self.assertEqual(result.minimo_avaliados.unique().tolist(), [20])

    def test_boundaries(self):
        frame = self.sample()
        frame.loc[0, "ivs"] = 0.400
        frame.loc[1, "ivs"] = 0.401
        frame.loc[2, "idhm"] = 0.600
        frame.loc[3, "dai_pct"] = 6.699
        frame.loc[4, "avaliados_altura"] = 19
        frame.loc[5, "avaliados_peso"] = 19
        frame.loc[6, "dpi_pct"] = 1.799
        result, _ = analysis.classify(frame)
        self.assertFalse(result.loc[0, "dim_social"])
        self.assertTrue(result.loc[1, "dim_social"])
        self.assertFalse(result.loc[2, "dim_social"])
        self.assertFalse(result.loc[3, "dim_nutricional"])
        self.assertTrue(pd.isna(result.loc[4, "dim_nutricional"]))
        self.assertEqual(result.loc[4, "classe_prioridade"], "dados insuficientes")
        self.assertTrue(result.loc[5, "convergencia_total"])
        self.assertTrue(pd.isna(result.loc[5, "nutricional_mapa_insan"]))
        self.assertFalse(result.loc[6, "nutricional_mapa_insan"])

    def test_missing_values_never_become_zero_or_low_risk(self):
        frame = self.sample()
        for i, col in enumerate(["ivs", "idhm", "cadinsan_pct_com_PBF", "dai_pct", "avaliados_altura"]):
            frame.loc[i, col] = np.nan
        frame.loc[5, "dpi_pct"] = np.nan
        frame.loc[0, "idhm"] = 0.9  # Mesmo com outro critério falso, dimensão incompleta é ausente.
        result, _ = analysis.classify(frame)
        self.assertTrue(result.loc[:4, "n_dimensoes_desfavoraveis"].isna().all())
        self.assertTrue(result.loc[:4, "convergencia_total"].isna().all())
        self.assertTrue(result.loc[:4, "classe_prioridade"].eq("dados insuficientes").all())
        self.assertTrue(pd.isna(result.loc[0, "dim_social"]))
        self.assertTrue(result.loc[5, "convergencia_total"])
        self.assertEqual(result.loc[5, "dpi_status"], "dados insuficientes")

    def test_all_four_dimension_counts_and_social_status(self):
        frame = self.sample()
        frame["cadinsan_pct_com_PBF"] = [0, 0, 0, 100, 0, 0, 0, 100]
        frame.loc[:1, "ivs"] = 0.2
        frame.loc[0, "dai_pct"] = 0
        result, _ = analysis.classify(frame)
        self.assertEqual(result.loc[:3, "n_dimensoes_desfavoraveis"].tolist(), [0, 1, 2, 3])
        self.assertEqual(result.loc[0, "social_status"], "apenas IDHM desfavorável")
        self.assertEqual(result.loc[3, "social_status"], "ambos desfavoráveis")

    def test_oms_exact_boundaries_and_small_denominators(self):
        frame = self.sample()
        frame["dai_pct"] = [0, 2.499, 2.5, 9.999, 10, 20, 30, 100]
        result, _ = analysis.classify(frame)
        self.assertEqual(result.dai_categoria_oms.tolist(),
                         ["muito baixa", "muito baixa", "baixa", "baixa", "média", "alta", "muito alta", "muito alta"])
        frame.loc[0, "avaliados_altura"] = 19
        frame.loc[1, "dai_pct"] = np.nan
        result, _ = analysis.classify(frame)
        self.assertTrue(result.loc[:1, "dai_categoria_oms"].eq("dados insuficientes").all())

    def test_cadinsan_quantile_is_national_not_social_subset(self):
        frame = self.sample()
        frame["cadinsan_pct_com_PBF"] = np.arange(8) * 10.0
        frame.loc[7, "ivs"] = 0.1
        _, cuts = analysis.classify(frame)
        self.assertEqual(cuts.set_index("indicador").loc["cadinsan", "corte"], 52.5)

    def test_sensitivity_main_row_and_minimum_transitions(self):
        frame = self.sample()
        frame["avaliados_altura"] = [20, 49, 50, 99, 100, 200, 300, 400]
        reference, _ = analysis.classify(frame)
        table, stability = analysis.sensitivity(frame, reference)
        self.assertEqual(len(table), 72)
        rows = table.loc[table.cenario.eq("com_PBF") & table.quantil.eq(0.75) & table.referencia_dai.eq("6.7")]
        self.assertEqual(rows.convergencia_total.tolist(), [8, 6, 4])
        self.assertEqual(rows.saem_vs_principal.tolist(), [0, 2, 4])
        self.assertEqual(rows.entram_vs_principal.tolist(), [0, 0, 0])
        self.assertTrue(stability.cenarios_testados.eq(72).all())

    def test_invalid_parameters_fail(self):
        for kwargs in [{"quantile": 1}, {"min_evaluated": 0}, {"min_evaluated": 20.5},
                       {"scenario": "bad"}, {"dai_cutoff": -1}, {"dpi_cutoff": float("nan")}]:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                analysis.classify(self.sample(), **kwargs)


class RealInputsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.directory = Path(cls.temporary.name)
        cls.payload = payload_bytes()
        with zipfile.ZipFile(io.BytesIO(cls.payload)) as archive:
            archive.extractall(cls.directory)
            cls.members = archive.namelist()
        cls.base, cls.audit, cls.hashes = analysis.prepare_base(cls.directory)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def test_no_person_count_dataset_or_columns(self):
        self.assertFalse(any("cadunico" in m.lower() for m in self.members))
        self.assertFalse(any("cadunico" in c.lower() for c in self.base))
        self.assertEqual(len(self.base), 5571)
        self.assertEqual(len(self.hashes), 4)
        self.assertEqual(set(self.audit.fonte), set(analysis.DATA_FILES))

    def test_embedded_inputs_are_exact_and_catalogue_is_explicit_extract(self):
        for source, relative in analysis.DATA_FILES.items():
            path = ROOT / "dados/pesquisa" / relative
            if source == "sisvan_peso":
                path = ROOT / "dados/tratados/sisvan/peso_por_idade" / Path(relative).name
            self.assertEqual((self.directory / relative).read_bytes(), path.read_bytes())
        report, _ = analysis.validate_catalogue(self.directory / "documentacao/dataset_catalogue.json", self.directory)
        self.assertEqual(len(report), 2)
        catalogue = json.loads((self.directory / "documentacao/dataset_catalogue.json").read_text())
        self.assertEqual(set(catalogue["datasets"]), {"municipios_ivs", "municipios_cadinsan"})
        self.assertIn("catalogo_original_sha256", catalogue["extrato"])

    def test_formulas_and_missingness(self):
        self.assertTrue(np.allclose(self.base.dai_pct.dropna(),
                                   (100 * self.base.dai_n / self.base.avaliados_altura).dropna()))
        self.assertTrue(np.allclose(self.base.dpi_pct.dropna(),
                                   (100 * self.base.dpi_n / self.base.avaliados_peso).dropna()))
        self.assertTrue(self.base.loc[self.base.avaliados_peso.eq(0), "dpi_pct"].isna().all())
        result, _ = analysis.classify(self.base)
        self.assertTrue(result.loc[~result.elegivel_principal, "n_dimensoes_desfavoraveis"].isna().all())

    def test_height_results_remain_equal_to_v1(self):
        from scripts.analise_sobreposicao import prepare_base
        original, _, _ = prepare_base(ROOT / "dados/pesquisa")
        for column in ["codigo_ibge_6", "avaliados_altura", "altura_muito_baixa_n", "altura_baixa_n", "dai_pct"]:
            pd.testing.assert_series_equal(original[column], self.base[column])

    def test_embedded_analysis_executes_without_project_imports(self):
        source = analysis_source()
        self.assertNotIn("from scripts", source)
        self.assertNotIn("municipios-cadunico.json", source)
        namespace = {}
        exec(compile(source, "<v2-autocontida>", "exec"), namespace)
        embedded, _, _ = namespace["prepare_base"](self.directory)
        pd.testing.assert_frame_equal(embedded, self.base)


if __name__ == "__main__":
    unittest.main()
