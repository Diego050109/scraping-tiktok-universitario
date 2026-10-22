# Pruebas del proyecto

Las consultas reales se hicieron el 22 de octubre de 2026, sin capturas preparadas, cookies privadas ni resolución de verificaciones.

| Cuenta | Técnica | Perfil recibido | Videos recuperados |
|---|---|---|---:|
| nasa | Playwright, JSON y DOM públicos | Sí | 0 |
| natgeo | Playwright, JSON y DOM públicos | Sí | 0 |
| duolingo | yt-dlp con funciones restringidas | No | 0 |
| espn | Comparación de HTML inicial, JSON y DOM | Sí | 0 |
| guinnessworldrecords | Comparación de HTML inicial, JSON y DOM | Sí | 0 |

En NASA y National Geographic el listado respondió HTTP 200 con cero bytes y se detectó una verificación. El perfil estaba disponible en los datos de la página. En la prueba de yt-dlp se recibió una página de verificación; no se resolvió ni se reintentó.

En ESPN y Guinness World Records no aparecieron enlaces de videos ni identificadores utilizables en el HTML/JSON inspeccionado o en el DOM. Se esperaron tres intervalos de dos segundos. El listado llegó con cero bytes en ambas cuentas; en Guinness apareció una verificación en el tercer intervalo. No se visitaron páginas de videos ni se comprobaron fechas porque no se encontraron candidatos.

**Conclusión:** la extracción de perfiles está comprobada en algunas cuentas, pero no se consiguió recuperar videos de las cuentas nuevas probadas. El requisito de obtener los diez últimos videos de una cuenta arbitraria solo con el username sigue pendiente. Un HTTP 200 sin contenido no equivale a una lista válida ni a una cuenta sin publicaciones.

El Excel y el chat se comprobaron previamente con una captura pública guardada de `mayerli_anahi`. Eso demuestra el procesamiento de las descripciones disponibles, no la extracción automática de una cuenta nueva.

Los resultados públicos se conservan localmente en `data/`. Los informes detallados y las herramientas de auditoría están en `_respaldo_local/`, excluidos de Git. Las pruebas automatizadas activas se ejecutan con:

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
```

Esas pruebas son sintéticas: no hacen peticiones a TikTok ni a Gemini y no deben presentarse como resultados de scraping real.
