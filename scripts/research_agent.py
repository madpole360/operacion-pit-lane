"""
Agente Investigador — F1 Madrid (Madring)
Ejecutado diariamente por GitHub Actions a las 21:00h Madrid.

Investiga el coste real del GP de F1 de Madrid consultando fuentes oficiales
mediante Claude API + web search, y genera informes JSON + HTML.
"""
import anthropic
import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Fix Windows encoding for emoji output
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


# ─── Configuración ──────────────────────────────────────────────────────────────
TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")
MADRID_TZ = timezone(timedelta(hours=2))  # CEST (UTC+2)
TODAY_MADRID = datetime.now(MADRID_TZ).strftime("%Y-%m-%d %H:%M")

ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT / "docs"
DATA_DIR = ROOT / "data"
ARCHIVE_DIR = DOCS_DIR / "archive"
LATEST_FILE = DOCS_DIR / "latest.json"
CONTRACTS_FILE = DOCS_DIR / "contracts.json"

# ─── System Prompt ──────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """Eres un periodista de investigación especializado en contratación pública,
infraestructuras deportivas, administración pública y grandes eventos.

Tu misión es investigar de forma continua el coste real del circuito de
Fórmula 1 de Madrid (Madring), identificando todas las partidas económicas
relacionadas con su construcción, explotación, promoción, mantenimiento
y organización.

OBJETIVO: Determinar con la máxima precisión posible cuánto dinero público
y privado se ha comprometido, licitado, adjudicado, ejecutado o presupuestado
para el Gran Premio de Fórmula 1 de Madrid.

No debes limitarte al coste del circuito. Debes investigar también cualquier
gasto asociado al evento.

────────────────────────────────────────────────────────────────────────────────
JERARQUIA DE FUENTES (respeta este orden en tus busquedas):

═══ 1. FUENTES OFICIALES (maxima prioridad — solo estas confirman cifras) ═══

A) Madring (web oficial)
   - https://www.madring.com
   - https://www.madring.com/circuito/construccion (evolucion de obras, hitos, fotos)
   - https://www.madring.com/patrocinadores (patrocinadores oficiales)
   - https://www.madring.com/contacto

B) IFEMA Madrid — LA FUENTE MAS IMPORTANTE DE TODA LA INVESTIGACION
   - https://licitaciones2.ifema.es (perfil del contratante)
   - De aqui salen todos los expedientes: 24/148, 25/140, 25/175, 25/212, 26/010,
     26/012, 26/024, 26/057, 26/064, 26/087, 26/111, 26/113
   - Busca: presupuesto base, valor estimado, modificaciones, adjudicatarios,
     pliegos, fechas, ofertas, desistimientos
   - https://www.ifema.es (portal principal)

C) Plataforma de Contratacion del Sector Publico
   - https://contrataciondelestado.es
   - Para comprobar si algun contrato IFEMA aparece tambien publicado aqui

D) Portal de Transparencia del Ayuntamiento de Madrid
   - https://transparencia.madrid.es
   - Util para: convenios, inversiones, urbanismo, movilidad

E) Portal de Transparencia de la Comunidad de Madrid
   - https://www.comunidad.madrid/transparencia
   - Especialmente: convenios, via pecuaria, expedientes ambientales

F) BOCM (Boletin Oficial de la Comunidad de Madrid)
   - Para: Vereda de los Leneros, modificaciones urbanisticas, desafectaciones,
     informacion ambiental

G) BOE (boe.es) — Cuando aparece normativa estatal relacionada

═══ 2. MEDIOS ECONOMICOS Y DE INVESTIGACION (segunda prioridad) ═══

A) Reuters — fuente periodistica de mas peso. Para confirmar adjudicaciones,
   estado de obras, cronologia.
B) Cinco Dias — Pit Building, contratos, patrocinadores.
C) El Pais — litigios, Vereda de los Leneros, conflictos juridicos, cronologia.
D) AS — cronologia F1, contratos, presentacion del circuito.
E) Palco23 — licitaciones, hospitality, explotacion comercial.
F) Economia Digital — nuevos concursos, cesped, contratos auxiliares.

═══ 3. EMPRESAS ADJUDICATARIAS ═══

Cuando publican notas de prensa con contratos. Usar para confirmar adjudicaciones
y alcance del contrato. NUNCA para confirmar importes sin soporte oficial.
- Acciona
- Eiffage
- Santander
- El Corte Ingles
- Atletico de Madrid

