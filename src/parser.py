"""Funciones puras para interpretar los datos públicos, sin conexiones de red."""

import json
import re
from datetime import datetime, timezone


def normalizar_username(valor):
    usuario = valor.strip().removeprefix("@")
    if not re.fullmatch(r"[A-Za-z0-9._]{1,24}", usuario):
        raise ValueError("Escribe un username de 1 a 24 letras, números, puntos o guiones bajos.")
    return usuario


def recorrer(objeto):
    """Recorrer diccionarios JSON sin depender de una ruta interna fija."""
    if isinstance(objeto, dict):
        yield objeto
        for valor in objeto.values():
            yield from recorrer(valor)
    elif isinstance(objeto, list):
        for valor in objeto:
            yield from recorrer(valor)


def numero(valor):
    if isinstance(valor, bool):
        return None
    try:
        entero = int(str(valor))
        return entero if entero >= 0 else None
    except (ValueError, TypeError):
        return None


def fecha_utc(valor):
    timestamp = numero(valor)
    if timestamp is None:
        return None
    try:
        return datetime.fromtimestamp(timestamp, timezone.utc).isoformat()
    except (ValueError, OSError, OverflowError):
        return None


def diccionario(valor):
    return valor if isinstance(valor, dict) else {}


def autor_de(video):
    autor = video.get("author")
    if isinstance(autor, dict):
        return autor.get("uniqueId") or autor.get("unique_id")
    return autor if isinstance(autor, str) else None


def normalizar_video(video, username):
    stats = diccionario(video.get("stats")) or diccionario(video.get("statsV2"))
    video_id = str(video["id"])
    return {
        "username": username,
        "id_video": video_id,
        "descripcion": video.get("desc") if isinstance(video.get("desc"), str) else None,
        "descripcion_fuente": "JSON público servido por TikTok" if isinstance(video.get("desc"), str) else None,
        "fecha_utc": fecha_utc(video.get("createTime")),
        "enlace": f"https://www.tiktok.com/@{username}/video/{video_id}",
        "visualizaciones": numero(stats.get("playCount")),
        "me_gusta": numero(stats.get("diggCount")),
        "comentarios": numero(stats.get("commentCount")),
        "compartidos": numero(stats.get("shareCount")),
    }


def interpretar_scripts(contenidos, username):
    """Aceptar solo el perfil y videos cuyo autor coincide con la consulta."""
    perfil = None
    videos = {}
    for contenido in contenidos:
        try:
            objeto = json.loads(contenido)
        except (ValueError, TypeError, RecursionError):
            continue
        for nodo in recorrer(objeto):
            info = diccionario(nodo.get("userInfo"))
            usuario = diccionario(info.get("user"))
            if str(usuario.get("uniqueId", "")).casefold() == username.casefold():
                stats = diccionario(info.get("stats")) or diccionario(info.get("statsV2"))
                perfil = {
                    "username": usuario["uniqueId"],
                    "nombre_visible": usuario.get("nickname"),
                    "biografia": usuario.get("signature"),
                    "seguidores": numero(stats.get("followerCount")),
                    "seguidos": numero(stats.get("followingCount")),
                    "me_gusta_totales": numero(stats.get("heartCount", stats.get("heart"))),
                    "videos_totales": numero(stats.get("videoCount")),
                    "privada": usuario.get("privateAccount") is True,
                }
            autor = autor_de(nodo)
            video_id = str(nodo.get("id", ""))
            if isinstance(autor, str) and autor.casefold() == username.casefold() and video_id.isdigit():
                # Un usuario también tiene id; solo aceptar objetos con datos de video.
                if any(clave in nodo for clave in ("video", "desc", "createTime")):
                    videos[video_id] = normalizar_video(nodo, username)
    return perfil, videos


def ordenar_videos(videos):
    # Los de fecha desconocida quedan al final, sin inventar una fecha.
    return sorted(videos, key=lambda v: (v.get("fecha_utc") or "", int(v.get("id_video", "0")) if str(v.get("id_video", "0")).isdigit() else 0), reverse=True)[:10]
