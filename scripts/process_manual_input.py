"""
Procesa hallazgos manuales: lee texto de docs/manual-input.txt, lo analiza con
Sonnet para extraer contratos y hallazgos, y los incorpora a la base de datos.
"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT / "docs"
INPUT_FILE = DOCS_DIR / "manual-input.txt"
CONTRACTS_FILE = DOCS_DIR / "contracts.json"
LATEST_FILE = DOCS_DIR / "latest.json"
TODAY = datetime.now().strftime("%Y-%m-%d")

EXTRACT_PROMPT = """Eres un periodista de investigación. Analiza el siguiente texto con
hallazgos manuales sobre el GP de F1 de Madrid (Madring) y extrae:

1. Nuevos contratos/expedientes (con todos los datos disponibles: fecha, organismo,
   expediente, concepto, importe, estado, fuente)
2. Nuevos hallazgos (cada uno empezando con la fecha [YYYY-MM-DD])

Devuelve SOLO un JSON válido con este formato:
{
  "contratos": [
    {
      "fecha": "YYYY-MM-DD",
      "organismo": "Nombre",
      "expediente": "Numero real (formato NN/NNN o NNNNNNNNNN)",
      "adjudicatario": "Nombre o UTE",
      "concepto": "Descripcion",
      "importe": 0.00,
      "importe_texto": "123.456,78 €",
      "estado": "licitado|adjudicado|ejecutado|desistido|pendiente_confirmar",
      "fuente": "URL o descripcion de la fuente"
    }
  ],
  "nuevos_hallazgos": ["[YYYY-MM-DD] texto del hallazgo"]
}

Solo incluye datos que aparezcan EXPLICITAMENTE en el texto. No inventes nada.
Usa español correcto con tildes."""


def process_manual_input():
    if not INPUT_FILE.exists():
        print("❌ No se encontró docs/manual-input.txt")
        print("   Crea ese archivo, pega tus hallazgos y vuelve a ejecutar.")
        sys.exit(1)

    text = INPUT_FILE.read_text(encoding="utf-8").strip()
    if not text:
        print("❌ docs/manual-input.txt está vacío")
        sys.exit(1)

    print(f"📋 Procesando {len(text)} caracteres de texto manual...")

    # Enviar a Sonnet para extraer datos estructurados
    import anthropic
    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        thinking={"type": "disabled"},
        system=EXTRACT_PROMPT,
        messages=[{
            "role": "user",
            "content": f"TEXTO A ANALIZAR:\n\n{text}"
        }]
    )

    raw = response.content[0].text

    # Extraer JSON
    import re
    raw = raw.strip()
    # Limpiar posibles markdown
    m = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', raw, re.DOTALL)
    if m:
        raw = m.group(1).strip()
    # Buscar JSON con balance de llaves
    start = raw.find('{')
    if start >= 0:
        depth = 0
        for i, ch in enumerate(raw[start:], start):
            if ch == '{': depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    raw = raw[start:i+1]
                    break

    extracted = json.loads(raw)
    nuevos_contratos = extracted.get("contratos", [])
    nuevos_hallazgos = extracted.get("nuevos_hallazgos", [])

    print(f"   Contratos extraídos: {len(nuevos_contratos)}")
    print(f"   Hallazgos extraídos: {len(nuevos_hallazgos)}")

    # Cargar datos existentes
    contracts = json.loads(CONTRACTS_FILE.read_text(encoding="utf-8"))
    latest = json.loads(LATEST_FILE.read_text(encoding="utf-8"))

    # Fusionar contratos (misma lógica que el agente)
    import re as _re
    EXP_RE = _re.compile(r"^\d{2}/\d{3,4}$")
    EXP_CM_RE = _re.compile(r"^\d{10}$")

    seen = set()
    for c in contracts:
        seen.add(c.get("expediente", "").strip())

    added = 0
    for c in nuevos_contratos:
        exp = c.get("expediente", "").strip()
        if not (EXP_RE.match(exp) or EXP_CM_RE.match(exp)):
            continue
        if exp in seen:
            continue
        c["descubierto_el"] = TODAY
        contracts.append(c)
        seen.add(exp)
        added += 1

    print(f"   Contratos nuevos añadidos: {added}")

    # Actualizar latest.json
    latest["contratos"] = contracts
    latest["fecha"] = TODAY
    latest["fecha_madrid"] = f"{TODAY} 12:00"

    # Añadir hallazgos al principio
    latest["nuevos_hallazgos"] = nuevos_hallazgos + latest.get("nuevos_hallazgos", [])

    # Recalcular costes
    conf = sum(c.get("importe", 0) or 0 for c in contracts
               if c.get("estado") in ("adjudicado", "ejecutado"))
    comp = sum(c.get("importe", 0) or 0 for c in contracts
               if c.get("estado") in ("adjudicado", "ejecutado", "licitado"))

    latest["coste_acumulado_confirmado"] = conf
    latest["coste_comprometido"] = comp
    latest["coste_acumulado_texto"] = f"{conf/1e6:.1f} M€ (adjudicaciones con soporte oficial)."
    latest["coste_comprometido_texto"] = f"{comp/1e6:.1f} M€ (confirmado + licitaciones activas)."

    # Guardar
    CONTRACTS_FILE.write_text(json.dumps(contracts, ensure_ascii=False, indent=2), encoding="utf-8")
    LATEST_FILE.write_text(json.dumps(latest, ensure_ascii=False, indent=2), encoding="utf-8")

    # Limpiar el archivo de entrada
    INPUT_FILE.write_text(
        f"# Último procesamiento: {TODAY}\n"
        f"# {added} contratos y {len(nuevos_hallazgos)} hallazgos añadidos.\n"
        f"# Pega aquí nuevos hallazgos y vuelve a ejecutar.\n\n", encoding="utf-8")

    print(f"\n✅ Procesamiento completado:")
    print(f"   Contratos: {len(contracts)} total (+{added})")
    print(f"   Confirmado: {conf/1e6:.1f} M€")
    print(f"   Comprometido: {comp/1e6:.1f} M€")
    print(f"   El archivo manual-input.txt se ha limpiado para el próximo uso.")


if __name__ == "__main__":
    process_manual_input()
