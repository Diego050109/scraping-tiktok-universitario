"""Lectura de páginas públicas, sin sesiones privadas ni evasión de bloqueos."""

import asyncio
import json
import re
from datetime import datetime, timezone
from urllib.parse import urlsplit

from .parser import interpretar_scripts, normalizar_username, normalizar_video, ordenar_videos


def describir_error(error, etapa):
    """Explicar causas comprobables sin mostrar datos de una sesión."""
    detalle = str(error)
    tipo = type(error).__name__
    prefijo = f"No se completó la lectura al {etapa} ({tipo}). "
    if "Executable doesn't exist" in detalle:
        return prefijo + "Falta el navegador de esta instalación. Ejecuta: python -m playwright install chromium"
    codigo = re.search(r"net::ERR_[A-Z0-9_]+", detalle)
    if codigo:
        return prefijo + f"Código de red: {codigo[0]}. Comprueba tu conexión y abre el perfil manualmente en el navegador. No se ha confirmado la causa ni un bloqueo de TikTok."
    if "Timeout" in tipo:
        return prefijo + "Se agotó el tiempo de espera. Comprueba la conexión e inténtalo de nuevo más tarde."
    if tipo == "TargetClosedError":
        return prefijo + "El navegador o la página se cerraron antes de terminar."
    return prefijo + "No se pudo determinar la causa. Conserva este aviso para revisar la etapa que falló; no demuestra que la cuenta no exista o que TikTok haya bloqueado el acceso."


def requiere_verificacion(texto, url=''):
    texto = texto.casefold()
    return any(frase in texto for frase in (
        'verify to continue', 'verify you are human', 'complete the captcha',
        'verifica que eres humano', 'security verification', 'access denied',
        'drag the slider', 'fit the puzzle', 'arrastra el deslizador',
    )) or '/login' in url.casefold() or 'captcha' in url.casefold()


