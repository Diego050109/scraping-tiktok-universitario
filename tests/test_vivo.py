"""Regresiones para la evaluación en vivo. No consulta cuentas reales."""

import asyncio
import json
import unittest
from unittest.mock import patch

from src.consola import obtener_datos
from src.parser import interpretar_scripts, ordenar_videos
from src.scraper import analizar_cuenta
import test_acceso as acceso


class VivoTests(unittest.TestCase):
    def test_consola_no_busca_capturas(self):
        with patch('pathlib.Path.glob') as cache, patch('src.consola.analizar_cuenta', return_value={'videos': []}) as vivo, patch('builtins.print'):
            obtener_datos('demo')
            cache.assert_not_called()
            vivo.assert_awaited_once_with('demo')

    def test_stats_v2_y_descripcion_ausente(self):
        perfil, videos = interpretar_scripts([json.dumps({'userInfo': {'user': {'uniqueId': 'demo'},
            'statsV2': {'followerCount': '0', 'heartCount': '12'}},
            'itemList': [{'id': '1', 'author': {'uniqueId': 'demo'}, 'desc': None}]})], 'demo')
        self.assertEqual(perfil['seguidores'], 0)
        self.assertEqual(perfil['me_gusta_totales'], 12)
        self.assertIsNone(videos['1']['descripcion'])
        self.assertIsNone(videos['1']['comentarios'])

    def test_orden_empata_por_id_sin_inventar_fecha(self):
        salida = ordenar_videos([{'id_video': '1', 'fecha_utc': None}, {'id_video': '2', 'fecha_utc': None}])
        self.assertEqual(salida[0]['id_video'], '2')
        self.assertIsNone(salida[0]['fecha_utc'])

    def test_verificacion_tardia_conserva_perfil_y_detiene(self):
        async def prueba():
            modules, page, browser = acceso.AccesoTests().navegador_simulado([200], {'userInfo': {'user': {'uniqueId': 'demo'}, 'stats': {'followerCount': 5}}})
            page.locator.return_value.inner_text.side_effect = ['Perfil público', 'Drag the slider to fit the puzzle']
            with patch.dict('sys.modules', modules):
                resultado = await analizar_cuenta('demo')
            self.assertEqual(resultado['estado'], 'acceso_no_disponible')
            self.assertEqual(resultado['perfil']['seguidores'], 5)
            self.assertTrue(resultado['diagnostico_html'][0]['verificacion'])
            self.assertEqual(page.goto.await_count, 1)
            browser.close.assert_awaited_once()
        asyncio.run(prueba())
