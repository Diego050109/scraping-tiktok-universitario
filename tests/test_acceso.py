"""Simular bloqueos y respuestas parciales; no se accede a cuentas reales."""

import json
import types
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from src.scraper import analizar_cuenta, describir_error, requiere_verificacion


class AccesoTests(unittest.IsolatedAsyncioTestCase):
    def navegador_simulado(self, respuestas, contenido):
        page = types.SimpleNamespace(
            goto=AsyncMock(side_effect=[types.SimpleNamespace(status=s) for s in respuestas]),
            wait_for_timeout=AsyncMock(),
            url="https://www.tiktok.com/@demo",
            locator=MagicMock(),
            on=MagicMock(),
            mouse=types.SimpleNamespace(wheel=AsyncMock()),
        )
        page.locator.return_value.all_text_contents = AsyncMock(return_value=[json.dumps(contenido)])
        page.locator.return_value.evaluate_all = AsyncMock(return_value=[])
        page.locator.return_value.inner_text = AsyncMock(return_value="Contenido público de prueba")
        context = types.SimpleNamespace(new_page=AsyncMock(return_value=page))
        browser = types.SimpleNamespace(new_context=AsyncMock(return_value=context), close=AsyncMock())
        engine = types.SimpleNamespace(chromium=types.SimpleNamespace(launch=AsyncMock(return_value=browser)))
        factory = MagicMock()
        factory.return_value.__aenter__ = AsyncMock(return_value=engine)
        factory.return_value.__aexit__ = AsyncMock(return_value=False)
        module = types.ModuleType("playwright.async_api")
        module.async_playwright = factory
        return {"playwright": types.ModuleType("playwright"), "playwright.async_api": module}, page, browser

    async def test_http_bloqueado_detiene_sin_datos(self):
        modules, page, browser = self.navegador_simulado([403], {})
        with patch.dict("sys.modules", modules):
            resultado = await analizar_cuenta("demo")
        self.assertEqual(resultado["estado"], "acceso_no_disponible")
        self.assertIsNone(resultado["perfil"])
        self.assertEqual(resultado["videos"], [])
        self.assertEqual(page.goto.await_count, 1)
        browser.close.assert_awaited_once()

    async def test_cuenta_privada_detiene_sin_videos(self):
        contenido = {"userInfo": {"user": {"uniqueId": "demo", "privateAccount": True}}}
        modules, page, browser = self.navegador_simulado([200], contenido)
        with patch.dict("sys.modules", modules):
            resultado = await analizar_cuenta("demo")
        self.assertEqual(resultado["estado"], "cuenta_privada")
        self.assertIsNone(resultado["perfil"])
        self.assertEqual(page.goto.await_count, 1)
        browser.close.assert_awaited_once()

    async def test_bloqueo_video_conserva_perfil_y_datos_previos(self):
        contenido = {"userInfo": {"user": {"uniqueId": "demo"}}, "itemList": [
            {"id": "123", "author": {"uniqueId": "demo"}, "desc": "Solo prueba"}
        ]}
        modules, page, browser = self.navegador_simulado([200, 403], contenido)
        with patch.dict("sys.modules", modules):
            resultado = await analizar_cuenta("demo")
        self.assertEqual(resultado["estado"], "parcial")
        self.assertEqual(len(resultado["videos"]), 1)
        self.assertIsNone(resultado["videos"][0]["visualizaciones"])
        self.assertTrue(any("detenido" in aviso for aviso in resultado["avisos"]))
        browser.close.assert_awaited_once()

    async def test_lee_videos_cargados_por_la_pagina_sin_repetir_endpoint(self):
        import asyncio
        contenido = {"userInfo": {"user": {"uniqueId": "demo"}}}
        modules, page, browser = self.navegador_simulado([], contenido)
        respuesta_red = types.SimpleNamespace(url="https://www.tiktok.com/api/post/item_list/", status=200,
            json=AsyncMock(return_value={"itemList": [{"id":"123", "author":{"uniqueId":"demo"}, "desc":"Descripción de prueba", "createTime":1700000000}]}))
        async def navegar(url, **opciones):
            if url.endswith('@demo'):
                page.on.call_args.args[1](respuesta_red)
                await asyncio.sleep(0)
            return types.SimpleNamespace(status=200)
        page.goto.side_effect = navegar
        with patch.dict("sys.modules", modules):
            resultado = await analizar_cuenta('demo')
        self.assertEqual(resultado['videos'][0]['descripcion'], 'Descripción de prueba')
        self.assertEqual(page.goto.await_count, 2)
        self.assertFalse(any('/api/' in llamada.args[0] for llamada in page.goto.await_args_list))

    async def test_respuesta_200_sin_cuerpo_no_se_confunde_con_lista_valida(self):
        import asyncio
        modules, page, browser = self.navegador_simulado([], {"userInfo":{"user":{"uniqueId":"demo"}}})
        respuesta_red = types.SimpleNamespace(url="https://www.tiktok.com/api/post/item_list/", status=200,
            json=AsyncMock(side_effect=ValueError("Respuesta vacía")), body=AsyncMock(return_value=b""))
        async def navegar(url, **opciones):
            page.on.call_args.args[1](respuesta_red)
            await asyncio.sleep(0)
            return types.SimpleNamespace(status=200)
        page.goto.side_effect = navegar
        with patch.dict("sys.modules", modules):
            resultado = await analizar_cuenta("demo")
        self.assertEqual(resultado['diagnostico_publicaciones'][0], {'http':200,'bytes':0,'json_valido':False})
        self.assertEqual(resultado['videos'], [])
        self.assertTrue(any('0 bytes' in aviso for aviso in resultado['avisos']))
        self.assertEqual(page.mouse.wheel.await_count, 3)  # Una respuesta vacía no impide esperar el DOM público.



    async def test_descripcion_visible_se_conserva_si_detalle_no_la_entrega(self):
        modules, page, browser = self.navegador_simulado([200, 200], {'userInfo': {'user': {'uniqueId': 'demo'}}})
        def contenido_dom(codigo):
            if 'descripcion:' in codigo:
                return [{'enlace': '/@demo/video/123', 'descripcion': 'Texto público de prueba'},
                        {'enlace': '/@otra/video/456', 'descripcion': 'No mezclar cuentas'}]
            return ['https://www.tiktok.com/@demo/video/123']
        page.locator.return_value.evaluate_all.side_effect = contenido_dom
        with patch.dict('sys.modules', modules):
            resultado = await analizar_cuenta('demo')
        self.assertEqual(len(resultado['videos']), 1)
        self.assertEqual(resultado['videos'][0]['descripcion'], 'Texto público de prueba')
        self.assertIn('miniatura', resultado['videos'][0]['descripcion_fuente'])
        self.assertIsNone(resultado['videos'][0]['me_gusta'])