async def analizar_cuenta(username, enlaces_adicionales=None):
    username = normalizar_username(username)
    resultado = {
        "usuario_solicitado": username,
        "url_consultada": f"https://www.tiktok.com/@{username}",
        "consultado_utc": datetime.now(timezone.utc).isoformat(),
        "estado": "sin_datos",
        "http": None,
        "perfil": None,
        "videos": [],
        "avisos": [],
        "orden_reciente_verificado": False,
        "diagnostico_publicaciones": [],
        "diagnostico_html": [],
        "metodo_obtencion": "Consulta en vivo: Playwright, JSON público y DOM; sin capturas previas",
    }
    avisos = resultado["avisos"]
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        avisos.append("Falta Playwright. Ejecuta: python -m pip install -r requirements.txt")
        return resultado

    etapa = "iniciar Playwright"
    try:
        async with async_playwright() as p:
            etapa = "iniciar Chromium"
            navegador = await p.chromium.launch(headless=True)
            try:
                etapa = "crear la página"
                contexto = await navegador.new_context()
                pagina = await contexto.new_page()
                videos_red = {}
                tareas_red = set()
                lista_vacia = False
                bloqueo_red = False

                async def observar_respuesta(respuesta):
                    nonlocal lista_vacia, bloqueo_red
                    url = urlsplit(respuesta.url)
                    # Solo observar la lista cargada por la navegación normal.
                    if url.hostname != "www.tiktok.com" or url.path != "/api/post/item_list/":
                        return
                    registro = {"http": respuesta.status, "bytes": None, "json_valido": None}
                    resultado["diagnostico_publicaciones"].append(registro)
                    if respuesta.status in (401, 403, 429):
                        bloqueo_red = True
                        return
                    try:
                        datos = await respuesta.json()
                        registro["json_valido"] = True
                        _, encontrados = interpretar_scripts([json.dumps(datos)], username)
                        videos_red.update(encontrados)
                        if not encontrados:
                            lista_vacia = True
                    except (ValueError, TypeError):
                        registro["json_valido"] = False
                        try:
                            registro["bytes"] = len(await respuesta.body())
                        except Exception:
                            pass
                        lista_vacia = True
                    except Exception:
                        lista_vacia = True

                def recibir_respuesta(respuesta):
                    tarea = asyncio.create_task(observar_respuesta(respuesta))
                    tareas_red.add(tarea)
                    tarea.add_done_callback(tareas_red.discard)

                pagina.on("response", recibir_respuesta)

                async def leer(url):
                    nonlocal etapa
                    etapa = "conectar con la página pública"
                    respuesta = await pagina.goto(url, wait_until="domcontentloaded", timeout=30000)
                    status = respuesta.status if respuesta else None
                    if url == resultado["url_consultada"]:
                        resultado["http"] = status
                    if status is None or status >= 400:
                        return status, [], [], True
                    etapa = "leer el contenido público recibido"
                    await pagina.wait_for_timeout(2000)
                    # Solo se inspecciona el contenido servido al navegador público.
                    scripts = await pagina.locator(
                        'script#__UNIVERSAL_DATA_FOR_REHYDRATION__, script#SIGI_STATE, script[type="application/json"]'
                    ).all_text_contents()
                    enlaces = await pagina.locator('a[href*="/video/"]').evaluate_all(
                        "elements => elements.map(element => element.getAttribute('href'))"
                    )
                    texto = (await pagina.locator("body").inner_text()).casefold()
                    bloqueada = requiere_verificacion(texto, pagina.url)
                    perfil_html, videos_html = interpretar_scripts(scripts, username)
                    resultado['diagnostico_html'].append({'http': status, 'scripts_json': len(scripts),
                        'enlaces_video': len(enlaces), 'perfil_en_json': bool(perfil_html),
                        'videos_en_json': len(videos_html), 'verificacion': bloqueada})
                    return status, scripts, enlaces, bloqueada

                status, scripts, enlaces, bloqueada = await leer(resultado["url_consultada"])
                resultado["http"] = status
                perfil, videos = interpretar_scripts(scripts, username)
                if perfil and not perfil.get('privada'):
                    resultado['perfil'] = perfil
                if bloqueada:
                    resultado["estado"] = "acceso_no_disponible"
                    avisos.append(f"Consulta detenida: HTTP {status}, inicio de sesión o verificación. No se intenta evadir el acceso.")
                    return resultado
                perfil, videos = interpretar_scripts(scripts, username)
                resultado["perfil"] = perfil
                if perfil and perfil["privada"]:
                    resultado["perfil"] = None
                    resultado["estado"] = "cuenta_privada"
                    avisos.append("El perfil indica que la cuenta es privada. Consulta detenida.")
                    return resultado

                patron = re.compile(r"^(?:https://www\.tiktok\.com)?/@" + re.escape(username) + r"/video/(\d+)(?:[?#].*)?$", re.I)
                # Esperar contenido dinámico; los videos fijados no determinan la fecha.
                if len(videos) < 13 and len(enlaces) < 13:
                    for _ in range(3):
                        if bloqueo_red:
                            break
                        await pagina.mouse.wheel(0, 900)
                        await pagina.wait_for_timeout(2500)
                        nuevos_enlaces = await pagina.locator('a[href*="/video/"]').evaluate_all(
                            "elements => elements.map(element => element.getAttribute('href'))"
                        )
                        enlaces = list(dict.fromkeys(enlaces + nuevos_enlaces))
                        if requiere_verificacion(await pagina.locator('body').inner_text(), pagina.url):
                            resultado['estado'] = 'acceso_no_disponible'
                            resultado['diagnostico_html'][-1]['verificacion'] = True
                            avisos.append('TikTok mostró una verificación de acceso. Consulta detenida sin resolverla ni usar cookies privadas; no se obtuvieron descripciones para el análisis.')
                            return resultado
                        if len(enlaces) >= 13 or len(videos_red) >= 13:
                            break
                if tareas_red:
                    await asyncio.gather(*list(tareas_red), return_exceptions=True)
                videos.update(videos_red)
                if lista_vacia:
                    if any(r["bytes"] == 0 for r in resultado["diagnostico_publicaciones"]):
                        avisos.append("La respuesta de publicaciones llegó con 0 bytes: no contiene videos ni descripciones para extraer. El HTTP 200 no garantiza datos. La causa de esa respuesta vacía no está confirmada.")
                    else:
                        avisos.append("TikTok entregó vacía o ilegible la lista pública de publicaciones. Esto no prueba que la cuenta no tenga videos.")
                if bloqueo_red:
                    avisos.append("TikTok rechazó la lista de videos (HTTP 401, 403 o 429). Se detiene la consulta de videos.")
                    resultado['estado'] = 'acceso_no_disponible'
                    resultado['videos'] = ordenar_videos(list(videos.values()))
                    return resultado
                elif enlaces_adicionales:
                    enlaces += enlaces_adicionales
                for enlace in enlaces:
                    match = patron.fullmatch(enlace or "")
                    if match and match[1] not in videos:
                        videos[match[1]] = normalizar_video({"id": match[1]}, username)

                # Leer las descripciones visibles, incluso si la lista JSON vino vacía.
                # No usar sesiones privadas ni repetir el endpoint de publicaciones.
                if not bloqueo_red:
                    tarjetas = await pagina.locator('a[href*="/video/"]').evaluate_all("""elements => elements.map(a => ({
                        enlace: a.getAttribute('href'),
                        descripcion: a.querySelector('[data-e2e="user-post-item-desc"]')?.textContent ?? a.querySelector('img[alt]')?.getAttribute('alt') ?? null
                    }))""")
                    for tarjeta in tarjetas:
                        if not isinstance(tarjeta, dict):
                            continue
                        match = patron.fullmatch(tarjeta.get('enlace') or '')
                        if not match:
                            continue
                        video = videos.setdefault(match[1], normalizar_video({'id': match[1]}, username))
                        descripcion = tarjeta.get('descripcion')
                        if video.get('descripcion') is None and isinstance(descripcion, str) and descripcion.strip():
                            video['descripcion'] = descripcion.strip()
                            video['descripcion_fuente'] = 'Texto visible o alternativo de miniatura pública; puede estar abreviado'
                    if any(v.get('descripcion_fuente') for v in videos.values()):
                        avisos.append('Se leyeron textos de miniaturas públicas; pueden estar abreviados y no son transcripciones de videos.')

                # Consultar como máximo diez detalles de candidatos descubiertos públicamente.
                seleccion = ordenar_videos(list(videos.values()))
                if bloqueo_red:
                    seleccion = []
                for video in seleccion:
                    resultado["videos"] = ordenar_videos(list(videos.values()))
                    status_video, scripts_video, _, bloqueada = await leer(video["enlace"])
                    if bloqueada:
                        avisos.append(f"Acceso a videos detenido (HTTP {status_video} o verificación); se conservan los datos públicos ya recibidos.")
                        break
                    _, detalles = interpretar_scripts(scripts_video, username)
                    if video["id_video"] in detalles:
                        detalle = detalles[video['id_video']]
                        for campo in ('descripcion', 'descripcion_fuente'):
                            if detalle.get(campo) is None and video.get(campo) is not None:
                                detalle[campo] = video[campo]
                        videos[video['id_video']] = detalle
                    else:
                        avisos.append(f"No se recibieron los detalles del video {video['id_video']}; no se inventa su descripción.")
                resultado["videos"] = ordenar_videos(list(videos.values()))
                if perfil is None:
                    avisos.append("No se recibió el perfil esperado. Puede ser un bloqueo, una cuenta inexistente o un cambio de formato.")
                if not resultado["videos"]:
                    avisos.append("No se recibieron videos públicos identificables; esto no demuestra que la cuenta tenga cero videos.")
            finally:
                if 'tareas_red' in locals():
                    for tarea in tareas_red:
                        tarea.cancel()
                    if tareas_red:
                        await asyncio.gather(*list(tareas_red), return_exceptions=True)
                await navegador.close()
    except Exception as error:
        # Clasificar sin volcar respuestas, cabeceras, cookies ni URLs privadas.
        avisos.append(describir_error(error, etapa))

    if resultado["perfil"] and resultado["videos"] and not avisos:
        resultado["estado"] = "datos_disponibles"
    elif resultado["perfil"] or resultado["videos"]:
        resultado["estado"] = "parcial"
    avisos.append("Se muestran hasta 10 videos entre los recibidos, ordenados por fecha cuando existe. No se garantiza que sean los 10 más recientes de toda la cuenta (fijados, carga parcial o fechas ausentes).")
    return resultado