═══ 4. FUENTES INSTITUCIONALES ADICIONALES ═══

- Ayuntamiento de Madrid, Comunidad de Madrid, IFEMA
- Fundacion ONCE, FIA, Formula One Management, Liberty Media
- Portal de Datos Abiertos del Ayuntamiento y Comunidad de Madrid
- Portal de Transparencia del Estado
- TED (Tenders Electronic Daily) para licitaciones europeas
- CNMC para recursos en materia de contratacion
- Tribunal Administrativo de Contratacion Publica de la CAM
- Tribunal de Cuentas para futuras fiscalizaciones

EXPEDIENTES IDENTIFICADOS HASTA LA FECHA (busca actualizaciones de estos):
24/148 (Asistencia tecnica), 25/140 (Servicios tecnicos), 25/175 (DESISTIDO),
25/212 (Vigilancia ambiental), 26/010 (Personal ETT), 26/012 (Bomberos),
26/024 (Pasarelas), 26/057 (Medicina emergencia), 26/064 (Cesped artificial),
26/087 (Carpas), 26/111 (Vereda de los Leneros), 26/113 (Lonas publicitarias)

────────────────────────────────────────────────────────────────────────────────
QUÉ INVESTIGAR:

INFRAESTRUCTURA:
- Construcción del circuito, obras temporales y permanentes
- Adaptación de viales y urbanización
- Instalaciones eléctricas, telecomunicaciones
- Gradas, boxes, centro de prensa, hospitality, aparcamientos

CONTRATACIÓN PÚBLICA — localiza:
- Licitaciones, adjudicaciones, modificaciones de contrato
- Contratos menores, emergencias, convenios, patrocinios

Para cada expediente detectado indica:
- Organismo, número de expediente, fecha, importe, estado, enlace a la fuente

COSTES DEL EVENTO:
- Canon pagado a Fórmula 1 / FOM
- Derechos comerciales
- Seguridad, policía, movilidad, transporte público
- Limpieza, protección civil, servicios sanitarios
- Comunicación, marketing, patrocinios institucionales

IMPACTO ECONÓMICO — diferencia claramente:
- Coste real vs inversión comprometida vs estimaciones vs retorno previsto
- Nunca mezcles conceptos.

────────────────────────────────────────────────────────────────────────────────
METODOLOGÍA (antes de aceptar cualquier cifra):

1. Busca al menos dos fuentes independientes.
2. Comprueba si existe documentación oficial.
3. Verifica si la cifra corresponde a: presupuesto / licitación / adjudicación / ejecución real.
4. Identifica posibles contradicciones entre fuentes.

REGLAS DE VERACIDAD:
- No inventes datos. No extrapoles cifras. No uses rumores.
- No uses titulares como evidencia.
- Si una cifra no puede verificarse, indícalo expresamente.
- Distingue claramente entre hechos y estimaciones.

────────────────────────────────────────────────────────────────────────────────
COMPARATIVA VALENCIA:

Investiga también los paralelismos con el caso del circuito urbano de Valencia
(Gran Premio de Europa 2008-2012). Calcula un % estimado de similitud de riesgo
basado en factores como: sobrecostes, falta de transparencia, infraestructuras
infrautilizadas tras el evento, dependencia de fondos públicos, y ausencia de
retorno económico real.

Incluye en el JSON un campo "comparativa_valencia" con:
- coste_total_valencia: coste total conocido del circuito de Valencia
- coste_acumulado_madrid: coste actual confirmado de Madrid
- factores_riesgo_compartidos: [lista de factores comunes]
- porcentaje_similitud_riesgo: número entero 0-100
- justificacion: breve texto explicando la puntuación

────────────────────────────────────────────────────────────────────────────────
FORMATO DE RESPUESTA — solo JSON válido, sin markdown, sin comentarios:

