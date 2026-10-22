"""Verificar que la consola no mezcle cuentas ni envíe fuentes inexistentes."""

import unittest
from unittest.mock import patch

from src.consola import conversar, main


class ConsolaTests(unittest.TestCase):
    def test_cuenta_sin_descripciones_no_abre_chat(self):
        resultado = {'videos': []}
        with patch('builtins.input', side_effect=['demo', 'salir']), \
             patch('src.consola.obtener_datos', return_value=resultado), \
             patch('src.consola.mostrar'), patch('src.consola.guardar_resultados'), \
             patch('src.consola.conversar') as chat, patch('builtins.print'):
            self.assertEqual(main(), 0)
            chat.assert_not_called()

    def test_cambiar_cuenta_no_reutiliza_historial(self):
        resultado = {'usuario_solicitado': 'demo', 'consultado_utc': '2026-10-22',
                     'videos': [{'id_video': '1', 'descripcion': 'Texto de prueba'}]}
        with patch('builtins.input', side_effect=['Pregunta', '/otra']), \
             patch('src.consola.consultar_gemini', return_value='Respuesta') as ia, \
             patch('builtins.print'):
            continuar, _ = conversar(resultado, 'clave_sintetica')
            self.assertTrue(continuar)
        with patch('builtins.input', side_effect=['Otra pregunta', '/salir']), \
             patch('src.consola.consultar_gemini', return_value='Respuesta') as ia, \
             patch('builtins.print'):
            # Copiar el historial en el momento de la llamada, antes de actualizarlo.
            historiales = []
            ia.side_effect = lambda clave, contexto, historial, pregunta: historiales.append(list(historial)) or 'Respuesta'
            continuar, _ = conversar(resultado, 'clave_sintetica')
            self.assertFalse(continuar)
            self.assertEqual(historiales, [[]])

    def test_sin_confirmacion_gratuita_no_pide_clave_ni_llama_ia(self):
        resultado = {'usuario_solicitado': 'demo', 'consultado_utc': '2026-10-22', 'videos': []}
        with patch('builtins.input', side_effect=['Pregunta', 'n', '/salir']), \
             patch('src.consola.getpass.getpass') as clave, \
             patch('src.consola.consultar_gemini') as ia, patch('builtins.print'):
            conversar(resultado, '')
            clave.assert_not_called()
            ia.assert_not_called()
