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
y organización. No debes limitarte al coste del circuito: investiga cualquier gasto asociado.

─── FUENTES ───
Oficiales (solo estas confirman cifras):
- Plataforma de Contratación del Sector Público (contrataciondelestado.es)
- IFEMA Madrid, perfil del contratante (licitaciones2.ifema.es)
- Madring (madring.com), BOE, BOCM
- Comunidad de Madrid, Ayuntamiento de Madrid
- Portal de Transparencia, Tribunal de Cuentas

Secundarias (solo para localizar, NUNCA para confirmar):
Reuters, El Diario, Cinco Días, El País, Expansión, AS, Palco23, Economía Digital.

─── QUÉ INVESTIGAR ───
Infraestructura: circuito, boxes, Pit Building, gradas, electricidad, fibra,
asfaltado, drenaje, urbanización, pasarelas, hospitales de campaña, bomberos.
Contratación pública: licitaciones, adjudicaciones, modificaciones, contratos
menores, emergencias, convenios, patrocinios, desistimientos.
Costes del evento: canon FOM, seguridad, policía, movilidad, transporte público,
limpieza, protección civil, servicios sanitarios, marketing, patrocinios.
Urbanismo: expropiaciones, vía pecuaria, licencias, impacto ambiental.

─── METODOLOGÍA ───
Antes de aceptar cualquier cifra:
1. Busca al menos dos fuentes independientes.
2. Comprueba si existe documentación oficial.
3. Identifica si es: presupuesto / licitación / adjudicación / ejecución real.
4. NUNCA mezcles conceptos.

🟢 CONFIRMADO: soporte documental oficial. Solo esto suma al coste confirmado.
🟡 MUY PROBABLE: documentación indirecta sólida. NO sumar al confirmado.
🟠 HIPÓTESIS: evidencia parcial. NO sumar.
🔴 RUMOR: no utilizar.

─── REGLAS ───
- No inventes datos. No extrapoles cifras. No uses rumores ni titulares.
- Si una cifra no puede verificarse, indícalo expresamente.
- Para cada contrato: organismo, expediente REAL (formato NN/NNN o NNNNNNNNNN), fecha,
  importe, adjudicatario, estado, fuente URL.
- NUNCA uses expedientes genéricos como "No disponible" o "Pendiente confirmar".
- Compara SIEMPRE con el informe anterior. Muestra SOLO novedades.
- No uses lenguaje político. Sé extremadamente preciso.
- Usa español correcto con tildes, eñes y todos los acentos.

─── CUATRO CIFRAS (nunca mezclar) ───
1. COSTE CONFIRMADO: solo adjudicaciones con soporte documental oficial.
2. COSTE COMPROMETIDO: confirmado + PBL de licitaciones activas.
3. COSTE ESTIMADO: presupuestos base e hipótesis.
4. COSTE POTENCIAL: incluyendo prórrogas, modificaciones previstas y VEC.

─── FORMATO DE RESPUESTA ───
Solo JSON válido, sin markdown ni etiquetas:

{
  "fecha": "YYYY-MM-DD",
  "resumen_ejecutivo": "Máx 10 líneas. Qué se ha descubierto, qué ha cambiado, mejor estimación actual del coste.",
  "nuevos_hallazgos": ["Solo información nueva desde el último informe"],
  "contratos": [
    {
      "fecha": "YYYY-MM-DD",
      "organismo": "Nombre",
      "expediente": "Número real (NUNCA genérico)",
      "adjudicatario": "Nombre o UTE",
      "concepto": "Descripción",
      "importe": 0.00,
      "importe_texto": "123.456,78 €",
      "estado": "licitado|adjudicado|en_ejecución|ejecutado|desistido",
      "nivel_confianza": "confirmado|muy_probable|hipotesis",
      "fuente": "URL directa al documento oficial"
    }
  ],
  "coste_acumulado_confirmado": 0.00,
  "coste_acumulado_texto": "X M€ (solo adjudicaciones con soporte oficial)",
  "coste_comprometido": 0.00,
  "coste_comprometido_texto": "X M€ (incluye PBL de licitaciones activas)",
  "incremento_respecto_anterior": 0.00,
  "partidas_pendientes_confirmar": ["..."],
  "riesgos_detectados": ["..."],
  "comparativa_valencia": {
    "coste_total_valencia": 0,
    "coste_total_valencia_texto": "X millones de euros",
    "factores_riesgo_compartidos": ["factor 1"],
    "porcentaje_similitud_riesgo": 50,
    "justificacion": "Explicación"
  },
  "fuentes_consultadas": ["URL1", "URL2"]
}