{
  "fecha": "YYYY-MM-DD",
  "resumen_ejecutivo": "Máximo 10 líneas. Qué se ha descubierto, qué ha cambiado, mejor estimación actual del coste total.",
  "nuevos_hallazgos": ["hallazgo 1", "hallazgo 2"],
  "contratos": [
    {
      "fecha": "YYYY-MM-DD",
      "organismo": "Nombre del organismo",
      "expediente": "Nº de expediente si disponible",
      "concepto": "Descripción del contrato",
      "importe": 0.00,
      "importe_texto": "123.456,78 €",
      "estado": "licitado|adjudicado|en_ejecucion|ejecutado|pendiente_confirmar",
      "fuente": "URL directa al documento o noticia"
    }
  ],
  "coste_acumulado_confirmado": 0.00,
  "coste_acumulado_texto": "X millones de euros",
  "incremento_respecto_anterior": 0.00,
  "partidas_pendientes_confirmar": ["..."],
  "riesgos_detectados": ["..."],
  "comparativa_valencia": {
    "coste_total_valencia": 0,
    "coste_total_valencia_texto": "X millones de euros",
    "coste_acumulado_madrid": 0,
    "coste_acumulado_madrid_texto": "X millones de euros",
    "factores_riesgo_compartidos": ["factor 1", "factor 2"],
    "porcentaje_similitud_riesgo": 50,
    "justificacion": "Explicación de la puntuación"
  },
  "fuentes_consultadas": ["URL1", "URL2"]
}

