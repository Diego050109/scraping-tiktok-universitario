# Scraping de TikTok

Proyecto universitario de Python para consultar una cuenta pública desde la terminal, guardar los datos recibidos y analizar las descripciones disponibles.

**Estado actual:** la consulta del perfil funcionó en varias cuentas, pero la extracción de videos falló en las pruebas documentadas. El programa no garantiza obtener los diez últimos videos de una cuenta cualquiera. No presenta datos guardados como si fueran una consulta nueva.

## Cómo ejecutarlo en Visual Studio Code

Abre la carpeta del proyecto con **File → Open Folder** y abre **Terminal → New Terminal**.

Si todavía no tienes un entorno virtual, créalo una sola vez:

```powershell
py -3 -m venv .venv
```

Instala las dependencias y Chromium:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m playwright install chromium
```

Ejecuta el programa:

```powershell
.\.venv\Scripts\python.exe -m src.main
```

Escribe el username con o sin `@`. El programa muestra el perfil y hasta diez videos que consiga recibir. Guarda CSV y JSON en `data/`. Si hay videos intenta generar también un Excel. Si hay descripciones, permite conversar con Gemini en la misma terminal.

Escribe `salir` para terminar. En el chat puedes usar `/otra` para consultar otra cuenta o `/nueva` para borrar la conversación. El comando anterior `python -m src.consola` también sigue funcionando.

## Archivos del proyecto

```text
src/
  main.py          Inicia el programa.
  consola.py       Preguntas, resultados y conversación en la terminal.
  scraper.py       Consulta pública con Playwright y control de restricciones.
  parser.py        Valida el username, interpreta JSON y ordena los videos.
  exportar.py      Guarda CSV y JSON sin sobrescribir archivos anteriores.
  analisis.py      Cuenta palabras y señales en las descripciones.
  chat_ia.py       Envía preguntas y fuentes a Gemini; clave solo en memoria.
  excel.py         Ejecuta el exportador de Excel opcional.
  excel.mjs        Construye las hojas y gráficos de Excel.
data/              Resultados locales; no se publican en Git.
docs/PRUEBAS.md     Resumen de las pruebas reales y las limitaciones.
tests/             Pruebas automatizadas con datos sintéticos.
requirements.txt   Dependencia principal: Playwright.
.gitignore         Excluye entorno virtual, claves, datos y respaldo local.
```

`__init__.py` indica que `src` es un paquete de Python. Tu cuaderno original permanece en la raíz, sin modificar; conserva los ensayos previos y se excluye de Git porque puede contener salidas y metadatos locales. La aplicación se ejecuta con los archivos de `src/`, no con todas las celdas del cuaderno.

## Datos ausentes y restricciones

- `null` en JSON y una celda vacía en CSV significan dato no disponible. Un cero se conserva solo si llegó de la fuente.
- Un listado con cero videos recuperados no demuestra que la cuenta no tenga publicaciones.
- Se ordena por fecha recibida. Las fechas ausentes, los anclados y una carga incompleta impiden garantizar los diez últimos de toda la cuenta.
- La consulta se detiene ante verificaciones o rechazos. No usa la API oficial de TikTok, sesiones privadas, proxies ni resolución de CAPTCHA.

Playwright abre una sesión nueva de Chromium y lee el JSON y los enlaces públicos que recibe la página. El perfil puede estar disponible aunque el listado de videos llegue vacío.

## Chat y Excel

El chat es opcional. Requiere una clave de Gemini de un proyecto Free Tier sin facturación. La clave se introduce oculta y no se guarda en archivos. Google recibe las fuentes públicas y las preguntas; el nivel gratuito tiene límites y puede utilizar ese contenido para mejorar productos. La aplicación no comprueba la facturación de tu proyecto. No publiques tu clave.

La interpretación Big Five describe señales del contenido. No es una prueba de personalidad, diagnóstico ni porcentaje psicométrico. Sin descripciones no se abre ese análisis.

El Excel conserva el exportador configurado en este equipo: `excel.py` llama a un script de Node.js (`excel.mjs`) que usa `@oai/artifact-tool`. Ese motor no se instala con `requirements.txt`. Si no está disponible, el programa informa el problema y conserva CSV y JSON. Los gráficos representan estadísticas recibidas y señales textuales, no puntuaciones de personalidad.

## Pruebas y GitHub

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
git status
git diff --cached --check
```

Los tests usan datos sintéticos y respuestas simuladas. Comprueban el manejo de errores y los cálculos; no demuestran que TikTok permita obtener videos en vivo. El resultado de las consultas reales está en `docs/PRUEBAS.md`.

Se conservaron las herramientas de investigación, la interfaz web anterior y sus pruebas en `_respaldo_local/`. Ese respaldo, `.venv`, el cuaderno original y los resultados de `data/` quedan fuera de Git. VS Code oculta localmente el entorno y el respaldo para facilitar la navegación; los archivos siguen en el disco.

Antes de publicar revisa `git diff --cached`. Mensaje de commit propuesto:

```powershell
git commit -m "Organizar proyecto de scraping de TikTok"
```

Repositorio privado: https://github.com/Diego050109/scraping-tiktok-universitario. La rama principal es `main`. Para guardar cambios futuros revisa `git status`, selecciona los archivos con `git add`, crea un commit y usa `git push`. No publiques contraseñas, cookies ni claves de Gemini.
