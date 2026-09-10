"""
Incluye el canon/derechos F1 (~277 M€) en el contador principal — 2026-09-10
===========================================================================
El canon no está confirmado oficialmente (cláusulas de confidencialidad), pero
se incorpora como hipótesis en el contador y en el total estimado provisional.

Total = mínimo comprometido + servicios extraordinarios + canon F1.
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
EXEC_DATE = "2026-09-10"
EXEC_DATETIME = NOW.strftime("%Y-%m-%d %H:%M")


def load(p):
    return json.loads(p.read_text(encoding="utf-8"))


def save(p, data):
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    d = load(LATEST_FILE)
    comprometido = d.get("coste_comprometido", 0)
    servicios = (d.get("estimacion_servicios_extraordinarios") or {}).get("importe", 0) or 0
    canon = (d.get("canon_fom") or {}).get("total_10_anios", 0) or 0

    total = comprometido + servicios + canon

    d["coste_total_estimado_provisional"] = total
    d["coste_total_estimado_provisional_texto"] = (
        f"≈{total/1e6:.1f} M€ (compromisos + servicios extraordinarios + canon F1 estimado), "
        "antes de costes operativos recurrentes."
    )

    # Añadir mención del canon al resumen (sin reescribirlo entero)
    resumen = d.get("resumen_ejecutivo", "")
    frase = (
        " Incluyendo el canon/derechos F1 (~277 M€, hipótesis no confirmada) en el contador, la dimensión "
        f"económica conocida/estimada total asciende a ≈{total/1e6:.1f} M€ (compromisos + servicios "
        "extraordinarios + canon), antes de los costes operativos recurrentes de las diez ediciones."
    )
    if "Incluyendo el canon/derechos F1" not in resumen:
        d["resumen_ejecutivo"] = resumen.rstrip() + frase

    d["fecha_madrid"] = EXEC_DATETIME

    save(LATEST_FILE, d)
    daily = ARCHIVE_DIR / f"{EXEC_DATE}.json"
    if daily.exists():
        save(daily, d)

    from generate_pages import build_site
    build_site(d)

    print("=" * 60)
    print("Canon F1: %.0f M" % (canon / 1e6))
    print("Total estimado provisional: %.1f M" % (total / 1e6))


if __name__ == "__main__":
    main()
