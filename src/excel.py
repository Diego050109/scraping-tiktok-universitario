"""Crear el Excel mediante el motor de hojas de cálculo disponible en este equipo."""

import json
import os
import subprocess
import tempfile
from pathlib import Path


def crear_excel(resultado, destino):
    dependencias = Path.home() / '.cache/codex-runtimes/codex-primary-runtime/dependencies'
    node = Path(os.environ.get('TIKTOK_NODE', str(dependencias / 'node/bin/node.exe')))
    modulos = Path(os.environ.get('TIKTOK_MODULOS', str(dependencias / 'node/node_modules')))
    if not node.is_file() or not (modulos / '@oai/artifact-tool').exists():
        raise RuntimeError('No se encontró el motor de Excel configurado para este equipo. CSV y JSON siguen disponibles.')
    with tempfile.TemporaryDirectory(prefix='tiktok_excel_') as temporal:
        entrada = Path(temporal) / 'entrada.json'
        entrada.write_text(json.dumps(resultado, ensure_ascii=False), encoding='utf-8')
        try:
            proceso = subprocess.run([str(node), str(Path(__file__).with_name('excel.mjs')), str(entrada), str(destino), str(modulos)], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=180)
        except subprocess.TimeoutExpired as error:
            raise RuntimeError('La creación del Excel superó el tiempo de espera. Los resultados CSV/JSON se conservan.') from error
        if proceso.returncode:
            raise RuntimeError('No se pudo crear Excel. Los resultados CSV/JSON se conservan; revisa la configuración del motor de hojas de cálculo.')
    return Path(destino)
