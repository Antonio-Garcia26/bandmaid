# Extracción pública de Band-Maid con Selenium y Pandas

Programa modular para navegar la página pública de Band-Maid, extraer sus fichas de `#miembros` y procesarlas con Pandas. Selenium abre Edge de forma visible por defecto (o Chrome con `--browser chrome`) y usa esperas explícitas. El sitio no ofrece controles propios de búsqueda ni paginación, así que `--query`, `--offset` y `--limit` se aplican localmente al DataFrame.

## Instalación y uso

Desde esta carpeta:

```powershell
python -m pip install -r requirements.txt
python main.py --browser edge
python main.py --browser edge --query "Miku" --limit 1 --screenshot
```

El navegador correspondiente debe estar instalado. Selenium Manager gestiona el controlador cuando sea necesario.

## Flujo de trabajo

- Abre la página pública y pulsa el enlace visible a `#miembros`.
- Extrae nombre, función, texto alternativo de imagen y URL de cada ficha.
- Normaliza el texto, descarta registros sin los campos requeridos, agrega la fecha de extracción y muestra el DataFrame procesado.
- `--query` busca texto localmente, sin distinguir mayúsculas; `--offset` y `--limit` permiten recorrer una porción de la tabla.
- Guarda cada resultado en un CSV con nombre único dentro de `salida/`; `--screenshot` guarda una captura PNG de la página visible en la misma carpeta.

El script no inicia sesión ni envía formularios. Si detecta CAPTCHA, acceso denegado o una verificación humana, pausa para revisión manual y detiene la extracción; no intenta resolver ni sortear el desafío.
