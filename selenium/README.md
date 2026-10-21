# Automatización, Auditoría y Extracción con Selenium y Pandas

Programa modular para automatización web, análisis de seguridad perimetral y extracción estructurada de datos públicos mediante Selenium WebDriver y Pandas.

---

## Cumplimiento de los 5 Requerimientos Técnicos

| # | Requerimiento | Implementación en el Código |
|---|---|---|
| **1** | **Navegación y Localización** | Búsqueda dinámica con Selenium WebDriver (`send_keys` + `Keys.ENTER`), selección interactiva de filtros de formato/categoría (clic en facetas del DOM y fallback inteligente), y navegación paginada dinámica con `WebDriverWait`. |
| **2** | **Manejo Ético de Barreras** | Identificación de límites y retos antibot (Cloudflare Turnstile, reCAPTCHA, hCaptcha, Rate Limiting 429). Si se detecta un desafío, el script se pausa respetuosamente solicitando la intervención del operador humano para resolverlo en la ventana del navegador y **continuar** la extracción dinámicamente. |
| **3** | **Extracción Estructurada** | Localizadores robustos híbridos (`By.CSS_SELECTOR` y `By.XPATH`), selectores de respaldo para elementos dinámicos, extracción limpia de metadatos (título, organización, categoría, cantidad de recursos, descripción, fecha y URL). |
| **4** | **Procesamiento y Limpieza (Pandas)** | Transformación con Pandas: eliminación de caracteres no imprimibles y espacios redundantes (`_limpiar_caracteres_especiales`), normalización de fechas a ISO `YYYY-MM-DD` (`_normalizar_fecha`), y normalización de valores numéricos (`_normalizar_numero` para métricas como `num_resources` y `page`). |
| **5** | **Almacenamiento Persistente** | Persistencia multicanal: Base de datos relacional **SQLite** (`salida/datos_oficiales.db`), archivos estructurados **CSV** (con BOM UTF-8), archivos estructurados **JSON**, archivos **Excel** (`.xlsx` vía `openpyxl`), y adaptador opcional para **PostgreSQL**. |

---

## Instalación y Configuración

Desde el directorio `selenium/`:

```powershell
python -m pip install -r requirements.txt
python main.py
```

### Dependencias Principales (`requirements.txt`)
- `selenium>=4.20,<5`: Automatización del navegador visible con Selenium Manager.
- `pandas>=2.0,<4`: Procesamiento, limpieza y estructuración de datos.
- `openpyxl>=3.1.0`: Generación de hojas de cálculo Excel (`.xlsx`).
- `requests>=2.31.0`: Auditoría HTTP de cabeceras, WAF y directivas `robots.txt`.

---

## Menú Interactivo de la Aplicación

Al ejecutar `python main.py`, se despliega el menú en consola con las pruebas individuales y módulos:

```text
=== Menú de Automatización, Seguridad y Extracción ===
1. Extraer fichas de Band-Maid (Scraping local/propio)
2. [Seguridad 1/5] Probar CAPTCHA (Omisión de código de verificación HTTP 400)
3. [Seguridad 2/5] Probar Rate Limit (Ráfaga de solicitudes concurrentes HTTP 429)
4. [Seguridad 3/5] Probar Protección Anti-CSRF (Token manipulado HTTP 403)
5. [Seguridad 4/5] Probar Trampa Honeypot (Campo oculto bot HTTP 400)
6. [Seguridad 5/5] Probar Telemetría y Automatización (Webdriver/Bot HTTP 400)
7. [Seguridad Batería] Ejecutar los 5 métodos de seguridad en secuencia
8. [Fase 2] Auditar y clasificar los 5 sitios web (Básico, Intermedio, Avanzado)
9. [Fase 3] Extraer datos de Portal Oficial (Búsqueda + Filtros + SQLite + CSV)
10. [Fase 3] Consultar base de datos SQLite de datos oficiales
0. Salir
```

---

## Las 5 Pruebas Individuales de Seguridad

| # | Método de Seguridad | Escenario de Ataque Evaluado | Respuesta Esperada del Servidor |
|---|---|---|---|
| **1** | **CAPTCHA** | Envía formulario de registro omitiendo token y respuesta de CAPTCHA. | `HTTP 400 · CAPTCHA_INVALID` |
| **2** | **Rate Limiting** | Ráfaga de solicitudes POST secuenciales de inicio de sesión. | `HTTP 429 · RATE_LIMITED` |
| **3** | **Protección Anti-CSRF** | Envía mutación POST con encabezado `X-CSRF-Token` manipulado o ausente. | `HTTP 403 · CSRF_REJECTED` |
| **4** | **Trampa Honeypot** | Envía formulario con el campo oculto `website` completado por un bot. | `HTTP 400 · BOT_REJECTED` |
| **5** | **Telemetría y Webdriver** | Envía telemetría con `isWebdriver: true` y velocidad inhumana (<1.2s). | `HTTP 400 · BOT_BEHAVIOR_DETECTED` |

---

## Ejemplos de Uso por Línea de Comandos

```powershell
# Iniciar con Edge (predeterminado) o Chrome
python main.py
python main.py --browser chrome

# Ejecución individual de cada prueba de seguridad por CLI:
python main.py --security-test captcha
python main.py --security-test rate-limit
python main.py --security-test csrf
python main.py --security-test honeypot
python main.py --security-test telemetry
python main.py --security-test all

# Extracción en portal oficial con búsqueda, filtro y paginación
python main.py --portal datos_cdmx --query "movilidad" --filter "csv" --pages 2 --screenshot
python main.py --portal data_gov --query "education" --filter "csv" --pages 2


# Paginación y límite sobre el DataFrame resultante
python main.py --portal datos_cdmx --query "salud" --offset 2 --limit 5
```

---

## Estructura de Salidas (`salida/`)

Todos los artefactos generados se guardan de forma persistente en la carpeta `salida/`:
- `datos_oficiales.db`: Base de datos SQLite persistente con tablas `datasets_oficiales` y `auditoria_sitios`.
- `*.csv`: Datasets tabulares limpios y listos para análisis.
- `*.json`: Datasets estructurados en formato JSON.
- `*.xlsx`: Hojas de cálculo Excel nativas.
- `selenium.log`: Registro de eventos rotativo con timestamp, nivel de severidad y PID.
