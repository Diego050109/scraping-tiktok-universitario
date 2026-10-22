"""Exportación con nombres únicos y protección frente a fórmulas de CSV."""

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


def celda_segura(valor):
    if isinstance(valor, str) and valor.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + valor
    return valor


def guardar_csv(ruta, filas, columnas):
    with ruta.open("x", encoding="utf-8-sig", newline="") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=columnas)
        escritor.writeheader()
        for fila in filas:
            escritor.writerow({clave: celda_segura(fila.get(clave)) for clave in columnas})


def exportar(resultado, formato="ambos", carpeta=None):
    carpeta = Path(carpeta) if carpeta else Path(__file__).resolve().parents[1] / "data"
    carpeta.mkdir(parents=True, exist_ok=True)
    marca = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    prefijo = f"tiktok_{resultado['usuario_solicitado']}_{marca}_{uuid4().hex[:8]}"
    archivos = []
    if formato in ("json", "ambos"):
        ruta = carpeta / f"{prefijo}.json"
        with ruta.open("x", encoding="utf-8") as archivo:
            json.dump(resultado, archivo, ensure_ascii=False, indent=2)
        archivos.append(ruta)
    if formato in ("csv", "ambos"):
        ruta = carpeta / f"{prefijo}_perfil.csv"
        perfil = resultado["perfil"] or {}
        fila = {"usuario_solicitado": resultado["usuario_solicitado"], **perfil,
                "estado": resultado["estado"], "consultado_utc": resultado["consultado_utc"],
                "http": resultado["http"], "avisos": " | ".join(resultado["avisos"])}
        guardar_csv(ruta, [fila], ["usuario_solicitado", "username", "nombre_visible", "biografia", "seguidores", "seguidos", "me_gusta_totales", "videos_totales", "estado", "consultado_utc", "http", "avisos"])
        archivos.append(ruta)
        ruta = carpeta / f"{prefijo}_videos.csv"
        guardar_csv(ruta, resultado["videos"], ["username", "id_video", "descripcion", "descripcion_fuente", "fecha_utc", "fecha_publicacion_texto", "enlace", "visualizaciones", "visualizaciones_texto", "me_gusta", "comentarios", "compartidos", "anclado"])
        archivos.append(ruta)
    return archivos
