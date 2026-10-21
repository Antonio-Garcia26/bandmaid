"""Configuración del recolector y auditor de sitios web."""

BANDMAID_URL = "https://bandmaid-abcd123.vercel.app/"
OUTPUT_DIR_NAME = "salida"
WAIT_SECONDS = 12

BANDMAID_SELECTORS = {
    "members_link": "a[href='#miembros']",
    "members_section": "#miembros",
    "cards": "#miembros article.member-card",
    "name": ".member-name",
    "role": ".member-role",
    "image": "img[alt]",
}

# --- FASE 2: 5 Sitios para Auditoría Comparativa (Básico, Intermedio, Avanzado) ---
AUDIT_TARGETS = [
    {
        "id": "loc_gov",
        "nombre": "Library of Congress (Colecciones Públicas Oficiales)",
        "url": "https://www.loc.gov/collections/",
        "robots_url": "https://www.loc.gov/robots.txt",
        "nivel_esperado": "Básico",
        "tipo_fuente": "Portal Oficial Gubernamental (EE.UU.)",
        "descripcion": "Estructura HTML semántica estándar, metadatos abiertos, paginación por parámetros de URL, robots.txt permisivo para catálogos.",
        "viabilidad_legal": "Alta: Contenido de dominio público del gobierno federal, robots.txt permite indexación de colecciones con crawl-delay moderado.",
    },
    {
        "id": "data_gov",
        "nombre": "Catálogo Federal de Datos Abiertos de EE.UU. (Data.gov)",
        "url": "https://catalog.data.gov/dataset",
        "robots_url": "https://catalog.data.gov/robots.txt",
        "nivel_esperado": "Básico",
        "tipo_fuente": "Catálogo Federal Oficial de Datos Abiertos",
        "descripcion": "Estructura CKAN semántica, HTML estructurado con paginación tradicional por URL, sin WAF bloqueante agresivo, robots.txt permisivo para catálogos.",
        "viabilidad_legal": "Alta: Dominio público de EE.UU. bajo la política federal Open Data Policy (M-13-13). Reutilización irrestricta.",
    },
    {
        "id": "datos_cdmx",
        "nombre": "Portal de Datos Abiertos de la Ciudad de México",
        "url": "https://datos.cdmx.gob.mx/dataset/",
        "robots_url": "https://datos.cdmx.gob.mx/robots.txt",
        "nivel_esperado": "Intermedio",
        "tipo_fuente": "Portal Oficial de Transparencia y Datos Abiertos (Gobierno CDMX)",
        "descripcion": "Renderizado dinámico con JavaScript/React y CKAN, llamadas asíncronas AJAX para filtrado interactivo y paginación facetada.",
        "viabilidad_legal": "Alta: Política de Datos Abiertos de CDMX, reutilización libre sin restricciones comerciales.",
    },
    {
        "id": "data_worldbank",
        "nombre": "Banco Mundial - Indicadores de Datos Abiertos (data.worldbank.org)",
        "url": "https://data.worldbank.org/indicator",
        "robots_url": "https://data.worldbank.org/robots.txt",
        "nivel_esperado": "Intermedio",
        "tipo_fuente": "Organismo Multilateral Oficial Internacional",
        "descripcion": "Single Page Application (SPA) con carga diferida intensiva, hidratación React, APIs REST internas y gráficos dinámicos.",
        "viabilidad_legal": "Alta: Términos de uso de datos abiertos del Banco Mundial (Creative Commons CC BY 4.0).",
    },
    {
        "id": "bandmaid_security",
        "nombre": "World Domination Club (Portal Propio con Protección Perimetral)",
        "url": "https://bandmaid-abcd123.vercel.app/",
        "robots_url": "https://bandmaid-abcd123.vercel.app/robots.txt",
        "nivel_esperado": "Avanzado",
        "tipo_fuente": "Aplicación Web con WAF y Defensas Propias",
        "descripcion": "Protección perimetral Cloudflare, verificación Turnstile/CAPTCHA, telemetría de interacción humana (cadencia y mouse), rate limit estricto (5 req/min con 429) y honeypot.",
        "viabilidad_legal": "Autorizada en el entorno de desarrollo y pruebas de seguridad éticas controladas.",
    },
]

# --- FASE 3: Configuración de Portales Oficiales para Extracción Dinámica ---
OFFICIAL_PORTALS = {
    "datos_cdmx": {
        "nombre": "Portal de Datos Abiertos de la Ciudad de México",
        "url": "https://datos.cdmx.gob.mx/dataset/",
        "search_input": "input.dataset-search-input, input[name='q']",
        "search_button": "button.dataset-search-button, button[type='submit']",
        "cards": ".card.dataset-card, .dataset-item",
        "title": "h5.card-title a, h3 a, .dataset-heading a",
        "organization": ".card-text",
        "category": "span.text-aqua, .dataset-topic, .badge",
        "description": "p.card-text",
        "pagination_next": "ul.pagination li a[rel='next'], ul.pagination li:last-child a",
        "default_query": "salud",
    },
    "data_gov": {
        "nombre": "Catálogo Federal de Datos Abiertos de EE.UU. (Data.gov)",
        "url": "https://catalog.data.gov/dataset",
        "search_input": "input#search-big-input, input[name='q'], input#q",
        "search_button": "button[type='submit']",
        "cards": ".dataset-content, .dataset-item",
        "title": "h3.usa-collection__heading a, .dataset-heading a",
        "organization": ".usa-collection__meta-item a, .dataset-organization",
        "category": ".usa-tag, .tag",
        "description": ".dataset-description, .usa-collection__description",
        "pagination_next": "a.usa-pagination__next-page, .pagination a[rel='next']",
        "default_query": "health",
    },
}
