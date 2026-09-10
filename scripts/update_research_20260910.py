"""
Limpieza y corrección del contador — 2026-09-10
================================================
El cron diario acumuló duplicados (25/187 ×15, 24/226 ×5 con adjudicatario
erróneo 'Dragados', etc.) que inflan el coste confirmado a 428,7 M€.

Este script:
1. Deduplica contracts.json por expediente.
2. Corrige el contrato del circuito (UTE Acciona-Eiffage, no Dragados) y
   pliega sus duplicados (25/052, 24/226 ×5, modificaciones).
3. Incorpora el Pit Building (25/053) como ADICIONAL al circuito (adjudicado).
4. Retira la Fan Zone (liquidación 0 €) y el 25/187 desistido.
5. Añade: TRAGSATEC, Ayuntamiento 1,9 M€, 25/211, 24/047 R y nuevas licitaciones.
6. Recalcula el contador: confirmado = adjudicado+ejecutado+en_ejecución.
"""
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT / "docs"
DATA_DIR = ROOT / "data"
ARCHIVE_DIR = DOCS_DIR / "archive"
LATEST_FILE = DOCS_DIR / "latest.json"
CONTRACTS_FILE = DOCS_DIR / "contracts.json"
TIMELINE_FILE = DATA_DIR / "timeline.json"

MADRID_TZ = timezone(timedelta(hours=2))
NOW = datetime.now(MADRID_TZ)
EXEC_DATE = "2026-09-10"
EXEC_DATETIME = NOW.strftime("%Y-%m-%d %H:%M")

CONFIRMED_STATES = ("adjudicado", "ejecutado", "en_ejecución", "en_ejecucion")
AYTO_APORTACION = 1_900_000.0
SERVICIOS_EXTRA_ESTIMACION = 2_600_000.0

_STATE_PRIORITY = {
    "adjudicado": 4, "ejecutado": 4, "en_ejecución": 4, "en_ejecucion": 4,
    "licitado": 2, "pendiente_confirmar": 1, "desistido": 0, "comprometido": 3,
}


def load(p):
    return json.loads(p.read_text(encoding="utf-8"))


def save(p, data):
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ─── Entradas canónicas para los grandes contratos ────────────────────────────
CANONICAL = {
    "24/226": {
        "descubierto_el": "2026-06-24", "fecha": "2025-04-15",
        "organismo": "IFEMA Madrid", "expediente": "24/226",
        "adjudicatario": "UTE Acciona (60%) - Eiffage (40%)",
        "concepto": "Construcción del circuito MADRING y reposición de infraestructuras (adjudicación 83.206.500,01 € + modificación 2.304.868,93 €).",
        "importe": 85511368.94,
        "importe_texto": "85.511.368,94 € (adjudicación 83.206.500,01 € + modificación 2.304.868,93 €)",
        "estado": "adjudicado", "nivel_confianza": "confirmado",
        "fuente": "https://licitaciones2.ifema.es",
    },
    "25/053": {
        "descubierto_el": "2026-09-10", "fecha": "2025-09-30",
        "organismo": "IFEMA Madrid", "expediente": "25/053",
        "adjudicatario": "Eiffage Construcción",
        "concepto": ("Pit Building: ampliación de los pabellones 1 y 2 IFEMA (boxes, oficinas técnicas, "
                     "logística y Paddock Club). Contrato ADICIONAL al circuito: Eiffage confirma que "
                     "'se suma' al contrato de la UTE Acciona-Eiffage."),
        "importe": 68100000.0,
        "importe_texto": "68.100.000,00 € (adjudicado a Eiffage; adicional al circuito)",
        "estado": "adjudicado", "nivel_confianza": "confirmado",
        "fuente": "https://www.eiffage.es/proyectos/pit-building-formula-1-madrid",
    },
}

# Expedientes duplicados que se pliegan en otro (se eliminan)
REMOVE_EXPEDIENTES = {
    "25/052",            # duplicado del circuito (Acciona) -> 24/226
    "PIT-BUILDING-2025",  # duplicado del Pit Building -> 25/053
    "2000026766",        # modificación nº1 -> 24/226
    "25/047",            # modificación (hipótesis) -> 24/226
}

