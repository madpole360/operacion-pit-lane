"""
Generador de páginas HTML para el sitio de Operación Pit-Lane.
Usa Jinja2 para renderizar las plantillas con los datos de investigación.
"""
import json
import re
import sys
from datetime import datetime, timedelta
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

    # Calcular próxima ejecución (lunes y jueves 20:00 Madrid)
    now = datetime.now()
    next_run = None
    for d in range(8):
        check = now + timedelta(days=d)
        if check.weekday() in (0, 3):  # lunes=0, jueves=3
            if d == 0 and check.hour < 20:
                next_run = check.replace(hour=20, minute=0, second=0, microsecond=0)
                break
            elif d > 0:
                next_run = check.replace(hour=20, minute=0, second=0, microsecond=0)
                break
    if next_run is None:
        next_run = now + timedelta(days=1)
    dias_es = {0: 'Lunes', 1: 'Martes', 2: 'Miércoles', 3: 'Jueves', 4: 'Viernes', 5: 'Sábado', 6: 'Domingo'}
    next_run_str = f"{dias_es[next_run.weekday()]} {next_run.strftime('%d/%m')} a las 20:00"

    # Datos comunes — ordenar contratos por descubierto DESC, luego fecha DESC
    contracts_db = load_json(CONTRACTS_FILE, [])
    contracts_db.sort(key=lambda c: (c.get("descubierto_el") or "", c.get("fecha") or ""), reverse=True)
    # Separar licitaciones de contratos menores
    licitaciones = [c for c in contracts_db if re.match(r"^\d{2}/\d{3,4}", c.get("expediente", ""))]
    menores = [c for c in contracts_db if not re.match(r"^\d{2}/\d{3,4}", c.get("expediente", ""))]
    # Desglose por categorias
    categorias = _build_categories(contracts_db)
    timeline = load_json(TIMELINE_FILE, [])
    archive_files = sorted(
        [f.name for f in ARCHIVE_DIR.glob("*.json")],
        reverse=True
    )

    ctx = {
        "data": latest_data,
        "contracts_db": contracts_db,
        "licitaciones": licitaciones,
        "contratos_menores": menores,
        "categorias": categorias,
        "timeline": timeline,
        "archive_files": archive_files,
        "today": datetime.now().strftime("%Y-%m-%d"),
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "next_run": next_run_str,
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

    # ── Indice del archivo ──
    _generate_archive_index(archive_files)


def _generate_archive_index(files: list):
    """Genera docs/archive/index.html con listado de informes historicos."""
    rows = ""
    for f in files:
        date_str = f.replace(".json", "")
        rows += f'<tr><td style="font-family:monospace;">{date_str}</td><td><a href="{f}">JSON</a></td></tr>\n'

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Historico de informes — Operacion Pit-Lane</title>
  <style>
    body {{ background:#0C0C0F; color:#EBEBF0; font-family:Inter,system-ui,sans-serif; max-width:600px; margin:2rem auto; padding:1rem; }}
    h1 {{ font-size:1.2rem; color:#F59E0B; }}
    table {{ width:100%; border-collapse:collapse; margin-top:1rem; }}
    th, td {{ padding:.5rem .75rem; text-align:left; border-bottom:1px solid #2C2C3A; }}
    th {{ color:#6B7280; font-size:.7rem; text-transform:uppercase; }}
    a {{ color:#60A5FA; }}
    .back {{ font-size:.8rem; margin-bottom:1rem; }}
  </style>
</head>
<body>
  <p class="back"><a href="../index.html">← Volver al informe</a></p>
  <h1>Historico de informes diarios</h1>
  <p style="color:#6B7280;font-size:.8rem;">{len(files)} informes almacenados</p>
  <table>
    <thead><tr><th>Fecha</th><th>Archivo</th></tr></thead>
    <tbody>{rows if rows else '<tr><td colspan="2">Sin informes todavia</td></tr>'}</tbody>
  </table>
  <p style="color:#3A3A4A;font-size:.7rem;margin-top:1.5rem;">Operacion Pit-Lane · Datos de fuentes oficiales publicas</p>
</body>
</html>"""
    (ARCHIVE_DIR / "index.html").write_text(html, encoding="utf-8")
    print("✅ archive/index.html generado")


def _build_categories(contracts: list) -> dict:
    """Categoriza contratos y devuelve desglose de costes por tipo."""
    cat_map = {
        "Obra civil": re.compile(r"obra|construcci|asfaltado|pabell|pit.build|edificio|urbaniz|paviment|reposici",
                                 re.IGNORECASE),
        "Asistencia técnica": re.compile(r"asistencia|asesor|consultor|control.*calidad|supervisi|direcci.*obra|"
                                         r"project.*management|comissioning|pliego|estudios? (cuantitativo|de mercado)",
                                         re.IGNORECASE),
        "Servicios operativos": re.compile(r"montaje|desmontaje|mantenimiento|vigilancia|bombero|medicin|emergencia|"
                                           r"personal|ett|azafata|protocolo|acreditaci|prensa|limpieza|aseos|wc|"
                                           r"carpas|pasarela|modulo|oficina|generaci|electric|ruido|calidad.*aire|"
                                           r"hospitality|catering|transporte|logístic",
                                           re.IGNORECASE),
        "Suministros": re.compile(r"suministro|cesped|extintor|lonas|pantalla|fibra|alumbrado|iluminaci|megafon|"
                                  r"tornos|conectividad|bandera|trofeo",
                                  re.IGNORECASE),
        "Seguros": re.compile(r"seguro|rc\b|responsabilidad civil|póliza", re.IGNORECASE),
        "Marketing y comunicación": re.compile(r"comunicaci|marketing|branding|publicidad|promoci|redes social|"
                                                r"audiovisual|fotograf|influencer|merchandising|agencia creativa|"
                                                r"experiencia.*marca|fan.zone|show.run",
                                                re.IGNORECASE),
        "Patrocinios": re.compile(r"patrocinador|sponsor|santander|ford|corte.ingl|heineken", re.IGNORECASE),
    }

    categories = {k: {"total": 0, "count": 0, "color": "", "items": []} for k in cat_map}
    colors = ["#E10600", "#F59E0B", "#60A5FA", "#34D399", "#C084FC", "#FB923C", "#F87171"]

    for i, (name, pattern) in enumerate(cat_map.items()):
        categories[name]["color"] = colors[i]
        for c in contracts:
            concepto = c.get("concepto", "")
            if pattern.search(concepto):
                imp = c.get("importe", 0) or 0
                est = c.get("estado", "")
                # Solo adjudicado/ejecutado para el grafico de confirmado
                if est in ("adjudicado", "ejecutado"):
                    categories[name]["total"] += imp
                categories[name]["count"] += 1
                categories[name]["items"].append(c.get("expediente", ""))

    # Ordenar por total descendente
    result = {
        "categories": dict(sorted(categories.items(), key=lambda x: x[1]["total"], reverse=True)),
        "total_confirmado": sum(v["total"] for v in categories.values()),
    }
    return result


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
