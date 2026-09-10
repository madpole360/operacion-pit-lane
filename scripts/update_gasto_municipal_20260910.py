"""
Revisión del gasto del Ayuntamiento de Madrid vinculado a la F1 — 2026-09-10
============================================================================
Incorpora el contador municipal específico (independiente del contador IFEMA):

- Mínimo municipal directamente F1: 1.911.878,81 € (1,9 M€ adenda + 11.878,81 €
  merchandising 300/2026/02102), ya ambos en el contador global.
- Nuevo: SP26-00246 (18.059,25 €, Madrid Destino, patrocinio World Motorsport
  Tourism Congress) — asociado al motor, no directamente GP.
- FITUR 2025: 60.121,11 € PBL de "elementos promocionales F1" (pendiente reparto).
- Operativo estimado: seguridad/emergencias ≈485.000 € + EMT ≈140.000 €.
- Ingresos municipales pendientes: ICIO, TPSU, canon demanial, tasas de ocupación.
"""
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT / "docs"
ARCHIVE_DIR = DOCS_DIR / "archive"
LATEST_FILE = DOCS_DIR / "latest.json"
CONTRACTS_FILE = DOCS_DIR / "contracts.json"

MADRID_TZ = timezone(timedelta(hours=2))
NOW = datetime.now(MADRID_TZ)
EXEC_DATE = "2026-09-10"
EXEC_DATETIME = NOW.strftime("%Y-%m-%d %H:%M")

CONFIRMED_STATES = ("adjudicado", "ejecutado", "en_ejecución", "en_ejecucion")

DIRECTO = 1_911_878.81      # 1.900.000 + 11.878,81
ASOCIADO = 1_929_938.06     # directo + 18.059,25 (motorsport congress)
FITUR_PBL = 60_121.11
OPERATIVO_SEG = 485_000.0
OPERATIVO_EMT = 140_000.0
TOTAL_BRUTO = 2_536_878.81  # 1.911.878,81 + 485.000 + 140.000


def load(p):
    return json.loads(p.read_text(encoding="utf-8"))


def save(p, data):
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def add_contract():
    cs = load(CONTRACTS_FILE)
    nuevo = {
        "descubierto_el": EXEC_DATE,
        "fecha": "2026-06-03",
        "organismo": "Madrid Destino",
        "expediente": "SP26-00246",
        "adjudicatario": "No especificado",
        "concepto": ("Patrocinio del World Motorsport Tourism Congress (asociado a la estrategia de turismo "
                     "del motor, no directamente al GP de F1)."),
        "importe": 18059.25,
        "importe_texto": "18.059,25 € (adjudicación)",
        "estado": "adjudicado",
        "nivel_confianza": "confirmado",
        "vinculo": "asociado",
        "fuente": "Registro de contratos menores del Ayuntamiento de Madrid",
    }
    if not any(c.get("expediente") == "SP26-00246" for c in cs):
        cs.append(nuevo)
    save(CONTRACTS_FILE, cs)
    return cs


def compute(cs):
    confirmado = sum(c.get("importe", 0) or 0 for c in cs if c.get("estado") in CONFIRMED_STATES)
    comprometido = confirmado + sum(c.get("importe", 0) or 0 for c in cs if c.get("estado") == "comprometido")
    return confirmado, comprometido


