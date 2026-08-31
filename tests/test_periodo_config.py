"""Tests de la lógica de tipo de período (sin tocar la BD de producción)."""
import unittest

from app.services.periodo_config import (
    TIPO_CUATRIMESTRE,
    TIPO_TRIMESTRE,
    cantidad_periodos,
    etiqueta_periodo,
    fechas_limite_tipo,
    nombre_periodo,
    normalizar_tipo,
    numeros_periodo,
    prefijo_periodo,
)


class PeriodoConfigLogicTest(unittest.TestCase):
    def test_cuatrimestre_tiene_tres_periodos(self):
        self.assertEqual(cantidad_periodos(TIPO_CUATRIMESTRE), 3)
        self.assertEqual(numeros_periodo(TIPO_CUATRIMESTRE), [1, 2, 3])
        self.assertEqual(prefijo_periodo(TIPO_CUATRIMESTRE), "C")
        self.assertEqual(etiqueta_periodo(TIPO_CUATRIMESTRE, 1), "C1")
        self.assertEqual(nombre_periodo(TIPO_CUATRIMESTRE, plural=True), "Cuatrimestres")

    def test_trimestre_tiene_cuatro_periodos(self):
        self.assertEqual(cantidad_periodos(TIPO_TRIMESTRE), 4)
        self.assertEqual(numeros_periodo(TIPO_TRIMESTRE), [1, 2, 3, 4])
        self.assertEqual(etiqueta_periodo(TIPO_TRIMESTRE, 4), "T4")

    def test_fechas_limite_no_se_solapan(self):
        c = fechas_limite_tipo(TIPO_CUATRIMESTRE)
        self.assertEqual(c[1], (4, 30))
        self.assertEqual(c[2], (8, 31))
        self.assertEqual(c[3], (12, 31))
        t = fechas_limite_tipo(TIPO_TRIMESTRE)
        self.assertEqual(t[4], (12, 31))

    def test_normaliza_tipo_invalido_a_cuatrimestre(self):
        self.assertEqual(normalizar_tipo("CUATRIMESTRE"), TIPO_CUATRIMESTRE)
        self.assertEqual(normalizar_tipo("no-existe"), TIPO_CUATRIMESTRE)
        self.assertEqual(normalizar_tipo("trimestre"), TIPO_TRIMESTRE)


if __name__ == "__main__":
    unittest.main()
