"""Flujo sencillo: cuenta, datos públicos, Excel y conversación en la terminal."""

import asyncio
import getpass
import sys

from .analisis import analizar_descripciones
from .chat_ia import ErrorChat, consultar_gemini, contexto_documental
from .excel import crear_excel
from .exportar import exportar
from .parser import normalizar_username
from .scraper import analizar_cuenta

def mostrar(resultado):
    def dato(valor):
        return 'No disponible' if valor is None else valor
    perfil = resultado.get('perfil') or {}
    print(f"\nCUENTA: @{resultado['usuario_solicitado']}")
    for etiqueta, campo in [('Nombre', 'nombre_visible'), ('Biografía', 'biografia'),
                            ('Seguidores', 'seguidores'), ('Seguidos', 'seguidos'),
                            ('Me gusta de la cuenta', 'me_gusta_totales')]:
        valor = perfil.get(campo)
        if campo == 'me_gusta_totales' and valor is None:
            valor = perfil.get('me_gusta_totales_texto')
        print(f'{etiqueta}: {dato(valor)}')
    print(f"\nVIDEOS RECUPERADOS: {len(resultado['videos'])} (hasta 10)")
    for numero, video in enumerate(resultado['videos'], 1):
        print(f'\nVideo {numero}')
        print('Descripción:', dato(video.get('descripcion')))
        print('Fuente de la descripción:', dato(video.get('descripcion_fuente')))
        print('Fecha:', dato(video.get('fecha_utc') or video.get('fecha_publicacion_texto')))
        print('Vistas:', dato(video.get('visualizaciones') if video.get('visualizaciones') is not None else video.get('visualizaciones_texto')))
        print('Me gusta:', dato(video.get('me_gusta')), '| Comentarios:', dato(video.get('comentarios')),
              '| Compartidos:', dato(video.get('compartidos')))
        print('Enlace:', dato(video.get('enlace')))
    for aviso in resultado.get('avisos', []):
        print('Aviso:', aviso)


def obtener_datos(username):
    # Evaluación en vivo: nunca buscar ni reutilizar capturas automáticamente.
    print('\nConsultando la cuenta pública. Puede tardar un momento...')
    return asyncio.run(analizar_cuenta(username))


def guardar_resultados(resultado):
    resultado['analisis_textual'] = analizar_descripciones(resultado['videos'])
    archivos = exportar(resultado, 'ambos')
    print('\nTus resultados se guardaron en:', archivos[0].parent)
    print('Datos JSON:', archivos[0].name)
    if resultado['videos']:
        destino = archivos[0].with_suffix('.xlsx')
        print('Creando Excel con tablas y gráficos de barras...')
        try:
            print('EXCEL:', crear_excel(resultado, destino))
        except (RuntimeError, TimeoutError, OSError) as error:
            print('No se pudo crear el Excel:', error)
            print('Los archivos JSON y CSV sí se conservaron.')
    else:
        print('No hay videos para graficar. No se creará un gráfico con datos inventados.')


def conversar(resultado, clave):
    """El historial y la clave permanecen en memoria; cada cuenta inicia otro historial."""
    contexto = contexto_documental(resultado)
    historial = []
    print('\nCHAT DEL ANÁLISIS')
    print('Pregunta por las descripciones o por señales de Big Five.')
    print('Ejemplo: ¿Qué señales hay de cada dimensión y en qué videos te basas?')
    print('Big Five aquí es una lectura del contenido, no una medición de personalidad.')
    print('Comandos: /otra = otra cuenta | /salir = cerrar | /nueva = borrar conversación')
    while True:
        pregunta = input('\nTú: ').strip()
        if pregunta.casefold() in ('/salir', 'salir'):
            return False, clave
        if pregunta.casefold() == '/otra':
            return True, clave
        if pregunta.casefold() == '/nueva':
            historial.clear()
            print('Conversación borrada. Los datos de la cuenta siguen cargados.')
            continue
        if not pregunta:
            continue
        if len(pregunta) > 4000:
            print('Escribe una pregunta más corta (máximo 4000 caracteres).')
            continue
        if not clave:
            print('\nPara conversar necesitas tu clave de Gemini Free Tier, sin facturación.')
            print('Google recibirá las fuentes públicas y tus mensajes; el plan gratuito puede usarlos para mejorar productos.')
            print('La aplicación no verifica la facturación. No pegues la clave en chats ni archivos.')
            if input('¿Confirmas que tu proyecto es gratuito y sin facturación? [s/N]: ').strip().casefold() not in ('s', 'si', 'sí'):
                print('No se enviaron datos a Google.')
                continue
            # Si la terminal no admite ocultar la entrada, detenerse sin pedir la clave visible.
            import warnings
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter('error', getpass.GetPassWarning)
                    clave = getpass.getpass('Clave de Gemini (no se mostrará al escribir): ').strip()
            except getpass.GetPassWarning:
                print('Esta terminal no permite ocultar la clave. Abre una terminal normal de VS Code.')
                continue
        print('Consultando Gemini...')
        try:
            respuesta = consultar_gemini(clave, contexto, historial, pregunta)
        except ErrorChat as error:
            print('Aviso:', error)
            if error.estado == 502:
                clave = ''
            continue
        print('\nIA:', respuesta)
        historial.extend([{'role': 'user', 'content': pregunta}, {'role': 'assistant', 'content': respuesta}])
        # Limitar por caracteres además de turnos para respetar el cliente de Gemini.
        while len(historial) > 12 or sum(len(m['content']) for m in historial) > 35000:
            del historial[:2]


def main():
    for salida in (sys.stdout, sys.stderr):
        if hasattr(salida, 'reconfigure'):
            salida.reconfigure(encoding='utf-8', errors='replace')
    clave = ''
    print('TIKTOK: DATOS, EXCEL Y CHAT')
    print('Consulta en vivo, sin usar datos guardados. Escribe salir para cerrar.')
    try:
        while True:
            entrada = input('\nNombre de la cuenta de TikTok (con o sin @): ').strip()
            if entrada.casefold() in ('salir', '/salir'):
                break
            try:
                username = normalizar_username(entrada)
                resultado = obtener_datos(username)
                mostrar(resultado)
                guardar_resultados(resultado)
            except (ValueError, OSError) as error:
                print('No se completó la consulta:', error)
                continue
            if not any(isinstance(v.get('descripcion'), str) and v['descripcion'].strip() for v in resultado['videos']):
                print('\nNo se obtuvieron descripciones utilizables para el chat de esta cuenta.')
                print('Puedes probar otra cuenta. Esto no demuestra que la cuenta no tenga videos.')
                continue
            continuar, clave = conversar(resultado, clave)
            if not continuar:
                break
    except (KeyboardInterrupt, EOFError):
        print('\nConsulta finalizada.')
    finally:
        clave = ''
    print('Programa cerrado. La clave no se guardó en archivos.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
