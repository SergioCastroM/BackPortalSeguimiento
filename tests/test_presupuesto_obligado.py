"""La columna Obligado del Excel de presupuesto se lee como mínimo de cumplimiento."""
import io
import unittest

from openpyxl import Workbook

from app.services.presupuesto_sync_service import parse_presupuesto_excel


def _xlsx(headers: list[str], fila: list) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.append(headers)
    ws.append(fila)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


class ObligadoExcelTest(unittest.TestCase):
    def test_lee_obligado_cuando_la_columna_existe(self):
        content = _xlsx(
            ["Meta ID", "Código meta", "Valor inicial", "Adiciones", "Deducciones", "Obligado", "Valor final"],
            [820, "I4", 100, 10, 5, 80, 105],
        )
        rows, warnings = parse_presupuesto_excel(content)
        self.assertEqual(warnings, [])
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0]["tiene_obligado"])
        self.assertEqual(rows[0]["obligado"], 80.0)
        self.assertEqual(rows[0]["meta_id"], 820)

    def test_sin_columna_no_pisa_el_obligado(self):
        content = _xlsx(
            ["Meta ID", "Código meta", "Valor inicial", "Adiciones", "Deducciones", "Valor final"],
            [820, "I4", 100, 0, 0, 100],
        )
        rows, _warnings = parse_presupuesto_excel(content)
        self.assertFalse(rows[0]["tiene_obligado"])
        self.assertIsNone(rows[0]["obligado"])

    def test_celda_vacia_deja_obligado_nulo(self):
        content = _xlsx(
            ["Meta ID", "Código meta", "Valor inicial", "Adiciones", "Deducciones", "Obligado", "Valor final"],
            [821, "I4", 10, 0, 0, None, 10],
        )
        rows, _warnings = parse_presupuesto_excel(content)
        self.assertTrue(rows[0]["tiene_obligado"])
        self.assertIsNone(rows[0]["obligado"])


if __name__ == "__main__":
    unittest.main()
