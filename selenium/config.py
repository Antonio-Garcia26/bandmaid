"""Configuración del recolector de la página pública de Band-Maid."""

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