# Correcciones de estado
STATE_FIXES = {
    "FANZONE-SOL-2026": {"estado": "desistido", "importe": 0.0,
                         "importe_texto": "Liquidación 0,00 € (no se cuenta como gasto ejecutado)"},
    "25/187": {"estado": "desistido", "importe": 0.0,
               "importe_texto": "Desistido; sustituido por el expediente 25/211"},
}

# Contratos nuevos
NUEVOS = [
    {"descubierto_el": EXEC_DATE, "fecha": "2026-08-11", "organismo": "Comunidad de Madrid",
     "expediente": "EG/2026/0000009265", "adjudicatario": "TRAGSATEC",
     "concepto": "Promoción de productos agroalimentarios madrileños durante el GP de F1 (encargo a TRAGSATEC).",
     "importe": 167354.13, "importe_texto": "167.354,13 € (formalizado)", "estado": "ejecutado",
     "nivel_confianza": "confirmado", "fuente": "https://contrataciondelestado.es"},
    {"descubierto_el": EXEC_DATE, "fecha": "2026-09-03", "organismo": "Ayuntamiento de Madrid / Madrid Destino",
     "expediente": "ACUERDO-JG-28", "adjudicatario": "Madrid Destino",
     "concepto": ("Aportación extraordinaria de 1,9 M€ a Madrid Destino para modificar el convenio de promoción "
                  "internacional F1 (Destination Signage Package). BOAM 07/09/2026."),
     "importe": AYTO_APORTACION, "importe_texto": "1.900.000,00 € (compromiso oficial acreditado, BOAM 07/09/2026)",
     "estado": "comprometido", "nivel_confianza": "confirmado", "fuente": "https://www.madrid.es"},
    {"descubierto_el": EXEC_DATE, "fecha": "2026-09-01", "organismo": "IFEMA Madrid", "expediente": "25/211",
     "adjudicatario": "Sin adjudicación publicada",
     "concepto": ("Medios, acreditaciones, protocolo y atención VIP (sustituye al 25/187 desistido). Hasta 100.000 € "
                  "para viajes, 186.000 € PR/comunicación y 20.000 € press clipping."),
     "importe": 524000.0, "importe_texto": "524.000,00 € (PBL) / 2.882.000,00 € (VEC)", "estado": "licitado",
     "nivel_confianza": "confirmado", "fuente": "https://licitaciones2.ifema.es"},
    {"descubierto_el": EXEC_DATE, "fecha": "2026-09-01", "organismo": "IFEMA Madrid", "expediente": "24/047 R",
     "adjudicatario": "Sin adjudicación publicada",
     "concepto": "Asesoramiento jurídico del proyecto F1 (PBL anual 874.500 €; VEC máximo 4.809.750 € con prórrogas y modificación del 50%).",
     "importe": 874500.0, "importe_texto": "874.500,00 € (PBL anual) / 4.809.750,00 € (VEC)", "estado": "licitado",
     "nivel_confianza": "confirmado", "fuente": "https://licitaciones2.ifema.es"},
    {"descubierto_el": EXEC_DATE, "fecha": "2026-07-01", "organismo": "IFEMA Madrid", "expediente": "PEND-CERRAMIENTOS",
     "adjudicatario": "Por identificar", "concepto": "Cerramientos temporales y lona personalizada del GP de F1.",
     "importe": 203911.0, "importe_texto": "203.911,00 € (detectado; pendiente de resolución/pliego directo)",
     "estado": "pendiente_confirmar", "nivel_confianza": "muy_probable", "fuente": "https://licitaciones2.ifema.es"},
    {"descubierto_el": EXEC_DATE, "fecha": "2026-07-20", "organismo": "IFEMA Madrid", "expediente": "PEND-BUGGIES",
     "adjudicatario": "Por identificar", "concepto": "Alquiler de buggies eléctricos para el GP de F1.",
     "importe": 68090.0, "importe_texto": "68.090,00 € (detectado; pendiente de resolución/pliego directo)",
     "estado": "pendiente_confirmar", "nivel_confianza": "muy_probable", "fuente": "https://licitaciones2.ifema.es"},
    {"descubierto_el": EXEC_DATE, "fecha": "2026-07-17", "organismo": "IFEMA Madrid", "expediente": "PEND-SCOOTERS",
     "adjudicatario": "Por identificar", "concepto": "Alquiler de scooters eléctricos para el GP de F1.",
     "importe": 46104.0, "importe_texto": "46.104,00 € (detectado; pendiente de resolución/pliego directo)",
     "estado": "pendiente_confirmar", "nivel_confianza": "muy_probable", "fuente": "https://licitaciones2.ifema.es"},
]