IMPORTANTE: Tras usar web_search, responde SOLO con el JSON.
Sin introducciones, sin etiquetas XML, sin markdown. Solo el JSON.
ES OBLIGATORIO usar español correcto con tildes (á, é, í, ó, ú), eñes (ñ) y diéresis (ü)
en TODOS los campos de texto. Esta página se publica en España y debe usar
ortografía española real. No uses ASCII simplificado."""


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


import re
# Solo aceptar expedientes que coincidan con el formato real de IFEMA
EXP_RE = re.compile(r"^\d{2}/\d{3,4}$")  # ej: 26/113, 25/043, 24/226
EXP_CM_RE = re.compile(r"^\d{10}$")       # ej: 6200014240 (contratos menores)

def merge_contracts_db(existing: list, new_contracts: list) -> tuple:
    """Fusiona contratos nuevos en la BD historica. Solo acepta expedientes con formato real."""
    seen = set()
    for c in existing:
        key = (c.get("expediente", "").strip(), c.get("organismo", ""), c.get("fecha", ""))
        seen.add(key)

    nuevos = []
    for c in new_contracts:
        exp = c.get("expediente", "").strip()
        # SOLO aceptar formatos reales: NN/NNN o NNNNNNNNNN
        if not (EXP_RE.match(exp) or EXP_CM_RE.match(exp)):
            continue
        concepto = c.get("concepto", "").strip()
        if len(concepto) < 15:
            continue
        key = (exp, c.get("organismo", ""), c.get("fecha", ""))
        if key not in seen:
            seen.add(key)
            c["descubierto_el"] = TODAY
            existing.append(c)
            nuevos.append(c)

    return existing, nuevos


# ─── Agente ─────────────────────────────────────────────────────────────────────
MONITOR_PROMPT = """Eres un monitor automatico de portales de contratación pública.
Tu unica tarea: detectar NUEVOS expedientes o licitaciones relacionadas con el
circuito de Formula 1 de Madrid usando los terminos: 'madring', 'formula 1',
'gran premio', 'circuito', 'IFEMA'.

Busca especificamente en estos portales:

1. licitaciones2.ifema.es (perfil del contratante IFEMA):
   Busca: 'madrid formula 1', 'madring', 'gran premio espana', 'circuito IFEMA'

2. contrataciondelestado.es (Plataforma de Contratacion del Estado):
   Busca: 'IFEMA formula 1', 'madrid gran premio', 'madring circuito'

3. transparencia.madrid.es y madrid.es (Ayuntamiento de Madrid):
   Busca: 'formula 1 madrid', 'madring', 'gran premio IFEMA'

4. comunidad.madrid (Comunidad de Madrid):
   Busca: 'formula 1', 'madring', 'gran premio espana', 'circuito urbano'

Para cada hallazgo indica: PORTAL, expediente/expediente, titulo, importe (si visible),
estado (licitado/adjudicado/desistido), y URL.
NO uses JSON. Solo texto estructurado. Si no hay novedades di 'SIN NOVEDADES'."""

HAIKU_SEARCH_PROMPT = """Eres un investigador OSINT especializado en contratación pública espanola.
Tu tarea: buscar información actualizada sobre el GP de Formula 1 de Madrid (Madring)
y devolver los hallazgos en texto estructurado.

