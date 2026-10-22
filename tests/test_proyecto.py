"""Pruebas con datos sintéticos: no representan ninguna cuenta real."""

import csv
import json
import tempfile
import unittest
from pathlib import Path

from src.exportar import exportar
from src.parser import interpretar_scripts, normalizar_username, numero, ordenar_videos


class ProyectoTests(unittest.TestCase):
    def test_username(self):
        self.assertEqual(normalizar_username(" @estudiante_demo "), "estudiante_demo")
        for valor in ("", "@@demo", "https://tiktok.com/@demo", "a/b", "a b"):
            with self.assertRaises(ValueError):
                normalizar_username(valor)

    def test_cuenta_y_estadisticas_ausentes(self):
        objeto = {"userInfo": {"user": {"uniqueId": "demo", "nickname": "Prueba"}, "stats": {"followerCount": 0}}, "itemList": [
            {"id": "123", "author": {"uniqueId": "demo"}, "desc": "Prueba", "createTime": "1700000000", "stats": {"playCount": "10"}},
            {"id": "456", "author": {"uniqueId": "otra"}, "desc": "Ajeno"},
        ]}
        perfil, videos = interpretar_scripts(["no es json", json.dumps(objeto)], "demo")
        self.assertEqual(perfil["seguidores"], 0)
        self.assertIsNone(perfil["seguidos"])
        self.assertEqual(list(videos), ["123"])
        self.assertIsNone(videos["123"]["compartidos"])
        self.assertEqual(interpretar_scripts([json.dumps(objeto)], "desconocido"), (None, {}))

    def test_orden_y_numeros(self):
        self.assertIsNone(numero("desconocido"))
        self.assertIsNone(numero(-1))
        videos = [{"fecha_utc": f"2026-10-{i:02}T00:00:00+00:00"} for i in range(1, 16)]
        ordenados = ordenar_videos(videos + [{"fecha_utc": None}])
        self.assertEqual(len(ordenados), 10)
        self.assertEqual(ordenados[0], videos[-1])

    def test_exportacion_sin_datos_no_sobrescribe(self):
        resultado = {"usuario_solicitado": "demo", "perfil": None, "videos": [], "estado": "sin_datos", "http": 403, "consultado_utc": "2026-10-22", "avisos": ["Bloqueo de prueba"]}
        with tempfile.TemporaryDirectory() as temporal:
            archivos = exportar(resultado, "ambos", temporal)
            otros = exportar(resultado, "ambos", temporal)
            self.assertEqual(len(set(archivos + otros)), 6)
            self.assertIsNone(json.loads(archivos[0].read_text(encoding="utf-8"))["perfil"])
            with archivos[1].open(encoding="utf-8-sig", newline="") as archivo:
                fila = next(csv.DictReader(archivo))
                self.assertEqual(fila["seguidores"], "")
                self.assertEqual(fila["estado"], "sin_datos")


if __name__ == "__main__":
    unittest.main()