def main():
    cs = add_contract()
    confirmado, comprometido = compute(cs)
    d = load(LATEST_FILE)
    prev_conf = d.get("coste_acumulado_confirmado", confirmado)

    contador_municipal = {
        "directo_f1": {
            "importe": DIRECTO,
            "texto": "1.911.878,81 € (compromiso + adjudicación directa)",
            "desglose": [
                "Aportación adicional Madrid Destino (adenda, BOAM 07/09/2026): 1.900.000 €",
                "Merchandising preventivo (300/2026/02102): 11.878,81 €",
            ],
        },
        "asociado_motor": {
            "importe": ASOCIADO,
            "texto": "1.929.938,06 € (directo + patrocinio World Motorsport Tourism Congress 18.059,25 €)",
        },
        "fitur_f1_pendiente": {
            "importe": FITUR_PBL,
            "texto": "60.121,11 € PBL (elementos promocionales F1 en FITUR 2025; reparto Ayto/CAM pendiente)",
        },
        "operativo_estimado": {
            "seguridad_emergencias": "≈485.000 € (Policía Municipal 300k + SAMUR 130k + Bomberos 40k + Movilidad 15k)",
            "emt": "≈140.000 € (5 servicios especiales, rango 110k-180k)",
            "total_estimado": "≈625.000 € (no confirmado)",
        },
        "total_bruto_2026": {
            "importe": TOTAL_BRUTO,
            "texto": "≈2,54 M€ (1.911.878,81 € documentado + ≈625.000 € operativo estimado)",
        },
        "ingresos_pendientes": [
            "ICIO y tasas urbanísticas por las obras del circuito (expediente de licencia con 131 informes)",
            "TPSU (Tasa por Prestación de Servicios Urbanísticos) — el Ayuntamiento cita 'fórmula 1' como supuesto",
            "Canon/tasa de la autorización demanial de ocupación de viales (10 agosto - 20 septiembre)",
            "Tasas de ocupación de vía pública de las activaciones (Callao, Colón, Gran Vía, Serrano, Puente del Rey)",
        ],
        "nota": ("Contador municipal independiente del contador global IFEMA. No incluye limpieza/SELUR, "
                 "gestión de tráfico previa/posterior ni servicios técnicos. No descuenta ingresos (ICIO, "
                 "TPSU, canon demanial, tasas)."),
    }

    resumen = d.get("resumen_ejecutivo", "")
    frase = (
        " En el plano municipal, el mínimo directamente documentado asciende a 1.911.878,81 € (aportación "
        "adicional de 1,9 M€ + merchandising 11.878,81 €); sumando el patrocinio del World Motorsport Tourism "
        "Congress (18.059,25 €) son 1.929.938,06 € asociados al motor. Con la estimación operativa de seguridad, "
        "emergencias y EMT (≈625.000 €), el coste municipal bruto provisional 2026 ronda los 2,54 M€, antes de "
        "limpieza/SELUR y sin descontar ingresos por ICIO, TPSU, canon demanial y tasas de ocupación."
    )
    if "En el plano municipal" not in resumen:
        d["resumen_ejecutivo"] = resumen.rstrip() + frase

    hallazgos = [
        "[2026-09-10] Mínimo municipal directamente F1: 1.911.878,81 € = aportación adicional de 1,9 M€ (BOAM 07/09/2026) + merchandising preventivo 11.878,81 € (exp. 300/2026/02102).",
        "[2026-09-10] Madrid Destino: 18.059,25 € (exp. SP26-00246, 3-VI-2026) de patrocinio del World Motorsport Tourism Congress — asociado al motor, no directamente al GP.",
        "[2026-09-10] FITUR 2025: 60.121,11 € PBL de 'elementos promocionales relativos Fórmula 1' dentro del stand conjunto (exp. PR24-0071, 531.109,92 € PBL / 488.620 € formalizado); reparto Ayto/Comunidad pendiente.",
        "[2026-09-10] Los 1,9 M€ de septiembre son adicionales al convenio turístico donde Madrid ya aporta 2 M€/año (Madrid Turismo by IFEMA: 38,4 M€ 2025-2027). Solo los 1,9 M€ son atribuibles específicamente al GP.",
        "[2026-09-10] Dispositivo municipal de ~1.350 efectivos (Policía Municipal >1.000, SAMUR-PC >250, Bomberos >60, Movilidad ~50). Estimación marginal ≈485.000 € (no confirmado; se ejecuta en nóminas ordinarias).",
        "[2026-09-10] EMT: 5 servicios especiales gratuitos del GP; coste incremental estimado ≈140.000 € (110k-180k). Antecedente SE875/876/877 (F1 junio 2025) con coste sin publicar.",
        "[2026-09-10] Limpieza/SELUR: sin licitación específica F1; se activa dentro de contratos ordinarios (292,1 M€ limpieza + 22,7 M€ SELUR). Coste pendiente de orden de trabajo y certificación.",
        "[2026-09-10] Autorización demanial de ocupación de viales (10 agosto - 20 septiembre, Ribera del Sena, Vía de Dublín, Francisco Umbral): el Ayuntamiento cobra tasas (TPSU cita 'fórmula 1' como supuesto). Posible ingreso pendiente.",
        "[2026-09-10] ICIO y licencias: el expediente de licencia del circuito llegó a tener 131 informes; la recaudación por ICIO/tasas urbanísticas de MADRING no está localizada.",
        "[2026-09-10] Actuaciones del centro (Callao/Williams, Colón/Audi, Gran Vía/Alpine): sin contrato municipal de producción; posible coste indirecto (policía, limpieza, señalización) y tasas de ocupación por aclarar.",
    ]

    riesgos = [
        "ALTO — Las tres bolsas municipales mayores (personal, EMT, limpieza/SELUR) no generan contratos nuevos: se ejecutan dentro de servicios ya contratados y presupuestados, por lo que no aparecerán como 'contrato F1'.",
        "ALTO — Ventana de publicación: el registro municipal (2.859 contratos menores, 20,8 M€ en 2026) solo muestra 'Fórmula 1' explícitamente en el de 11.878,81 €; hay que buscar por beneficiario, proyecto, orden de servicio y factura.",
        "MEDIO — Tensión contable: en el Pleno de marzo Almeida afirmó 'no sale un euro del Ayuntamiento para la celebración'; en septiembre se aprueban 1,9 M€. Depende de dónde se trace la frontera entre 'celebración' y 'promoción asociada al GP'.",
        "MEDIO — El coste municipal neto puede ser menor de lo que aparenta: faltan por descontar ICIO, TPSU, canon demanial y tasas de ocupación (posibles ingresos).",
    ]

    partidas = [
        "Certificaciones de horas extraordinarias, productividad y órdenes de servicio de Policía Municipal, SAMUR, Bomberos y Agentes de Movilidad.",
        "Coste de los servicios especiales EMT del GP y de SE875/876/877 (presentación F1 junio 2025).",
        "Órdenes de trabajo y certificación económica de limpieza/SELUR tras el GP.",
        "Canon/tasa de la autorización demanial de ocupación de viales + TPSU + ICIO + tasas de ocupación (ingresos municipales).",
        "Memoria justificativa anual del convenio (cláusula de justificación): detalle del Destination Signage Package y acciones F1.",
        "Reparto Ayuntamiento/Comunidad de los 60.121,11 € de FITUR 2025 (exp. PR24-0071).",
    ]

    d["contador_municipal"] = contador_municipal
    d["nuevos_hallazgos"] = hallazgos + d.get("nuevos_hallazgos", [])
    d["riesgos_detectados"] = riesgos + d.get("riesgos_detectados", [])
    d["partidas_pendientes_confirmar"] = partidas + d.get("partidas_pendientes_confirmar", [])
    d["contratos"] = cs
    d["coste_acumulado_confirmado"] = confirmado
    d["coste_acumulado_texto"] = f"{confirmado/1e6:.1f} M€ (adjudicaciones con soporte oficial). No incluye canon FOM."
    d["coste_comprometido"] = comprometido
    d["coste_comprometido_texto"] = f"{comprometido/1e6:.1f} M€ (mínimo de compromisos: confirmado + aportaciones formalizadas)."
    d["incremento_respecto_anterior"] = round(confirmado - prev_conf, 2)
    d["fecha"] = EXEC_DATE
    d["fecha_madrid"] = EXEC_DATETIME

    save(LATEST_FILE, d)
    daily = ARCHIVE_DIR / f"{EXEC_DATE}.json"
    if daily.exists():
        save(daily, d)

    from generate_pages import build_site
    build_site(d)

    print("=" * 60)
    print("Contador municipal directo F1: %.2f M" % (DIRECTO / 1e6))
    print("Total bruto municipal 2026: %.2f M" % (TOTAL_BRUTO / 1e6))
    print("Confirmado global: %.4f M (SP26-00246 sumado)" % (confirmado / 1e6))
    print("Contratos: %d" % len(cs))


if __name__ == "__main__":
    main()
