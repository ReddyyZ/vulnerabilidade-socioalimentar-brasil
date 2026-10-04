import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from formatacao_tabelas import contagem_br, numero_br, percentual_br, tabela_br


class BrazilianDisplayTests(unittest.TestCase):
    def test_separators_precision_and_missing_values(self):
        self.assertEqual(contagem_br(9486.0), "9.486")
        self.assertEqual(contagem_br(223.0), "223")
        self.assertEqual(contagem_br(0), "0")
        self.assertEqual(contagem_br(7846413), "7.846.413")
        self.assertEqual(numero_br(0.401), "0,401")
        self.assertEqual(percentual_br(26.856123), "26,86%")
        self.assertEqual(percentual_br(0), "0,00%")
        for missing in (np.nan, pd.NA, None):
            self.assertEqual(numero_br(missing), "—")
            self.assertEqual(percentual_br(missing), "—")

    def test_display_preserves_data_types_precision_and_csv_bytes(self):
        frame = pd.DataFrame({
            "Código IBGE": ["001234", "510183"],
            "Município": ["ASSIS BRASIL", "<b>nome</b>"],
            "IVS": [0.40112345, np.nan], "IDHM": [0.59998765, np.nan],
            "CadInsan (%)": [14.87654321, np.nan], "DAI (%)": [26.85612345, np.nan],
            "Pessoas no CadÚnico — jun/2026": [9486.0, np.nan],
            "Famílias em risco estimado — jan/2025": [223.0, np.nan],
            "avaliados_altura": [1158.0, 0.0],
            "criterio_dai": pd.Series([True, pd.NA], dtype="boolean"),
        })
        original = frame.copy(deep=True)
        csv_before = frame.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
        styled = tabela_br(frame)
        html = styled.to_html()
        self.assertIs(styled.data, frame)
        pd.testing.assert_frame_equal(frame, original)
        self.assertEqual(frame.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig"), csv_before)
        for text in (">9.486</td>", ">223</td>", ">1.158</td>", ">0,401</td>",
                     ">0,600</td>", ">14,88%</td>", ">26,86%</td>", ">—</td>",
                     ">001234</td>", ">True</td>", "&lt;b&gt;nome&lt;/b&gt;"):
            self.assertIn(text, html)
        self.assertNotIn("9486.000", html)

    def test_threshold_column_uses_units_of_each_indicator(self):
        frame = pd.DataFrame({
            "indicador": ["ivs", "cadinsan", "dai", "idhm"],
            "corte": [0.401, 10.969776400916132, 12.380572037121558, 0.600],
            "percentil": [None, 75.0, 75.0, None],
            "municipios_referencia": [5565, 5570, 5331, 5565],
        }, index=[2, 4, 9, 14])
        original = frame.copy(deep=True)
        html = tabela_br(frame).to_html()
        for text in (">0,401</td>", ">10,97%</td>", ">12,38%</td>", ">0,600</td>",
                     ">75</td>", ">5.331</td>", ">—</td>"):
            self.assertIn(text, html)
        pd.testing.assert_frame_equal(frame, original)

    def test_ratios_are_not_percentages_and_regional_counts_are_integers(self):
        frame = pd.DataFrame({
            "quantil": [0.75], "jaccard_principal": [0.987123],
            "fracao_cenarios_selecionado": [0.833333], "dai_n": [877708.0],
            "avaliados_altura": [7846413.0], "dai_pct_agregado": [11.1861066],
            "pct_prioritarios_entre_elegiveis": [4.54374765],
        })
        html = tabela_br(frame).to_html()
        for text in (">0,75</td>", ">0,987</td>", ">0,833</td>", ">877.708</td>",
                     ">7.846.413</td>", ">11,19%</td>", ">4,54%</td>"):
            self.assertIn(text, html)

    def test_empty_table_still_renders(self):
        frame = pd.DataFrame({"indicador": pd.Series(dtype="string"),
                              "corte": pd.Series(dtype="float64")})
        self.assertIn("<table", tabela_br(frame).to_html())

    def test_notebook_embeds_the_formatter_without_changing_analysis_code(self):
        import nbformat
        import hashlib
        notebook = nbformat.read(ROOT / "notebooks/01_sobreposicao_criterios.ipynb", as_version=4)
        code = [cell.source for cell in notebook.cells if cell.cell_type == "code"]
        formatter = (ROOT / "scripts/formatacao_tabelas.py").read_text()
        self.assertTrue(any(formatter in source for source in code))
        analysis_code = (ROOT / "scripts/analise_sobreposicao.py").read_text()
        self.assertTrue(any(analysis_code.strip() in source for source in code))
        digest = hashlib.sha256(analysis_code.encode("utf-8")).hexdigest()
        self.assertTrue(any(f'CODIGO_ANALISE_SHA256 = "{digest}"' in source for source in code))
        section = next(source for source in code if "indicadores_selecao =" in source)
        self.assertIn("display(tabela_br(caracterizacao_municipios.head(30)))", section)
        self.assertNotIn("display.float_format", "\n".join(code))


if __name__ == "__main__":
    unittest.main()
