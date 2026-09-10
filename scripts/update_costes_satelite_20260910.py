"""
Investigación especial: costes satélite de la F1 en Madrid — 2026-09-10
=======================================================================
Incorpora el único nuevo gasto público confirmado (merchandising preventivo,
exp. 300/2026/02102, 11.878,81 €) y documenta la "F1 paralela" (activaciones
privadas, Tech Summit, municipios, Red Bull on Rails, vinilado Metro) y dos
bolsas de gasto promocional que NO se suman al contador:

- Destination Signage Package: ≈5 M€ (1,9 M€ Ayto confirmado + 3,1 M€ pendientes).
- Madrid Beats: 18,8 M€ (campaña turística, no imputable íntegramente a la F1).
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


def load(p):
    return json.loads(p.read_text(encoding="utf-8"))


def save(p, data):
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def add_contract():
    cs = load(CONTRACTS_FILE)
    nuevo = {
        "descubierto_el": EXEC_DATE,
        "fecha": "2026-07-24",
        "organismo": "Ayuntamiento de Madrid",
        "expediente": "300/2026/02102",
        "adjudicatario": "Modern Depot, S.L.",
        "concepto": ("Merchandising para la prevención de la violencia sexual y la LGTBIfobia en el Gran "
                     "Premio de Fórmula 1 de Madrid (puntos violeta y arcoíris)."),
        "importe": 11878.81,
        "importe_texto": "11.878,81 € (adjudicación)",
        "estado": "adjudicado",
        "nivel_confianza": "confirmado",
        "fuente": "Registro de Contratos Menores del Ayuntamiento de Madrid",
    }
    if not any(c.get("expediente") == "300/2026/02102" for c in cs):
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
    prev = load(LATEST_FILE)
    incremento = round(confirmado - prev.get("coste_acumulado_confirmado", confirmado), 2)

    resumen = (
        "Investigación especial de los 'costes satélite' de la F1 fuera de MADRING, a 10-IX-2026. Existe una "
        "auténtica 'F1 paralela', pero no toda la paga el contribuyente: Callao (Atlassian Williams), Colón (Audi), "
        "Gran Vía (Alpine) y el espectáculo de 252 drones (Banco Santander) son activaciones fundamentalmente "
        "privadas (coste público localizado 0 €); el videomapping de Sol está organizado por Tag Heuer sobre la "
        "Real Casa de Correos; y el 'Red Bull on Rails' pudo incluso generar ingresos a Metro, que normalmente "
        "cobra por los rodajes. El MADRING Tech Summit (Comunidad) y 'Madrid con el Motor' (8 municipios) sí son "
        "institucionales, pero no se localiza contrato de producción. El único gasto público nuevo confirmado es de "
        "11.878,81 € (merchandising preventivo, exp. 300/2026/02102). El coste confirmado se mantiene en "
        f"{confirmado/1e6:.1f} M€ y el mínimo comprometido en {comprometido/1e6:.1f} M€. Se abren dos bolsas "
        "separadas, no sumadas: el Destination Signage Package (≈5 M€ de promoción vinculada al GP, con 1,9 M€ "
        "municipales ya acreditados) y la campaña turística Madrid Beats (18,8 M€, no imputable íntegramente a la "
        "F1). Prioridad: localizar seis expedientes concretos (factura Metro–Red Bull, respuesta PI-233/2024, "
        "producción del Tech Summit, encargos de Pueblos con Vida, convenio Tag Heuer–Comunidad y ocupación de vía "
        "pública)."
    )

    hallazgos = [
        "[2026-09-10] Las activaciones 'F1 en las calles' son en gran parte privadas: Callao (Atlassian Williams Racing), Colón ('La Monumental, F1 City Experience', organizada por Audi) y Gran Vía (Alpine). Coste público localizado: 0 €. Pendiente: ocupación de vía pública, exenciones de tasas, seguridad, limpieza, vallados, electricidad.",
        "[2026-09-10] El espectáculo de 252 drones LED en Puente del Rey (4-IX, 13 min) está 'organizado por Banco Santander'. Coste público confirmado: 0 €; coste privado no publicado.",
        "[2026-09-10] El videomapping de la Real Casa de Correos (10-12-IX, 4 pases diarios entre 22:00 y 23:30) está 'organizado por su patrocinador, Tag Heuer'. Coste público confirmado: 0 €. Referencia de mercado: 28.500 € sin IVA (videomapping de Madrid Destino 2024).",
        "[2026-09-10] El MADRING Tech Summit (9-11-IX, Real Casa de Correos) es institucional: consejerías de Digitalización y Educación y Agencia de Ciberseguridad, con PwC, Salesforce, Oracle, Microsoft, HPE, IBM, Cisco, AWS, CrowdStrike y ElevenLabs. No se localiza contrato de producción específico.",
        "[2026-09-10] La Comunidad extiende la F1 a 8 municipios con 'Madrid con el Motor' (patrocinado por Pueblos con Vida): Alcobendas, Villa del Prado, Las Rozas, Arroyomolinos, Paracuellos de Jarama, Leganés, La Cabrera y Valdemorillo. Sin presupuestos individuales publicados.",
        "[2026-09-10] 'Red Bull on Rails': un RB8 adaptado circuló por vías y depósitos de Metro (7-9 de abril, 3 noches, >80 personas/noche, ~40 km, cortes de tensión y dresinas). Metro normalmente cobra por rodajes (485.575 € por 122 rodajes 2015-2021). Coste público: 0 € localizado; posible ingreso para Metro.",
        "[2026-09-10] El vinilado del tren de Línea 8 (enero 2024, anuncio de la F1) tiene pregunta oficial sin contestación localizada: PI-233/2024, RGEP.2976 ('coste total del vinilado... Fórmula 1').",
        "[2026-09-10] Nuevo gasto público confirmado: 11.878,81 € (exp. 300/2026/02102, Modern Depot S.L., 24-VII-2026) por merchandising para la prevención de la violencia sexual y LGTBIfobia en el GP (puntos violeta y arcoíris, atendidos por profesionales municipales y Voluntarios por Madrid).",
        "[2026-09-10] La Comunidad lanza 'Madrid Beats': campaña turística internacional de 18,8 M€ (13 países, más de 30 ciudades, hasta diciembre 2027) que usa la F1 como plataforma de comunicación (audiencia global >70 M espectadores). NO imputable íntegramente al GP.",
        "[2026-09-10] Destination Signage Package: ≈5 M€ (1,9 M€ Ayuntamiento confirmados por BOAM + 1,9 M€ Comunidad + 1,2 M€ IFEMA pendientes de adenda). Directamente asociado al GP. No sumar ambos conceptos hasta ver la adenda completa.",
    ]

    riesgos = [
        "CRÍTICO — El agujero de transparencia ya no es solo IFEMA: también Comunidad de Madrid, Metro, Madrid Destino y los ayuntamientos. Seis documentos prioritarios: factura Metro–Red Bull, respuesta PI-233/2024, producción del Tech Summit, encargos Pueblos con Vida, convenio Tag Heuer–Comunidad y ocupación de vía pública.",
        "ALTO — Metro–Red Bull on Rails: si Metro cedió 3 noches, talleres, personal, cortes eléctricos, dresinas, bomberos y técnicos sin facturar, sería aportación pública en especie; si los facturó, ingreso para Metro. Necesitamos el importe.",
        "ALTO — MADRING Tech Summit: uso de recursos públicos (Real Casa de Correos, personal, Agencia de Ciberseguridad) sin contrato de producción localizado.",
        "ALTO — 'Madrid con el Motor / Pueblos con Vida': encargos a 8 municipios sin costes desglosados publicados.",
        "ALTO — Vinilado del tren de Línea 8: coste preguntado oficialmente (PI-233/2024) sin contestación localizada.",
        "MEDIO — Videomapping de Sol: Tag Heuer como organizador, pero uso del edificio público de la Comunidad; falta aclarar cualquier aportación pública.",
        "MEDIO — Destination Signage (≈5 M€) y Madrid Beats (18,8 M€): riesgo de duplicidad contable; no sumar ambos hasta ver la adenda y el deslinde (Madrid Turismo by IFEMA dispone de 12,8 M€/año).",
    ]

    partidas = [
        "Factura/contrato Metro–Red Bull para 'On Rails' (ingreso vs aportación en especie de Metro).",
        "Respuesta a PI-233/2024 (RGEP.2976): coste total del vinilado F1 del tren de Línea 8.",
        "Expediente de producción del MADRING Tech Summit (contrato marco/genérico de organización de eventos de la Comunidad).",
        "Encargos de 'Madrid con el Motor / Pueblos con Vida' (simuladores, pantallas LED, producción técnica, dinamización).",
        "Convenio/autorización Tag Heuer–Comunidad para el videomapping de Sol.",
        "Expedientes de ocupación de vía pública de Callao, Colón, Gran Vía, Serrano y Puente del Rey (tasas y bonificaciones).",
        "Adenda completa del Destination Signage Package (Comunidad 1,9 M€ + IFEMA 1,2 M€).",
        "Deslinde de Madrid Beats (18,8 M€) respecto a la F1 y a Madrid Turismo by IFEMA (12,8 M€/año).",
    ]

    promocion_asociada = {
        "destination_signage": {
            "concepto": "Destination Signage Package (promoción internacional vinculada al GP)",
            "total": "≈5 M€",
            "confirmado": "1,9 M€ (Ayuntamiento, BOAM 07/09/2026)",
            "pendiente": "3,1 M€ (Comunidad 1,9 M€ + IFEMA 1,2 M€, pendientes de adenda)",
            "nota": "Directamente asociado al GP. No sumar los 3,1 M€ pendientes hasta ver la adenda completa.",
        },
        "madrid_beats": {
            "concepto": "Campaña turística internacional 'Madrid Beats'",
            "total": "18,8 M€ (13 países, 30+ ciudades, hasta diciembre 2027)",
            "imputable": "No exclusivamente imputable a la F1",
            "nota": "Usa el GP como plataforma. Posible solapamiento con Madrid Turismo by IFEMA (12,8 M€/año).",
        },
        "activaciones_privadas": {
            "concepto": "Activaciones del centro: Callao/Williams, Colón/Audi, Gran Vía/Alpine, drones/Santander, TAG/Serrano",
            "coste_publico": "0 € localizado",
            "nota": "Organizadas por marcas privadas. Pendiente: ocupación de vía, tasas, seguridad, limpieza, cesión de espacios.",
        },
    }

    d = prev
    d["resumen_ejecutivo"] = resumen
    d["nuevos_hallazgos"] = hallazgos + d.get("nuevos_hallazgos", [])
    d["riesgos_detectados"] = riesgos + d.get("riesgos_detectados", [])
    d["partidas_pendientes_confirmar"] = partidas + d.get("partidas_pendientes_confirmar", [])
    d["promocion_asociada"] = promocion_asociada
    d["contratos"] = cs
    d["coste_acumulado_confirmado"] = confirmado
    d["coste_acumulado_texto"] = f"{confirmado/1e6:.1f} M€ (adjudicaciones con soporte oficial). No incluye canon FOM."
    d["coste_comprometido"] = comprometido
    d["coste_comprometido_texto"] = f"{comprometido/1e6:.1f} M€ (mínimo de compromisos: confirmado + aportaciones formalizadas)."
    d["incremento_respecto_anterior"] = incremento
    d["fecha"] = EXEC_DATE
    d["fecha_madrid"] = EXEC_DATETIME

    save(LATEST_FILE, d)
    daily = ARCHIVE_DIR / f"{EXEC_DATE}.json"
    if daily.exists():
        save(daily, d)

    from generate_pages import build_site
    build_site(d)

    print("=" * 60)
    print("Nuevo contrato confirmado: 11.878,81 € (300/2026/02102)")
    print("Confirmado: %.4f M" % (confirmado / 1e6))
    print("Comprometido: %.4f M" % (comprometido / 1e6))
    print("Incremento: +%.2f €" % incremento)
    print("Contratos: %d" % len(cs))


if __name__ == "__main__":
    main()
