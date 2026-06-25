"""Actualizar BD de contratos con nuevos expedientes IFEMA."""
import json
from pathlib import Path
from datetime import datetime

TODAY = datetime.now().strftime("%Y-%m-%d")
ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT / "docs"

latest = json.loads((DOCS_DIR / "latest.json").read_text(encoding="utf-8"))
contracts = json.loads((DOCS_DIR / "contracts.json").read_text(encoding="utf-8"))

nuevos = [
    {
        "descubierto_el": TODAY,
        "fecha": "2026-06-26",
        "organismo": "IFEMA Madrid",
        "expediente": "26/113",
        "concepto": "Suministro, instalacion, mantenimiento y retirada de lonas publicitarias en cubiertas de pabellones IFEMA para el GP de Espana de F1 (ediciones 2026 y 2027). Cierre de ofertas: 26/06/2026.",
        "importe": 572500.00,
        "importe_texto": "572.500,00 € (PBL sin impuestos) / 858.750,00 € (VEC)",
        "estado": "licitado",
        "fuente": "https://licitaciones2.ifema.es/licitacion?numExpediente=26/113"
    },
    {
        "descubierto_el": TODAY,
        "fecha": "2026-06-19",
        "organismo": "IFEMA Madrid",
        "expediente": "26/057",
        "concepto": "Servicio de medicina de emergencias durante montaje, celebracion y desmontaje del GP de Espana de F1 en IFEMA Madrid. Cierre de ofertas: 07/07/2026.",
        "importe": 296200.00,
        "importe_texto": "296.200,00 € (PBL sin impuestos) / 1.036.700,00 € (VEC)",
        "estado": "licitado",
        "fuente": "https://licitaciones2.ifema.es/licitacion?numExpediente=26/057"
    },
    {
        "descubierto_el": TODAY,
        "fecha": "2026-06-15",
        "organismo": "IFEMA Madrid",
        "expediente": "26/027",
        "concepto": "Suministro de medicamentos y material fungible sanitario para el servicio de medicina de emergencias del GP F1 y servicio medico laboral de IFEMA. Cierre: 07/07/2026.",
        "importe": 32280.68,
        "importe_texto": "32.280,68 € (PBL sin impuestos)",
        "estado": "licitado",
        "fuente": "https://licitaciones2.ifema.es/licitacion?numExpediente=26/027"
    },
]

# Fusionar sin duplicados
seen = set()
for c in contracts:
    seen.add(c.get("expediente", ""))
added = 0
for c in nuevos:
    if c["expediente"] not in seen:
        contracts.append(c)
        seen.add(c["expediente"])
        added += 1

# Actualizar latest.json
latest["contratos"] = contracts
latest["fecha"] = TODAY
latest["fecha_madrid"] = f"{TODAY} 12:00"

# Anadir hallazgos
hallazgos = [
    "Detectados 3 nuevos expedientes activos en el portal IFEMA: 26/113, 26/057, 26/027.",
    "Exp. 26/113 (lonas publicitarias F1 2026-2027): PBL 572.500 €, cierre de ofertas HOY 26/06/2026.",
    "Exp. 26/057 (medicina emergencia F1): PBL 296.200 €, VEC 1.036.700 €, cierre 07/07/2026.",
    "Exp. 26/027 (medicamentos y material sanitario): PBL 32.280,68 €, cierre 07/07/2026.",
    "Exp. 25/175 DESISTIDO por error no subsanable en criterios de adjudicacion.",
    "Exp. 26/024 (pasarelas): oferta de NUSSLI IBERIA por 9.731.922,17 €, pendiente adjudicacion formal.",
]
latest["nuevos_hallazgos"] = hallazgos + [h for h in latest.get("nuevos_hallazgos", []) if h not in hallazgos]

# Anadir riesgos
riesgos = [
    "Exp. 26/113 cierra HOY (26/06/2026). Adjudicacion inminente sin tiempo para escrutinio publico.",
    "Exp. 25/175 desistido: indicio de mala planificacion de pliegos que obliga a repetir expedientes.",
    "Tres nuevos expedientes sanitarios/logisticos suman +900.980 € al coste comprometido.",
]
latest["riesgos_detectados"] = riesgos + [r for r in latest.get("riesgos_detectados", []) if r not in riesgos]

# Guardar
(DOCS_DIR / "contracts.json").write_text(json.dumps(contracts, ensure_ascii=False, indent=2), encoding="utf-8")
(DOCS_DIR / "latest.json").write_text(json.dumps(latest, ensure_ascii=False, indent=2), encoding="utf-8")

print(f"✅ Contratos: {len(contracts)} total ({added} nuevos)")
for c in nuevos:
    print(f"   + {c['expediente']}: {c['importe_texto']}")