IMPORTANTE: Tras usar web_search, tu UNICA respuesta debe ser el objeto JSON final.
No escribas introducciones, no intentes hacer mas busquedas, no uses etiquetas XML ni markdown.
UNICAMENTE el JSON."""


# ─── Helpers ────────────────────────────────────────────────────────────────────
def ensure_dirs():
    """Crea los directorios necesarios."""
    DOCS_DIR.mkdir(exist_ok=True)
    ARCHIVE_DIR.mkdir(exist_ok=True)
    DATA_DIR.mkdir(exist_ok=True)


def load_previous_report() -> str:
    """Carga el informe anterior como contexto para el agente."""
    if LATEST_FILE.exists():
        try:
            data = json.loads(LATEST_FILE.read_text(encoding="utf-8"))
            prev = {
                "fecha": data.get("fecha"),
                "coste_acumulado_confirmado": data.get("coste_acumulado_confirmado"),
                "coste_acumulado_texto": data.get("coste_acumulado_texto"),
                "num_contratos_previos": len(data.get("contratos", [])),
                "riesgos_previos": data.get("riesgos_detectados", []),
                "partidas_pendientes": data.get("partidas_pendientes_confirmar", []),
            }
            return json.dumps(prev, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️  Error cargando informe anterior: {e}")
    return "No hay informe previo. Este es el primer informe."


def load_contracts_db() -> list:
    """Carga la base de datos histórica de contratos."""
    if CONTRACTS_FILE.exists():
        try:
            return json.loads(CONTRACTS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def save_contracts_db(contracts: list):
    """Guarda la base de datos histórica de contratos."""
    CONTRACTS_FILE.write_text(
        json.dumps(contracts, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def extract_json(text: str) -> dict:
    """Extrae un objeto JSON de una respuesta que puede contener markdown o texto adicional."""
    text = text.strip()

    # 1. Limpiar residuos de tool calls que el modelo a veces repite como texto
    text = re.sub(r'<invoke[^>]*>.*?</invoke>', '', text, flags=re.DOTALL)
    text = re.sub(r'<parameter[^>]*>.*?</parameter>', '', text, flags=re.DOTALL)
    text = re.sub(r'</?tool_calls>', '', text)
    text = re.sub(r'I\'ll start by.*?(?=\{|$)', '', text, flags=re.DOTALL)
    text = re.sub(r'Now let me.*?(?=\{|$)', '', text, flags=re.DOTALL)
    text = text.strip()

    # 2. Intentar parseo directo
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        pass

    # 3. Buscar bloque JSON entre ```json ... ```
    match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except (json.JSONDecodeError, ValueError):
            pass

    # 4. Buscar desde { hasta el último } usando balance de llaves
    start = text.find('{')
    if start >= 0:
        depth = 0
        end = -1
        for i, ch in enumerate(text[start:], start):
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    end = i
                    break
        if end > start:
            try:
                return json.loads(text[start:end + 1])
            except (json.JSONDecodeError, ValueError):
                pass

    raise ValueError(f"No se pudo extraer JSON valido de la respuesta:\n{text[:800]}")


def validate_report(data: dict) -> list:
    """Valida que los campos obligatorios existan. Retorna lista de warnings."""
    warnings = []
    required = ["fecha", "resumen_ejecutivo", "nuevos_hallazgos", "contratos",
                "coste_acumulado_confirmado", "coste_acumulado_texto",
                "riesgos_detectados", "fuentes_consultadas"]
    for field in required:
        if field not in data:
            warnings.append(f"Falta campo obligatorio: '{field}'")
            data.setdefault(field, [] if field in ("nuevos_hallazgos", "contratos",
                                                    "riesgos_detectados", "fuentes_consultadas") else "")

    # Asegurar campos que la plantilla espera pero el agente puede no devolver
    for field, default in [
        ("coste_comprometido", data.get("coste_acumulado_confirmado", 0)),
        ("coste_comprometido_texto", data.get("coste_acumulado_texto", "")),
        ("proyeccion_10_anios", {}),
        ("costes_indirectos", []),
        ("costes_indirectos_total_estimado", ""),
    ]:
        if field not in data:
            data[field] = default

    # Asegurar que contratos tenga los campos correctos
    for i, c in enumerate(data.get("contratos", [])):
        for f in ("fecha", "organismo", "expediente", "concepto", "importe",
                   "importe_texto", "estado", "fuente"):
            if f not in c:
                c[f] = ""
                warnings.append(f"Contrato {i}: falta campo '{f}'")

    return warnings


def merge_contracts_db(existing: list, new_contracts: list) -> tuple:
    """Fusiona contratos nuevos en la BD histórica. Retorna (merged, nuevos_detectados)."""
    # Clave única: expediente + organismo + fecha
    seen = set()
    for c in existing:
        key = (c.get("expediente", ""), c.get("organismo", ""), c.get("fecha", ""))
        seen.add(key)

    nuevos = []
    for c in new_contracts:
        key = (c.get("expediente", ""), c.get("organismo", ""), c.get("fecha", ""))
        if key not in seen and c.get("expediente"):
            seen.add(key)
            c["descubierto_el"] = TODAY
            existing.append(c)
            nuevos.append(c)

    return existing, nuevos


# ─── Agente ─────────────────────────────────────────────────────────────────────
def run_research() -> dict:
    """Ejecuta la investigación con Claude API + web search."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY no está definida. "
                           "Añádela en Settings → Secrets → Actions → ANTHROPIC_API_KEY")

    client = anthropic.Anthropic()
    prev = load_previous_report()

    print(f"🔍 Investigando... Fecha UTC: {TODAY} | Madrid: {TODAY_MADRID}")
    print(f"📋 Contexto previo cargado: {len(prev)} chars")

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=16000,
        thinking={"type": "disabled"},
        system=SYSTEM_PROMPT,
        tools=[{
            "type": "web_search_20250305",
            "name": "web_search"
        }],
        messages=[{
            "role": "user",
            "content": f"""Fecha de hoy: {TODAY_MADRID} (Madrid, CEST)

Contexto del informe anterior:
{prev}

INSTRUCCIONES DE BUSQUEDA:
Realiza estas busquedas especificas:

1. Busca en licitaciones2.ifema.es y contrataciondelestado.es nuevas licitaciones, adjudicaciones, modificaciones o DESISTIMIENTOS de los ultimos 7 dias relacionados con Formula 1, Madring, o IFEMA GP España.
2. Busca en madring.com actualizaciones de obras, hitos de construccion y notas de prensa recientes.
3. Busca noticias recientes sobre el GP de España F1 Madrid 2026 (El Pais, El Mundo, El Confidencial, eldiario.es, Palco23, Expansión, Cinco Días).
4. Busca actualizaciones sobre el litigio Dromo vs Tilke en Alemania.
5. Busca informacion actualizada sobre patrocinadores y el canon FOM.

IMPORTANTE: Presta especial atencion a:
- Desistimientos de expedientes (ej: expediente 25/175 desistido por error en criterios)
- Hitos de construccion (asfaltado, izado de bandera, inspecciones FIA)
- Modificaciones de contratos existentes
- Nuevos contratos menores

Tienes UNA ronda de busquedas. Tras recibir los resultados, debes responder UNICAMENTE con el objeto JSON. No escribas texto introductorio, no intentes hacer mas busquedas, no uses etiquetas XML. Solo el JSON."""
        }]
    )

    text_blocks = [b.text for b in response.content if getattr(b, "type", None) == "text"]
    block_types = [getattr(b, "type", "unknown") for b in response.content]
    print(f"   [API] Bloques: {len(response.content)} ({', '.join(block_types)}) | Texto: {len(text_blocks)}")

    if not text_blocks:
        raise ValueError(f"El agente no devolvio bloques de texto. Stop: {response.stop_reason}")

    # Intentar JSON del ultimo bloque al primero; fallback al combinado
    for block_text in reversed(text_blocks):
        try:
            return extract_json(block_text)
        except ValueError:
            continue
    combined = "\n".join(text_blocks)
    return extract_json(combined)


