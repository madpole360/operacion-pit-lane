"""
Monitor TED Europa — busca licitaciones relacionadas con F1 Madrid/IFEMA/Madring.
API publica, sin autenticacion.
Se integra en el pipeline de investigacion automatica.
"""
import json
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path

TED_API = "https://api.ted.europa.eu/v3/notices/search"
ROOT = Path(__file__).resolve().parent.parent
OUTPUT_FILE = ROOT / "data" / "ted_results.json"


def search_ted(query: str, country: str = "ES", days_back: int = 30) -> list:
    """Busca en TED Europa licitaciones por query y pais."""
    from_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y%m%d")

    payload = {
        "query": query,
        "scope": "ACTIVE",
        "country": country,
        "publicationDateFrom": from_date,
        "fields": [
            "publication-number",
            "title",
            "buyer-name",
            "buyer-country",
            "total-value",
            "currency",
            "publication-date",
            "deadline-date",
            "notice-type",
            "procedure-type",
            "cpv",
            "links",
        ],
        "page": 1,
        "limit": 50,
    }

    req = urllib.request.Request(
        TED_API,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("results", [])
    except Exception as e:
        print(f"   [TED] Error consultando API: {e}")
        return []


def monitor_ted() -> dict:
    """Ejecuta busquedas en TED y devuelve resultados estructurados."""
    queries = [
        "IFEMA Madrid",
        "Madring circuito",
        "Formula 1 Madrid",
        "GP España circuito",
    ]

    all_results = []
    seen = set()

    OUTPUT_FILE.parent.mkdir(exist_ok=True)

    for q in queries:
        print(f"   [TED] Buscando: '{q}'...")
        results = search_ted(q)
        for r in results:
            pub_num = r.get("publication-number", "")
            if pub_num and pub_num not in seen:
                seen.add(pub_num)
                all_results.append(r)
        print(f"   [TED]   {len(results)} resultados, {len(seen)} unicos acumulados")

    # Guardar resultados
    output = {
        "fecha_consulta": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "total_encontrados": len(all_results),
        "resultados": all_results,
    }
    OUTPUT_FILE.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    # Generar resumen para el agente
    summary_parts = []
    for r in all_results[:10]:  # top 10
        title = r.get("title", "")[:120]
        buyer = r.get("buyer-name", "")
        amount = r.get("total-value", "")
        currency = r.get("currency", "")
        pub_date = r.get("publication-date", "")
        notice_type = r.get("notice-type", "")
        amount_str = f"{amount} {currency}" if amount else "No publicado"
        summary_parts.append(
            f"- TED {pub_date} | {notice_type} | {buyer} | {amount_str}\n  {title}"
        )

    summary = "\n".join(summary_parts) if summary_parts else "SIN RESULTADOS en TED Europa"
    print(f"   [TED] Total unicos: {len(all_results)} | Resumen: {len(summary_parts)} items")

    return {
        "total": len(all_results),
        "summary": summary,
        "file": str(OUTPUT_FILE),
    }


if __name__ == "__main__":
    print("🔍 Monitor TED Europa — Buscando licitaciones F1 Madrid...")
    result = monitor_ted()
    print(f"\n📋 Resultados: {result['total']} encontrados")
    print(result["summary"][:2000])
