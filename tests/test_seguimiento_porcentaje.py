"""Porcentaje de seguimiento: sin valor final queda 0; con valor final se calcula."""
import unittest

from app.services.seguimiento_service import calcular_porcentaje


class PorcentajeSeguimientoTest(unittest.TestCase):
    def test_sin_referencia_queda_cero(self):
        self.assertEqual(calcular_porcentaje(5_000_000, 0), 0.0)

    def test_con_valor_final(self):
        self.assertEqual(calcular_porcentaje(5_000_000, 10_000_000), 50.0)

    def test_sobrecumplimiento(self):
        self.assertEqual(calcular_porcentaje(48_250_000, 37_800_000), 127.65)


if __name__ == "__main__":
    unittest.main()