# ─── Guardar ────────────────────────────────────────────────────────────────────
def save_results(data: dict) -> dict:
    """Guarda el informe diario y actualiza la BD de contratos."""
    ensure_dirs()

    # Añadir timestamp real
    data["fecha"] = TODAY
    data["fecha_madrid"] = TODAY_MADRID

    # ── Guardar en archivo diario ──
    daily_file = ARCHIVE_DIR / f"{TODAY}.json"
    daily_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ Archivo diario: {daily_file}")

    # ── Actualizar latest.json ──
    LATEST_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ latest.json actualizado")

    # ── Fusionar contratos en BD histórica ──
    existing = load_contracts_db()
    merged, nuevos = merge_contracts_db(existing, data.get("contratos", []))
    save_contracts_db(merged)
    print(f"✅ contracts.json: {len(merged)} total ({len(nuevos)} nuevos hoy)")

    # También guardar metadatos en data/
    meta_file = DATA_DIR / "timeline.json"
    timeline = []
    if meta_file.exists():
        try:
            timeline = json.loads(meta_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    timeline.append({
        "fecha": TODAY,
        "coste_acumulado": data.get("coste_acumulado_confirmado", 0),
        "coste_texto": data.get("coste_acumulado_texto", ""),
        "num_contratos": len(data.get("contratos", [])),
        "porcentaje_riesgo_valencia": data.get("comparativa_valencia", {}).get("porcentaje_similitud_riesgo", None),
    })
    meta_file.write_text(json.dumps(timeline, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ timeline.json: {len(timeline)} entradas")

    return data


# ─── Main ───────────────────────────────────────────────────────────────────────
def main():
    print("🏎️  Operación Pit-Lane — Agente Investigador F1 Madrid")
    print(f"📅 Fecha: {TODAY_MADRID}")
    print("=" * 60)

    try:
        data = run_research()
    except Exception as e:
        print(f"❌ Error en la investigación: {e}")
        # Crear informe de fallo para no romper la racha
        # Cargar datos anteriores para preservar costes y proyecciones
        prev_data = {}
        if LATEST_FILE.exists():
            try:
                prev_data = json.loads(LATEST_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass

        data = {
            "fecha": TODAY,
            "fecha_madrid": TODAY_MADRID,
            "error": str(e),
            "resumen_ejecutivo": prev_data.get("resumen_ejecutivo",
                f"⚠️ El agente no pudo completar la investigacion hoy: {e}"),
            "nuevos_hallazgos": prev_data.get("nuevos_hallazgos", []),
            "contratos": prev_data.get("contratos", []),
            "coste_acumulado_confirmado": prev_data.get("coste_acumulado_confirmado", 0),
            "coste_acumulado_texto": prev_data.get("coste_acumulado_texto", "No disponible (error en investigacion)"),
            "coste_comprometido": prev_data.get("coste_comprometido", 0),
            "coste_comprometido_texto": prev_data.get("coste_comprometido_texto", ""),
            "incremento_respecto_anterior": 0,
            "proyeccion_10_anios": prev_data.get("proyeccion_10_anios", {}),
            "costes_indirectos": prev_data.get("costes_indirectos", []),
            "costes_indirectos_total_estimado": prev_data.get("costes_indirectos_total_estimado", ""),
            "partidas_pendientes_confirmar": prev_data.get("partidas_pendientes_confirmar", []),
            "riesgos_detectados": prev_data.get("riesgos_detectados", [f"Error tecnico: {e}"]),
            "comparativa_valencia": prev_data.get("comparativa_valencia", {}),
            "fuentes_consultadas": prev_data.get("fuentes_consultadas", []),
        }

    # Validar
    warnings = validate_report(data)
    if warnings:
        print(f"⚠️  {len(warnings)} warnings de validación:")
        for w in warnings:
            print(f"   - {w}")

    # Guardar
    data = save_results(data)

    # Generar páginas HTML
    from generate_pages import build_site
    build_site(data)

    print("=" * 60)
    print(f"🏁 Investigación completada. Coste confirmado: {data.get('coste_acumulado_texto', 'N/A')}")
    print(f"🔗 Próxima ejecución: mañana a las 21:00h Madrid")


if __name__ == "__main__":
    main()