Busca en:
- licitaciones2.ifema.es: nuevas licitaciones, adjudicaciones, desistimientos
- madring.com: hitos de construcción, notas de prensa
- Noticias: Reuters, El Pais, Cinco Dias, Palco23

Para cada hallazgo indica: fuente, fecha, cifras, estado.
NO redactes JSON. Solo texto estructurado con los datos encontrados."""

SONNET_ANALYSIS_PROMPT = SYSTEM_PROMPT  # El prompt completo con toda la metodologia


def detect_changes(old_contracts: list, new_contracts: list) -> list:
    """Detecta cambios de estado o importe en expedientes ya conocidos."""
    cambios = []
    old_map = {c.get("expediente", ""): c for c in old_contracts}

    for c in new_contracts:
        exp = c.get("expediente", "")
        if exp not in old_map:
            continue  # es nuevo, no un cambio
        old = old_map[exp]
        # Detectar cambio de estado
        if c.get("estado") != old.get("estado"):
            cambios.append(
                f"🔄 {exp}: {old.get('estado','?')} → {c.get('estado','?')} "
                f"({c.get('concepto','')[:60]})"
            )
        # Detectar cambio de importe significativo (>5%)
        old_imp = old.get("importe", 0) or 0
        new_imp = c.get("importe", 0) or 0
        if old_imp > 0 and new_imp > 0 and abs(new_imp - old_imp) / old_imp > 0.05:
            cambios.append(
                f"💰 {exp}: {old_imp:,.0f}€ → {new_imp:,.0f}€ "
                f"({c.get('concepto','')[:60]})"
            )
    return cambios


def prev_data_or_empty(prev_str: str) -> dict:
    """Si no hay novedades, devuelve los datos anteriores intactos."""
    if LATEST_FILE.exists():
        try:
            return json.loads(LATEST_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "fecha": TODAY, "fecha_madrid": TODAY_MADRID,
        "resumen_ejecutivo": "Sin novedades detectadas en esta ejecución.",
        "nuevos_hallazgos": [], "contratos": [],
        "coste_acumulado_confirmado": 0, "coste_acumulado_texto": "",
        "coste_comprometido": 0, "coste_comprometido_texto": "",
        "incremento_respecto_anterior": 0,
        "partidas_pendientes_confirmar": [], "riesgos_detectados": [],
        "comparativa_valencia": {}, "fuentes_consultadas": [],
    }


def run_research() -> dict:
    """Pipeline en 2 pasos: Haiku busca, Sonnet analiza."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY no está definida.")

    client = anthropic.Anthropic()
    prev = load_previous_report()

    print(f"🔍 Investigando... Fecha UTC: {TODAY} | Madrid: {TODAY_MADRID}")

    # ── Paso 0: Monitor de portales (Haiku, busca nuevos expedientes) ──
    print("   [Paso 0] Monitor portales contratación...")
    monitor_response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=3072,
        thinking={"type": "disabled"},
        system=MONITOR_PROMPT,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{
            "role": "user",
            "content": f"Fecha: {TODAY_MADRID}. Busca nuevos expedientes en IFEMA, Ayto Madrid, Comunidad Madrid y contrataciondelestado.es usando: 'madring', 'formula 1', 'gran premio', 'circuito'. Max 3 busquedas."
        }]
    )
    monitor_data = "\n".join(
        b.text for b in monitor_response.content if getattr(b, "type", None) == "text"
    )
    m_blocks = [getattr(b, "type", "?") for b in monitor_response.content]
    has_news = "SIN NOVEDADES" not in monitor_data.upper()
    print(f"   [Monitor] Bloques: {len(monitor_response.content)} ({', '.join(m_blocks)}) | Novedades: {has_news}")

    # ── Paso 1: Haiku 4.5 + web_search (busca datos + noticias) ──
    print("   [Paso 1] Haiku 4.5 + web_search...")
    haiku_response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4096,
        thinking={"type": "disabled"},
        system=HAIKU_SEARCH_PROMPT,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{
            "role": "user",
            "content": f"Fecha: {TODAY_MADRID} (Madrid, CEST).\n\nContexto anterior:\n{prev}\n\nMONITOR DE PORTALES (nuevos expedientes detectados):\n{monitor_data}\n\nBusca mas detalles y noticias sobre estos hallazgos (max 3 busquedas)."
        }]
    )

    raw_data = "\n".join(
        b.text for b in haiku_response.content if getattr(b, "type", None) == "text"
    )
    blocks_h = [getattr(b, "type", "?") for b in haiku_response.content]
    print(f"   [Haiku] Bloques: {len(haiku_response.content)} ({', '.join(blocks_h)}) | Texto: {len(raw_data)} chars")

    if not raw_data.strip():
        raise ValueError("Haiku no devolvio resultados de busqueda")

    # Si monitor y busqueda no encontraron nada, saltar Sonnet (ahorro ~$2/ejec)
    if not has_news and len(raw_data) < 500:
        print("   [Skip] Sin novedades detectadas. Saltando analisis Sonnet.")
        return prev_data_or_empty(prev)

    # ── Paso 2: Sonnet 4.6 (analiza, sin web search, mas barato en output) ──
    print("   [Paso 2] Sonnet 4.6 analizando...")
    sonnet_response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8192,
        thinking={"type": "disabled"},
        system=SONNET_ANALYSIS_PROMPT,
        messages=[{
            "role": "user",
            "content": f"""Fecha: {TODAY_MADRID} (Madrid, CEST)

Contexto del informe anterior:
{prev}

DATOS RECOPILADOS POR EL INVESTIGADOR:
{raw_data}

Con esta información, genera el JSON final aplicando la metodologia:
- Solo CONFIRMADO si hay soporte documental oficial.
- Clasifica cada dato: 🟢🟡🟠🔴.
- Nunca sumes estimaciónes al coste confirmado.
- Solo expedientes con numero real (no 'No disponible').
- Cada nuevo_hallazgo DEBE empezar con la fecha del descubrimiento: "[YYYY-MM-DD] texto del hallazgo".
- Responde UNICAMENTE con el JSON, sin markdown ni etiquetas.
- Usa español correcto con tildes, eñes y todos los acentos."""
        }]
    )

    text_blocks = [b.text for b in sonnet_response.content if getattr(b, "type", None) == "text"]
    blocks_s = [getattr(b, "type", "?") for b in sonnet_response.content]
    print(f"   [Sonnet] Bloques: {len(sonnet_response.content)} ({', '.join(blocks_s)}) | Texto: {len(text_blocks)}")

    if not text_blocks:
        raise ValueError("Sonnet no devolvio respuesta de texto")

    for block_text in reversed(text_blocks):
        try:
            return extract_json(block_text)
        except ValueError:
            continue
    return extract_json("\n".join(text_blocks))


