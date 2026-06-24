"""
Generador de páginas HTML para el sitio de Operación Pit-Lane.
Usa Jinja2 para renderizar las plantillas con los datos de investigación.
"""
import json
import sys
from datetime import datetime
from pathlib import Path

# Fix Windows encoding for emoji output
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT / "docs"
TEMPLATES_DIR = ROOT / "templates"
ARCHIVE_DIR = DOCS_DIR / "archive"
CONTRACTS_FILE = DOCS_DIR / "contracts.json"
DATA_DIR = ROOT / "data"
TIMELINE_FILE = DATA_DIR / "timeline.json"


def load_json(path: Path, default=None):
    """Carga un JSON de forma segura."""
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return default if default is not None else {}


def build_site(latest_data: dict):
    """Genera index.html y valencia.html."""
    from jinja2 import Environment, FileSystemLoader

    DOCS_DIR.mkdir(exist_ok=True)
    ARCHIVE_DIR.mkdir(exist_ok=True)

    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))

    # Datos comunes — ordenar contratos por descubierto DESC, luego fecha DESC
    contracts_db = load_json(CONTRACTS_FILE, [])
    contracts_db.sort(key=lambda c: (c.get("descubierto_el") or "", c.get("fecha") or ""), reverse=True)
    timeline = load_json(TIMELINE_FILE, [])
    archive_files = sorted(
        [f.name for f in ARCHIVE_DIR.glob("*.json")],
        reverse=True
    )

    ctx = {
        "data": latest_data,
        "contracts_db": contracts_db,
        "timeline": timeline,
        "archive_files": archive_files,
        "today": datetime.now().strftime("%Y-%m-%d"),
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

    # ── Página principal ──
    template = env.get_template("index.html.j2")
    html = template.render(**ctx)
    (DOCS_DIR / "index.html").write_text(html, encoding="utf-8")
    print("✅ index.html generado")

    # ── Pagina Valencia ──
    template_v = env.get_template("valencia.html.j2")
    html_v = template_v.render(**ctx)
    (DOCS_DIR / "valencia.html").write_text(html_v, encoding="utf-8")
    print("✅ valencia.html generado")

    # ── Pagina Acerca de ──
    template_a = env.get_template("acerca.html.j2")
    html_a = template_a.render(**ctx)
    (DOCS_DIR / "acerca.html").write_text(html_a, encoding="utf-8")
    print("✅ acerca.html generado")
    template_v = env.get_template("valencia.html.j2")
    html_v = template_v.render(**ctx)
    (DOCS_DIR / "valencia.html").write_text(html_v, encoding="utf-8")
    print("✅ valencia.html generado")


def generate_initial_site():
    """Genera un sitio inicial con datos placeholder (sin investigación previa)."""
    placeholder = {
        "fecha": datetime.now().strftime("%Y-%m-%d"),
        "fecha_madrid": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "resumen_ejecutivo": "🕐 El agente investigador está configurado y se ejecutará cada día a las 21:00h (hora Madrid). El primer informe con datos reales se generará en la próxima ejecución programada.",
        "nuevos_hallazgos": ["Agente desplegado y a la espera de la primera ejecución"],
        "contratos": [],
        "coste_acumulado_confirmado": 0,
        "coste_acumulado_texto": "Pendiente de primera investigación",
        "incremento_respecto_anterior": 0,
        "partidas_pendientes_confirmar": [
            "Canon a FOM / Liberty Media por los derechos del GP",
            "Presupuesto total de obras de adecuación del circuito",
            "Contratos de IFEMA para la organización del evento",
            "Convenios entre Comunidad de Madrid, Ayuntamiento e IFEMA",
            "Costes de seguridad, movilidad y servicios públicos"
        ],
        "riesgos_detectados": [
            "Falta de transparencia: aún no se han publicado todos los convenios institucionales",
            "Posible infraestimación de costes indirectos (seguridad, transporte, limpieza)"
        ],
        "comparativa_valencia": {
            "coste_total_valencia": 0,
            "coste_total_valencia_texto": "~350 millones de euros (coste total estimado del circuito urbano de Valencia 2008-2012)",
            "coste_acumulado_madrid": 0,
            "coste_acumulado_madrid_texto": "Pendiente de determinar",
            "factores_riesgo_compartidos": [
                "Circuito urbano/semiurbano con necesidades de adaptación de viales",
                "Alta dependencia de fondos públicos",
                "Promesas de retorno económico sin estudios independientes",
                "Opacidad en los convenios entre administraciones",
                "Infraestructuras temporales que requieren mantenimiento recurrente"
            ],
            "porcentaje_similitud_riesgo": 60,
            "justificacion": "Estimación preliminar. A la espera de datos concretos de contratación para ajustar el porcentaje."
        },
        "fuentes_consultadas": [
            "https://contrataciondelestado.es",
            "https://www.boe.es",
            "https://www.madrid.es",
            "https://www.comunidad.madrid",
            "https://www.ifema.es",
            "https://transparencia.gob.es"
        ]
    }
    build_site(placeholder)
    return placeholder


if __name__ == "__main__":
    print("🏗️  Generando sitio inicial...")
    data = generate_initial_site()
    print("✅ Sitio inicial generado en docs/")