def clean_contracts():
    cs = load(CONTRACTS_FILE)

    # 1. Eliminar expedientes plegados
    cs = [c for c in cs if c.get("expediente", "").strip() not in REMOVE_EXPEDIENTES]

    # 2. Correcciones de estado
    for c in cs:
        exp = c.get("expediente", "").strip()
        if exp in STATE_FIXES:
            c.update(STATE_FIXES[exp])

    # 3. Reemplazar expedientes canónicos (1 sola entrada por expediente)
    seen_canonical = set()
    out = []
    for c in cs:
        exp = c.get("expediente", "").strip()
        if exp in CANONICAL:
            if exp not in seen_canonical:
                out.append(dict(CANONICAL[exp]))
                seen_canonical.add(exp)
            continue
        out.append(c)
    cs = out

    # 4. Deduplicar por expediente (mantener la entrada más completa)
    groups = {}
    for c in cs:
        groups.setdefault(c.get("expediente", "").strip(), []).append(c)
    cs = []
    for exp, entries in groups.items():
        if len(entries) == 1:
            cs.append(entries[0])
        else:
            best = max(entries, key=lambda c: (
                _STATE_PRIORITY.get(c.get("estado"), -1),
                c.get("importe") or 0,
                len(c.get("concepto") or ""),
            ))
            cs.append(best)

    # 5. Añadir contratos nuevos (evitar duplicados)
    seen = {c.get("expediente", "") for c in cs}
    for n in NUEVOS:
        if n["expediente"] not in seen:
            cs.append(n)
            seen.add(n["expediente"])

    save(CONTRACTS_FILE, cs)
    return cs


def compute(cs):
    confirmado = sum(c.get("importe", 0) or 0 for c in cs if c.get("estado") in CONFIRMED_STATES)
    comprometido = confirmado + AYTO_APORTACION
    total = comprometido + SERVICIOS_EXTRA_ESTIMACION
    return confirmado, comprometido, total


