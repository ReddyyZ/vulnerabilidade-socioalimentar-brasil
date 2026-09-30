import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from openpyxl import Workbook

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import coletar_sisvan as collector
import coletar_sisvan_derivado as helper


class SisvanCollectorTests(unittest.TestCase):
    def workbook(self, indicator, counts):
        book = Workbook()
        sheet = book.active
        sheet.cell(6, 1, indicator.official_title)
        width = 5 + 2 * len(indicator.categories) + 1
        offset = width
        for column, label in enumerate(collector.BASE_COLUMNS, offset + 1):
            sheet.cell(7, column, label)
        for index, category in enumerate(indicator.categories):
            sheet.cell(7, offset + 6 + 2 * index, category)
        sheet.cell(7, offset + width, "Total")
        total = sum(counts)
        base = ["NORTE", 11, "RO", 110001, "MUNICIPIO TESTE"]
        for column, value in enumerate(base, 1):
            sheet.cell(8, column, value)
        for index, count in enumerate(counts):
            sheet.cell(8, 6 + 2 * index, count)
            sheet.cell(8, 7 + 2 * index, "%s%%" % (count / total * 100))
        sheet.cell(8, width, total)
        output = io.BytesIO()
        book.save(output)
        book.close()
        return output.getvalue()

    def test_parse_imc_por_idade(self):
        indicator = collector.INDICATORS["imc_por_idade"]
        rows, schema = collector.parse_export(
            self.workbook(indicator, [1, 1, 5, 1, 1, 1]), "RO", indicator,
        )
        stats = collector.validate(rows, schema)
        self.assertEqual(stats["total"], 1)
        self.assertEqual(rows[0]["Magreza acentuada - Quantidade"], 1)
        self.assertEqual(rows[0]["Total"], 10)

    def test_parse_altura_por_idade(self):
        indicator = collector.INDICATORS["altura_por_idade"]
        rows, schema = collector.parse_export(
            self.workbook(indicator, [1, 2, 7]), "RO", indicator,
        )
        stats = collector.validate(rows, schema)
        self.assertEqual(stats["total"], 1)
        self.assertEqual(
            rows[0]["Altura Muito Baixa para a Idade - Quantidade"], 1,
        )
        self.assertEqual(rows[0]["Altura Adequada para a Idade - %"], "70.0%")

    def test_payload_recebe_indice_e_faixa(self):
        payload = helper.report_payload(2025, "11", "3", "5", "10")
        self.assertEqual(payload["nu_indice_cri"], "3")
        self.assertEqual(payload["nu_idade_inicio"], "5")
        self.assertEqual(payload["nu_idade_fim"], "10")

    def test_configuracao_aceita_varias_faixas_por_indice(self):
        data = {
            "ano": 2025,
            "consultas": [
                {
                    "indice": "imc_por_idade",
                    "faixas_etarias": ["0-5", "5-10"],
                },
                {
                    "indice": "altura_por_idade",
                    "faixas_etarias": ["0-5", "5-10"],
                },
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            args = SimpleNamespace(
                config=path, year=None, indices=None, faixas_etarias=None,
            )
            queries = collector.resolve_queries(args)
        self.assertEqual(len(queries), 4)
        self.assertEqual(
            {(item.indicator.key, item.age_range.key) for item in queries},
            {
                ("imc_por_idade", "0_a_menor_5_anos"),
                ("imc_por_idade", "5_a_menor_10_anos"),
                ("altura_por_idade", "0_a_menor_5_anos"),
                ("altura_por_idade", "5_a_menor_10_anos"),
            },
        )

    def test_faixa_invalida_e_rejeitada(self):
        with self.assertRaises(ValueError):
            collector.canonical_age("3-9")


if __name__ == "__main__":
    unittest.main()
