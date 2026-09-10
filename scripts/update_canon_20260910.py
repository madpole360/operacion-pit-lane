"""
Actualización de la hipótesis del canon/derechos F1 — 2026-09-10
=================================================================
Incorpora la mejor cifra disponible de derechos F1 (~277 M€/10 años) como
hipótesis de confianza media (NO coste confirmado) y actualiza la proyección
a 10 años y el resumen ejecutivo.

Fuentes:
- Consejo de Transparencia de la CAM (2025): IFEMA bajo cláusulas de
  confidencialidad estrictas; condiciones económicas denegadas.
- Más Madrid / El País (10-IX-2026): 277 M€ comprometidos en derechos, 10 años.
- Cuentas de IFEMA: riesgo contractual máximo de 270.362.597 € con F1.
- Coincidencia matemática: 22 M€ (2026) +5%/año = 276,71 M€ ≈ 277 M€.
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

MADRID_TZ = timezone(timedelta(hours=2))
NOW = datetime.now(MADRID_TZ)
EXEC_DATETIME = NOW.strftime("%Y-%m-%d %H:%M")

CANON_TOTAL = 277_000_000.0
CANON_MEDIA_ANUAL = 27_700_000.0
RIESGO_CONTRACTUAL_IFEMA = 270_362_597.0


def load(p):
    return json.loads(p.read_text(encoding="utf-8"))


def save(p, data):
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    d = load(LATEST_FILE)
    confirmado = d.get("coste_acumulado_confirmado", 0)
    comprometido = d.get("coste_comprometido", 0)
    # Dimensión económica conocida/estimada = compromisos localizados + derechos F1
    total_estimado = comprometido + CANON_TOTAL

    canon_fom = {
        "total_10_anios": CANON_TOTAL,
        "total_10_anios_texto": "~277 millones de euros por 10 ediciones (2026-2035)",
        "media_anual": CANON_MEDIA_ANUAL,
        "media_anual_texto": "27,7 M€/año de media",
        "confirmado": False,
        "nivel_confianza": "medio",
        "hipotesis_estructura": "22 M€ en 2026 con subida del 5% anual hasta 34,13 M€ en 2035 (total 276,71 M€)",
        "riesgo_contractual_ifema": RIESGO_CONTRACTUAL_IFEMA,
        "riesgo_contractual_ifema_texto": "270.362.597 € de riesgo contractual máximo reconocido en las cuentas de IFEMA",
        "nota": ("IFEMA y F1 no publican el canon (cláusulas de confidencialidad confirmadas por el "
                 "Consejo de Transparencia en 2025). La cifra de ~277 M€ procede de Más Madrid y es "
                 "reproducida por El País el 10-IX-2026. NO es coste confirmado."),
        "fuentes": [
            "https://elpais.com/espana/madrid/ (10-IX-2026)",
            "Consejo de Transparencia de la Comunidad de Madrid (2025)",
            "Cuentas anuales de IFEMA",
        ],
    }

    resumen = (
        f"La imagen económica del proyecto queda así a 10-IX-2026, un día antes del GP: (1) coste confirmado "
        f"{confirmado/1e6:.1f} M€ —adjudicaciones con soporte oficial, incluyendo el Pit Building de "
        f"68,1 M€ adicional al circuito—; (2) mínimo comprometido {comprometido/1e6:.1f} M€ (sumando la aportación "
        f"municipal de 1,9 M€); (3) servicios públicos extraordinarios ≈2,6 M€; y (4) los derechos/canon F1, que "
        f"siguen sin publicarse oficialmente (el Consejo de Transparencia confirmó en 2025 que IFEMA está sujeta a "
        f"cláusulas de confidencialidad estrictas y denegó las 'condiciones económicas'). La mejor cifra disponible "
        f"es ≈277 M€ por diez ediciones (Más Madrid, reproducida por El País hoy), coherente con un canon de 22 M€ "
        f"en 2026 con subida del 5% anual —total 276,71 M€— y con el riesgo contractual máximo de 270,36 M€ "
        f"reconocido en las cuentas de IFEMA. Sumando los derechos (~277 M€) a los compromisos localizados "
        f"(~{comprometido/1e6:.1f} M€), la dimensión económica conocida/estimada del proyecto ronda los "
        f"{total_estimado/1e6:.0f} M€, antes de incorporar los costes recurrentes de montaje, seguridad, movilidad, "
        f"limpieza, servicios médicos, personal y operación de las diez ediciones."
    )

    hallazgo_canon = (
        "[2026-09-10] Derechos/canon F1 2026-2035: la mejor cifra disponible es ≈277 M€ por diez ediciones "
        "(Más Madrid, reproducida por El País hoy). Coherente con un canon de 22 M€ en 2026 con subida del 5% "
        "anual (total 276,71 M€) y con el riesgo contractual máximo de 270.362.597 € reconocido en las cuentas de "
        "IFEMA. No publicado oficialmente (confidencialidad); confianza media, NO coste confirmado."
    )

    d["resumen_ejecutivo"] = resumen
    d["nuevos_hallazgos"] = [hallazgo_canon] + d.get("nuevos_hallazgos", [])

    # Riesgos: actualizar el CRÍTICO del canon
    riesgos = d.get("riesgos_detectados", [])
    nuevos_riesgos = []
    for r in riesgos:
        if "canon a FOM" in r.lower() or ("canon" in r.lower() and "48 M" in r):
            nuevos_riesgos.append(
                "CRÍTICO — El canon a FOM/Liberty Media sigue sin publicarse oficialmente a 10-IX-2026. La mejor "
                "cifra disponible es ≈277 M€/10 años (Más Madrid, El País), coherente con 22 M€ en 2026 +5% anual "
                "y con el riesgo contractual de 270,36 M€ de IFEMA. Confianza media; NO es coste confirmado. En "
                "octubre de 2025 Más Madrid citaba 294 M€; la rebaja a 277 M€ no tiene documento que la explique."
            )
        else:
            nuevos_riesgos.append(r)
    d["riesgos_detectados"] = nuevos_riesgos

    # Partidas pendientes: actualizar la del canon
    partidas = d.get("partidas_pendientes_confirmar", [])
    nuevas_partidas = []
    for p in partidas:
        if "canon" in p.lower() and ("fom" in p.lower() or "liberty" in p.lower()):
            nuevas_partidas.append(
                "Canon/derechos F1 2026-2035: importe no publicado oficialmente. Mejor cifra disponible ≈277 M€/10 "
                "años (27,7 M€/año). Prioridad: localizar el documento del que Más Madrid extrae los 277 M€ para "
                "confirmar el total, el canon de 2026 y la cláusula de escalado anual."
            )
        else:
            nuevas_partidas.append(p)
    d["partidas_pendientes_confirmar"] = nuevas_partidas

    # Proyección a 10 años actualizada
    d["proyeccion_10_anios"] = {
        "gastos_estimados": int(total_estimado),
        "gastos_estimados_texto": f"~{total_estimado/1e6:.0f} millones de euros (compromisos + derechos F1, sin costes recurrentes)",
        "gastos_desglose": [
            f"Compromisos localizados (obra + Pit Building + aportación municipal): ~{comprometido/1e6:.1f} M€",
            "Derechos F1 2026-2035 (canon): ~277 M€ — hipótesis, no confirmado (27,7 M€/año de media)",
            "Costes recurrentes de 10 ediciones (montaje, seguridad, movilidad, limpieza, servicios médicos): sin cuantificar",
        ],
        "ingresos_estimados": 0,
        "ingresos_estimados_texto": "Sin cifras públicas verificadas",
        "ingresos_desglose": [
            "Venta de entradas (~120.000 espectadores, sold out): importe no publicado",
            "Patrocinios (Santander, Fever, Red Bull, etc.): cuantías no publicadas",
            "Hospitality VIP: MATCH (inversión privada 400 M€), no es ingreso de IFEMA",
        ],
        "balance_neto": 0,
        "balance_neto_texto": "Indeterminado: canon sin confirmar e ingresos sin publicar (VAN de IFEMA: -18 M€ según su Memoria)",
        "nota": ("El canon F1 no está publicado (cláusulas de confidencialidad confirmadas por el Consejo de "
                 "Transparencia en 2025). La mejor cifra disponible es ~277 M€/10 años (Más Madrid, El País, "
                 "10-IX-2026), coherente con un canon de 22 M€ en 2026 con subida del 5% anual y con el riesgo "
                 "contractual máximo de 270,36 M€ de IFEMA. Confianza media; NO es coste confirmado."),
    }

    d["canon_fom"] = canon_fom
    d["fecha_madrid"] = EXEC_DATETIME

    save(LATEST_FILE, d)
    # Mantener el archivo diario coherente
    daily = ARCHIVE_DIR / f"{d.get('fecha', '2026-09-10')}.json"
    if daily.exists():
        save(daily, d)

    from generate_pages import build_site
    build_site(d)

    print("=" * 60)
    print("Canon F1: ~277 M€/10 años (hipótesis, no confirmado)")
    print("Compromisos localizados: %.2f M" % (comprometido / 1e6))
    print("Dimensión conocida/estimada: %.0f M" % (total_estimado / 1e6))


if __name__ == "__main__":
    main()