def main():
    cs = clean_contracts()
    confirmado, comprometido, total = compute(cs)
    M = 1e6
    cm, cpm, tm = confirmado / M, comprometido / M, total / M

    resumen = (
        f"A 10 de septiembre de 2026, un día antes del Gran Premio de España (11-13 de septiembre), rehago el "
        f"contador tras una corrección estructural y una limpieza de duplicados. El Pit Building / ampliación de "
        f"los pabellones 1 y 2 cuesta 68,1 M€ ADICIONALES al contrato del circuito: Eiffage confirma que 'este "
        f"contrato se suma' al de la UTE Acciona-Eiffage, por lo que no estaba incluido en los 83,2 M€ del circuito. "
        f"El circuito aparece en el portal con adjudicatario correcto (UTE Acciona-Eiffage), no Dragados, y su "
        f"adjudicación más modificación suma 85,51 M€. El coste confirmado (adjudicaciones con soporte oficial) se "
        f"sitúa en {cm:.1f} M€ y el mínimo de compromisos identificados en {cpm:.1f} M€, sumando la aportación "
        f"municipal de 1,9 M€ (BOAM 07/09/2026). El descenso desde los 428,7 M€ anteriores es una corrección de "
        f"base histórica (duplicados y adjudicatario erróneo), no una reducción del gasto. Retiro la hipótesis del "
        f"canon de 48 M€/año (480 M€): no hay documento oficial y el canon continúa desconocido. Retiro la Fan Zone "
        f"Red Bull de Sol (121.000 €), liquidada a 0,00 €. Se incorporan 167.354,13 € de la Comunidad vía TRAGSATEC "
        f"y se registran el 25/211 (que sustituye al 25/187 desistido) y el 24/047 R (asesoramiento jurídico). La "
        f"inversión privada de MATCH Hospitality (400 M€, 2026-2035) está confirmada pero no es ingreso. Añado una "
        f"estimación de {SERVICIOS_EXTRA_ESTIMACION/M:.2f} M€ (rango 1,68-3,82 M€) por los servicios públicos "
        f"extraordinarios de seguridad, emergencias y transporte, lo que eleva la estimación provisional ampliada a "
        f"≈{tm:.1f} M€."
    )

    hallazgos = [
        "[2026-09-10] El Pit Building son 68,1 M€ ADICIONALES al contrato del circuito: IFEMA adjudicó a Eiffage Construcción otro contrato para ampliar los pabellones 1 y 2 (boxes, oficinas técnicas, logística y Paddock Club), y Eiffage confirma que 'este contrato se suma' al del circuito urbano.",
        "[2026-09-10] Corrección del contador: el circuito estaba registrado con adjudicatario erróneo (Dragados, quintuplicado) y sin contar el contrato real de la UTE Acciona-Eiffage. El adjudicatario correcto es la UTE Acciona (60%) - Eiffage (40%), con adjudicación + modificación de 85,51 M€.",
        "[2026-09-10] La Junta de Gobierno del Ayuntamiento del 3-IX-2026 autorizó 1.900.000 € adicionales para Madrid Destino (convenio de promoción internacional F1, BOAM 07/09/2026). Parte del Destination Signage Package (~5 M€).",
        "[2026-09-10] La Comunidad formalizó el 11-VIII-2026 el expediente EG/2026/0000009265, encargado a TRAGSATEC, para promocionar productos agroalimentarios madrileños durante el GP. Importe: 167.354,13 €.",
        "[2026-09-10] El expediente 25/187 (medios, acreditaciones, protocolo y VIP), desistido, reaparece como 25/211: PBL 524.000 € y VEC 2.882.000 € sin IVA. Sin adjudicación localizada.",
        "[2026-09-10] El asesoramiento jurídico del proyecto es el expediente 24/047 R: PBL anual 874.500 € y VEC máximo 4.809.750 €. No se valida la cifra de 10 M€ aparecida en prensa.",
        "[2026-09-10] IFEMA confirma que MATCH Hospitality invertirá 400 M€ (2026-2035) en las zonas VIP/hospitality. Inversión privada, no ingreso.",
        "[2026-09-10] La Fan Zone Red Bull de Sol (121.000 €) se retira: liquidación del contrato de 0,00 €.",
        "[2026-09-10] Se retira la hipótesis del canon de 48 M€/año (480 M€): sin documento oficial. El País publica 277 M€/10 años atribuidos a Más Madrid, no a FOM/IFEMA. El canon continúa oficialmente desconocido.",
        "[2026-09-10] Nuevas licitaciones operativas: 26/129 (639.640,91 € PBL), 26/057 (296.200 € PBL), cerramientos+lona (203.911 €), buggies (68.090 €) y scooters (46.104 €). Total detectado 1.253.945,91 €.",
        "[2026-09-10] El gasto de IFEMA se acerca a 180 M€ (elDiario.es: casi 183 M€, 171,5 M€ en obras), no a los 100 M€ iniciales. Pendiente de homogeneizar IVA, adjudicaciones y PBL.",
        "[2026-09-10] Dispositivo de seguridad y transporte: >1.000 policías municipales, ~250 SAMUR-PC, >60 bomberos, ~60 agentes de movilidad, ~1.500 policías nacionales/guardias civiles diarios, 5 lanzaderas EMT, refuerzo Metro L4/L5/L8 y Cercanías. Coste extraordinario sin publicar.",
        "[2026-09-10] Estimación de coste público extraordinario de seguridad, emergencias y transporte: ≈2,6 M€ (rango 1,68-3,82 M€), 0 € confirmado.",
        "[2026-09-10] Vacío de contratos menores IFEMA 2026: el portal solo muestra 2023-2025 a 10-IX-2026, justo antes del GP.",
        "[2026-09-10] Patrocinios MADRING: Founding Partners (Santander, Fever); Local Event Supporters (American Express, Atlético de Madrid, Ford, Aqualy, Heineken, El Corte Inglés, PwC, Real Madrid); Official Partner (Red Bull); Destination Partner (Madrid Beats). Sin cuantías publicadas.",
        "[2026-09-10] El estudio PwC eleva el impacto económico estimado de 2026 a 467 M€, 8.850 empleos y ~83 M€ en impuestos. Es impacto económico, no ingreso.",
        "[2026-09-10] El circuito está homologado por la FIA (test F3 25-26 de agosto) y las gradas (~98.000 plazas) y barreras instaladas. Riesgos CRÍTICOS de julio resueltos en lo operativo.",
    ]

    riesgos = [
        "CRÍTICO — El canon a FOM/Liberty Media sigue sin publicarse oficialmente a 10-IX-2026. Retiramos la hipótesis de 48 M€/año; la única cifra en prensa (277 M€/10 años) no está acreditada.",
        "CRÍTICO — El gasto de IFEMA se aproxima a 180 M€ (elDiario.es: casi 183 M€), no a los 100 M€ iniciales. Falta homogeneizar IVA, adjudicaciones y PBL.",
        "ALTO — A un día del GP, los costes públicos operativos (policía, SAMUR, bomberos, Metro, Cercanías, EMT) están sin precio publicado; estimamos ≈2,6 M€, con 0 € confirmado.",
        "ALTO — Vacío en los contratos menores de IFEMA de 2026 (solo 2023-2025 publicados), justo antes del GP.",
        "ALTO — Sigue sin conocerse el coste de la bandera gigante, el acto oficial, los buses vinilados, patrocinios institucionales y el contrato FOM completo.",
        "ALTO — Según la Memoria de IFEMA (concesión 13 años), el proyecto arroja un VAN de -18 M€ y una TIR de -0,961%.",
        "ALTO — Litigio Dromo-Tilke por la propiedad intelectual del trazado (6 M€, procedimiento penal en Colonia) sin resolución.",
        "MEDIO — Robo de 300 m de cableado de generadores a dos semanas del GP.",
        "MEDIO — Un estudio de ruido cifra en 14.000 las personas expuestas por encima del límite legal.",
        "MEDIO — La pasarela de ganado sobre la M-11 (6-10 M€) no estaba prevista.",
        "BAJO — Paralelismo con Valencia reforzado: mismo patrón de financiación mixta, canon elevado y opacidad que derivó en una deuda pública superior a 150 M€.",
    ]

    pendientes = [
        "Número de expediente verificado del contrato de construcción (UTE Acciona-Eiffage): el portal muestra 24/226 y 25/052 duplicados; confirmar cuál es el oficial.",
        "Expediente e IVA del Pit Building (68,1 M€): la fuente primaria de Eiffage no especifica si es con o sin IVA.",
        "Expediente e importe del contrato de gradas temporales (~98.000 plazas) y de vallas/barreras de seguridad.",
        "Canon anual a FOM/Liberty Media: oficialmente desconocido.",
        "Aportación de la Comunidad (1,9 M€) e IFEMA (1,2-0,7 M€) del Destination Signage Package: pendientes de documento primario.",
        "Adjudicación de 25/211 (524.000 € PBL) y 24/047 R (874.500 € PBL anual).",
        "Coste extraordinario de seguridad, emergencias y transporte: solicitar por Transparencia el coste imputado.",
        "Coste de SUMMA 112, DGT, AENA/ENAIRE, Ejército del Aire, helicópteros y antidrones.",
        "Importe y expediente de la pasarela de ganado sobre la M-11 (6-10 M€).",
        "Resolución del litigio Dromo-Tilke (6 M€).",
    ]

    cambios = [
        "🔧 Corrección de base: Pit Building 68,1 M€ era ADICIONAL y no estaba en el contador.",
        "🔧 Corrección de base: circuito con adjudicatario erróneo (Dragados) quintuplicado -> UTE Acciona-Eiffage.",
        "🔧 Corrección de base: deduplicados 25/187 (×15), 25/140 (×12), 26/113 (×11) y otros expedientes repetidos.",
        "🔧 Corrección de base: Fan Zone Red Bull Sol (121.000 €) liquidada a 0,00 € — retirada.",
        "🔧 Corrección de base: retirada la hipótesis del canon 48 M€/año (480 M€); canon desconocido.",
        "🆕 Aportación municipal 1,9 M€ (BOAM 07/09/2026) + TRAGSATEC 167.354,13 € + expedientes 25/211 y 24/047 R.",
        "🆕 Estimación de servicios públicos extraordinarios: ≈2,6 M€ (rango 1,68-3,82 M€), 0 € confirmado.",
    ]

    comparativa = {
        "coste_total_valencia": 150000000,
        "coste_total_valencia_texto": "Más de 150 millones de euros de deuda pública del GP de Valencia (F1, 2008-2012); agujero estimado en más de 300 M€ según El Diario",
        "factores_riesgo_compartidos": [
            "Financiación mixta pública-privada con discurso de coste cero",
            "Canon FOM elevado sin soporte documental público",
            "Infraestructura temporal a gran escala sin expedientes publicados antes del evento",
            "Costes de seguridad, movilidad y servicios públicos sin presupuesto oficial",
            "Ausencia de auditoría independiente previa",
            "Entidad pública (Ayuntamiento/IFEMA) como paraguas jurídico y financiero",
            "Contratos auxiliares y modificados no previstos",
            "Recurso judicial medioambiental activo durante la construcción",
        ],
        "porcentaje_similitud_riesgo": 80,
        "justificacion": "El modelo de Madrid replica los factores estructurales de riesgo de Valencia. La diferencia es la infraestructura ferial permanente de IFEMA. Los datos de septiembre de 2026 refuerzan el paralelismo: gasto de IFEMA cercano a 180 M€, canon FOM sin publicar, VAN -18 M€ y TIR -0,961% según la Memoria de IFEMA, y ausencia de expedientes verificados para los mayores contratos (~151 M€). Similitud de riesgo: 80%.",
    }

    fuentes = [
        "https://www.eiffage.es/proyectos/pit-building-formula-1-madrid",
        "https://licitaciones2.ifema.es",
        "https://www.madrid.es",
        "https://contrataciondelestado.es",
        "https://www.eldiario.es/madrid/somos/quimera-cero-gasto-publico-formula-1-183-millones-ifema-coste-patrocinio-obras-colaterales_1_13495673.html",
        "https://www.publico.es/politica/formula-1-costara-ano-319-millones-euros-arcas-publicas-madrilenas-estudio.html",
        "https://www.infolibre.es/medioambiente/f1-llega-madrid-conozca-coste-real-impacto-arcas-publicas_1_2235619.html",
        "https://www.epe.es/es/madrid/20260902/madring-gana-primera-carrera-reloj-pista-gradas-listas-133844881",
        "https://revistascratch.com/formula1/noticia/la-fia-da-luz-verde-a-las-obras-de-madring-y-refuerza-el-gp-de-espana-2026-75482",
        "https://www.formula1.it/news/30934/1/scoppia-il-caso-madring-causa-milionaria-a-pochi-mesi-dal-gp-di-formula-1",
        "https://madring.com",
    ]

    costes_indirectos = [
        {"organismo": "Delegación del Gobierno / Interior", "concepto": "Policía Nacional + Guardia Civil (~1.500 agentes/día × 3 días)",
         "estimacion": "900.000 - 2.000.000 € (central ≈1,40 M€)",
         "nota": "Coste marginal estimado; no el coste económico completo."},
        {"organismo": "Ayuntamiento de Madrid", "concepto": "Policía Municipal (>1.000 efectivos)",
         "estimacion": "200.000 - 450.000 € (central ≈0,30 M€)", "nota": "Coste extraordinario atribuible al GP."},
        {"organismo": "Ayuntamiento de Madrid", "concepto": "SAMUR-Protección Civil (>250 efectivos + 36 ambulancias + PSA)",
         "estimacion": "80.000 - 200.000 € (central ≈0,13 M€)", "nota": "No incluye SUMMA 112."},
        {"organismo": "Ayuntamiento de Madrid", "concepto": "Bomberos Madrid (>60 efectivos)",
         "estimacion": "25.000 - 65.000 € (central ≈0,04 M€)", "nota": "No se dobla con el contrato IFEMA 26/012."},
        {"organismo": "Ayuntamiento de Madrid", "concepto": "Agentes de Movilidad (~60)",
         "estimacion": "10.000 - 25.000 € (central ≈0,015 M€)", "nota": "Regulación previa de 400-500 camiones."},
        {"organismo": "Metro de Madrid", "concepto": "Refuerzo L4/L5/L8 + seguridad",
         "estimacion": "150.000 - 400.000 € (central ≈0,25 M€)", "nota": "No se multiplica el coste ordinario por el titular '250%'."},
        {"organismo": "Cercanías (Renfe)", "concepto": "Frecuencias hasta 5 min + composiciones dobles",
         "estimacion": "200.000 - 500.000 € (central ≈0,32 M€)", "nota": "Obligación de servicio público estatal."},
        {"organismo": "EMT Madrid", "concepto": "5 lanzaderas gratuitas, hasta 49 buses (~1.767 h-bus)",
         "estimacion": "110.000 - 180.000 € (central ≈0,14 M€)", "nota": "Verificable en las cuentas de EMT."},
    ]

    prev = load(LATEST_FILE)
    final = {
        "fecha": EXEC_DATE, "fecha_madrid": EXEC_DATETIME,
        "resumen_ejecutivo": resumen,
        "nuevos_hallazgos": hallazgos,
        "riesgos_detectados": riesgos,
        "partidas_pendientes_confirmar": pendientes,
        "cambios_detectados": cambios,
        "comparativa_valencia": comparativa,
        "fuentes_consultadas": fuentes,
        "contratos": cs,
        "coste_acumulado_confirmado": confirmado,
        "coste_acumulado_texto": f"{cm:.1f} M€ (adjudicaciones con soporte oficial, incluye Pit Building 68,1 M€ adicional). No incluye canon FOM.",
        "coste_comprometido": comprometido,
        "coste_comprometido_texto": f"{cpm:.1f} M€ (mínimo de compromisos identificados: confirmado + aportación municipal 1,9 M€).",
        "incremento_respecto_anterior": 0,
        "estimacion_servicios_extraordinarios": {
            "importe": SERVICIOS_EXTRA_ESTIMACION, "rango": "1.680.000 - 3.820.000 €",
            "texto": "Servicios públicos extraordinarios de seguridad, emergencias y transporte GP 2026",
            "confirmado": 0,
            "nota": "Estimación central; 0 € confirmado hasta localizar liquidaciones.",
        },
        "coste_total_estimado_provisional": total,
        "coste_total_estimado_provisional_texto": f"≈{tm:.1f} M€ (compromisos + servicios extraordinarios estimados), antes de canon FOM y costes operativos sin cuantificar.",
        "proyeccion_10_anios": prev.get("proyeccion_10_anios", {}),
        "costes_indirectos": costes_indirectos,
        "costes_indirectos_total_estimado": "≈1.680.000 - 3.820.000 € (central ≈2,60 M€) por edición — ESTIMACIÓN, 0 € confirmado",
    }

    ARCHIVE_DIR.mkdir(exist_ok=True)
    save(ARCHIVE_DIR / f"{EXEC_DATE}.json", final)
    save(LATEST_FILE, final)

    timeline = load(TIMELINE_FILE) if TIMELINE_FILE.exists() else []
    if timeline and timeline[-1].get("fecha") == EXEC_DATE:
        timeline = timeline[:-1]
    timeline.append({"fecha": EXEC_DATE, "coste_acumulado": confirmado, "coste_texto": final["coste_acumulado_texto"],
                     "coste_comprometido": comprometido, "coste_comprometido_texto": final["coste_comprometido_texto"],
                     "num_contratos": len(cs), "porcentaje_riesgo_valencia": 80})
    save(TIMELINE_FILE, timeline)

    from generate_pages import build_site
    build_site(final)

    print("=" * 60)
    print("Contratos: %d (antes 143)" % len(cs))
    print("Confirmado: %.2f M" % cm)
    print("Mínimo comprometido: %.2f M" % cpm)
    print("Estimación ampliada: %.2f M" % tm)


if __name__ == "__main__":
    main()