# ─── Guardar ────────────────────────────────────────────────────────────────────
def save_results(data: dict) -> dict:
    """Guarda el informe diario y actualiza la BD de contratos.
    PRESERVA los datos curados (costes confirmados, proyecciones, etc.)
    y solo incorpora nuevos hallazgos y contratos del agente."""
    ensure_dirs()

    # Cargar datos anteriores para preservar campos curados
    prev = {}
    if LATEST_FILE.exists():
        try:
            prev = json.loads(LATEST_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass

    # Fusionar contratos: los existentes + solo los NUEVOS del agente
    existing_contracts = load_contracts_db()
    if not existing_contracts and prev.get("contratos"):
        existing_contracts = prev["contratos"]
    merged_contracts, nuevos = merge_contracts_db(existing_contracts, data.get("contratos", []))
    cambios = detect_changes(existing_contracts, data.get("contratos", []))
    save_contracts_db(merged_contracts)

    # Recalcular costes desde los contratos limpios
    confirmado = 0
    comprometido = 0
    for c in merged_contracts:
        estado = c.get("estado", "")
        imp = c.get("importe", 0) or 0
        if estado in ("adjudicado", "ejecutado"):
            confirmado += imp
        if estado in ("adjudicado", "ejecutado", "licitado"):
            comprometido += imp

    # Construir el informe final: preservar campos curados, actualizar solo lo nuevo
    # Usar la hora real de ejecución, no la del JSON del agente
    now_madrid = datetime.now(MADRID_TZ)
    exec_date = now_madrid.strftime("%Y-%m-%d")
    exec_datetime = now_madrid.strftime("%Y-%m-%d %H:%M")

    final = {
        "fecha": exec_date,
        "fecha_madrid": exec_datetime,
        # Campos narrativos del agente (si trae algo nuevo)
        "resumen_ejecutivo": data.get("resumen_ejecutivo") or prev.get("resumen_ejecutivo", ""),
        "nuevos_hallazgos": data.get("nuevos_hallazgos") or prev.get("nuevos_hallazgos", []),
        "riesgos_detectados": data.get("riesgos_detectados") or prev.get("riesgos_detectados", []),
        "partidas_pendientes_confirmar": data.get("partidas_pendientes_confirmar") or prev.get("partidas_pendientes_confirmar", []),
        "fuentes_consultadas": data.get("fuentes_consultadas") or prev.get("fuentes_consultadas", []),
        "comparativa_valencia": data.get("comparativa_valencia") or prev.get("comparativa_valencia", {}),
        # Contratos: la BD completa fusionada
        "contratos": merged_contracts,
        # Costes: recalculados desde la BD limpia
        "coste_acumulado_confirmado": confirmado,
        "coste_acumulado_texto": f"{confirmado/1e6:.1f} millones de euros (obra principal + modificación + asistencia tecnica + contratos menores). No incluye Pit Building, canon FOM ni licitaciones pendientes.",
        "coste_comprometido": comprometido,
        "coste_comprometido_texto": f"{comprometido/1e6:.1f} millones de euros (costes confirmados + PBL de licitaciones activas).",
        "incremento_respecto_anterior": confirmado - prev.get("coste_acumulado_confirmado", confirmado),
        "cambios_detectados": cambios,
        # Preservar campos curados que el agente no genera
        "proyeccion_10_anios": prev.get("proyeccion_10_anios", {}),
        "costes_indirectos": prev.get("costes_indirectos", []),
        "costes_indirectos_total_estimado": prev.get("costes_indirectos_total_estimado", ""),
    }

    # ── Guardar archivo diario ──
    daily_file = ARCHIVE_DIR / f"{exec_date}.json"
    daily_file.write_text(json.dumps(final, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ Archivo diario: {daily_file}")

    # ── Actualizar latest.json ──
    LATEST_FILE.write_text(json.dumps(final, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ latest.json actualizado")
    print(f"✅ contracts.json: {len(merged_contracts)} total ({len(nuevos)} nuevos hoy)")

    # Timeline
    meta_file = DATA_DIR / "timeline.json"
    timeline = []
    if meta_file.exists():
        try:
            timeline = json.loads(meta_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    timeline.append({
        "fecha": exec_date,
        "coste_acumulado": confirmado,
        "coste_texto": final["coste_acumulado_texto"],
        "coste_comprometido": comprometido,
        "coste_comprometido_texto": final.get("coste_comprometido_texto", ""),
        "num_contratos": len(merged_contracts),
        "porcentaje_riesgo_valencia": final["comparativa_valencia"].get("porcentaje_similitud_riesgo", None),
    })
    meta_file.write_text(json.dumps(timeline, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ timeline.json: {len(timeline)} entradas")

    return final


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
                f"⚠️ El agente no pudo completar la investigación hoy: {e}"),
            "nuevos_hallazgos": prev_data.get("nuevos_hallazgos", []),
            "contratos": prev_data.get("contratos", []),
            "coste_acumulado_confirmado": prev_data.get("coste_acumulado_confirmado", 0),
            "coste_acumulado_texto": prev_data.get("coste_acumulado_texto", "No disponible (error en investigación)"),
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
