"""
Monitor TED Europa — busca licitaciones F1 Madrid/IFEMA/Madring.
Simplemente genera las URLs de busqueda para consulta manual o web search.
"""
from datetime import datetime

TED_SEARCH_URL = "https://ted.europa.eu/en/notice/-/search"

QUERIES = [
    ("IFEMA Madrid", "resultNoticeType=ALL&query=IFEMA+Madrid"),
    ("Madring", "resultNoticeType=ALL&query=Madring"),
    ("Formula 1 Madrid", "resultNoticeType=ALL&query=Formula+1+Madrid"),
    ("GP Espana circuito", "resultNoticeType=ALL&query=GP+Espana+circuito"),
]


def get_ted_urls() -> list:
    """Devuelve las URLs de busqueda en TED para consulta."""
    urls = []
    for name, params in QUERIES:
        urls.append(f"{TED_SEARCH_URL}?{params}")
    return urls


def get_ted_queries() -> list:
    """Devuelve las queries para usar con web_search."""
    return [
        "site:ted.europa.eu IFEMA Madrid licitacion",
        "site:ted.europa.eu Madring circuito formula 1",
        "site:ted.europa.eu Espana 'formula 1' circuito IFEMA contrato",
    ]


if __name__ == "__main__":
    print("🔍 Monitor TED Europa — URLs de consulta:\n")
    for name, params in QUERIES:
        print(f"  {name}: {TED_SEARCH_URL}?{params}")
    print(f"\n📋 Queries para web_search:")
    for q in get_ted_queries():
        print(f"  {q}")
    print(f"\n🕐 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
