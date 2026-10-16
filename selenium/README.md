# Extracción pública de Band-Maid con Selenium y Pandas

Programa modular para navegar la página pública de Band-Maid, extraer sus fichas de `#miembros` y procesarlas con Pandas. Selenium abre Edge de forma visible por defecto (o Chrome con `--browser chrome`) y usa esperas explícitas. El sitio no ofrece controles propios de búsqueda ni paginación, así que `--query`, `--offset` y `--limit` se aplican localmente al DataFrame.

## Instalación y uso

Desde esta carpeta:

```powershell
python -m pip install -r requirements.txt
python main.py
```

El menú de la terminal ofrece estas opciones:

1. **Extraer información de la web (scraping):** abre la página pública, extrae las fichas de `#miembros` y guarda el CSV. Los parámetros de scraping siguen disponibles, por ejemplo:

   ```powershell
   python main.py --browser edge --query "Miku" --limit 1 --screenshot
   ```

2. **Probar el registro sin CAPTCHA:** hace primero un GET de CSRF y después un único POST de registro omitiendo los datos del CAPTCHA; se espera que el servidor rechace el intento.
3. **Probar el límite de solicitudes (rate limit):** envía como máximo seis POST secuenciales de inicio de sesión y se detiene en la primera respuesta HTTP 429.
0. **Salir** sin iniciar una operación.

Al terminar cada operación, el programa vuelve al menú, también si ocurre un error o el servidor rechaza la solicitud de prueba.

## Registro de actividad

Los eventos se guardan en `salida/selenium.log` en UTF-8. Cada línea usa el formato `[PID] [fecha,milisegundos] NIVEL [archivo.py:línea] ==> mensaje`. El archivo se escribe en modo append y rota al alcanzar 5 MB, conservando tres respaldos (`selenium.log.1` a `selenium.log.3`).

El navegador correspondiente debe estar instalado. Selenium Manager gestiona el controlador cuando sea necesario. `python main.py --help` muestra las opciones de línea de comandos, incluido `--browser` (`edge` por omisión o `chrome`).

## Flujo de trabajo

- Abre la página pública y pulsa el enlace visible a `#miembros`.
- Extrae nombre, función, texto alternativo de imagen y URL de cada ficha.
- Normaliza el texto, descarta registros sin los campos requeridos, agrega la fecha de extracción y muestra el DataFrame procesado.
- `--query` busca texto localmente, sin distinguir mayúsculas; `--offset` y `--limit` permiten recorrer una porción de la tabla.
- Guarda cada resultado en un CSV con nombre único dentro de `salida/`; `--screenshot` guarda una captura PNG de la página visible en la misma carpeta.

El scraping de la opción 1 no inicia sesión ni envía formularios. Si detecta CAPTCHA, acceso denegado o una verificación humana, pausa para revisión manual y detiene la extracción; no intenta resolver ni sortear el desafío.

Las pruebas de seguridad de las opciones 2 y 3 solo se ejecutan contra `https://bandmaid-abcd123.vercel.app/`. El destino está fijado en el programa: no se puede cambiar a localhost ni configurar otra URL.