class DiagnosticoTests(unittest.TestCase):
    def test_verificacion_de_rompecabezas_se_detecta(self):
        self.assertTrue(requiere_verificacion('Drag the slider to fit the puzzle'))
        self.assertTrue(requiere_verificacion('Arrastra el deslizador'))
        self.assertFalse(requiere_verificacion('Iniciar sesión | Seguidores | Videos'))

    def test_error_red_sin_exponer_url_o_token(self):
        error = RuntimeError("Page.goto: net::ERR_CONNECTION_RESET at https://example.test/?token=secreto")
        aviso = describir_error(error, "conectar con la página pública")
        self.assertIn("net::ERR_CONNECTION_RESET", aviso)
        self.assertNotIn("secreto", aviso)
        self.assertNotIn("install chromium", aviso)

    def test_navegador_ausente_da_instruccion_correcta(self):
        aviso = describir_error(RuntimeError("Executable doesn't exist at ruta-local"), "iniciar Chromium")
        self.assertIn("python -m playwright install chromium", aviso)
        self.assertNotIn("ruta-local", aviso)

    def test_fallo_lectura_conserva_http_recibido(self):
        # El HTTP ya recibido no debe perderse si falla después la lectura.
        async def ejecutar():
            modules, page, browser = AccesoTests().navegador_simulado([200], {})
            page.locator.return_value.all_text_contents.side_effect = RuntimeError("Fallo simulado")
            with patch.dict("sys.modules", modules):
                resultado = await analizar_cuenta("demo")
            self.assertEqual(resultado["http"], 200)
            self.assertIn("leer el contenido público recibido", resultado["avisos"][0])
            browser.close.assert_awaited_once()
        import asyncio
        asyncio.run(ejecutar())
