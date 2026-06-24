# 🏎️ Operación Pit-Lane — Investigador de Costes Públicos F1 Madrid

Agente automatizado que investiga **cada día a las 21:00h** el coste real del
Gran Premio de Fórmula 1 de Madrid (Madring), consultando fuentes oficiales
con IA y publicando los resultados en GitHub Pages.

## 🔍 Qué hace

- Busca licitaciones, adjudicaciones y contratos en fuentes oficiales
- Verifica cada cifra con al menos dos fuentes independientes
- Mantiene un **histórico de contratos** con fechas, expedientes y enlaces
- Compara el caso Madrid con el **precedente de Valencia** (GP Europa 2008-2012)
- Estima el % de similitud de riesgo de que se repita el mismo escenario
- Publica todo en una web pública accesible

## 🌐 Web pública

👉 **[https://madpole360.github.io/operacion-pit-lane](https://madpole360.github.io/operacion-pit-lane)**

- `index.html` → Informe diario con costes, contratos, riesgos y fuentes
- `valencia.html` → Comparativa Madrid vs Valencia con medidor de riesgo

## ⚙️ Cómo funciona

```
GitHub Actions (cron 21:00 Madrid)
  └─ Python research_agent.py
       └─ Claude API (Sonnet 4.6) + web_search
            └─ Genera JSON + HTML
                 └─ git commit + push → GitHub Pages
```

## 🛠️ Setup para tu propio fork

### 1. Requisitos previos

- Una cuenta de GitHub
- Una API key de [Anthropic (Claude API)](https://console.anthropic.com/)

### 2. Configurar el repositorio

```bash
git clone https://github.com/madpole360/operacion-pit-lane.git
cd operacion-pit-lane
```

### 3. Añadir la API key como secret

1. Ve a **Settings → Secrets and variables → Actions**
2. Haz clic en **New repository secret**
3. Nombre: `ANTHROPIC_API_KEY`
4. Valor: tu clave de API de Anthropic (empieza por `sk-ant-...`)

### 4. Activar GitHub Pages

1. Ve a **Settings → Pages**
2. En **Source**, selecciona **Deploy from a branch**
3. Rama: `main`, carpeta: `/docs`
4. Haz clic en **Save**

### 5. Primera ejecución

1. Ve a **Actions → 🏎️ F1 Madrid — Investigación Diaria**
2. Haz clic en **Run workflow**
3. En 2-3 minutos tu sitio estará publicado

## 📁 Estructura del proyecto

```
.github/workflows/f1-research.yml   → Workflow diario (cron)
scripts/
  ├── research_agent.py             → Agente investigador (Claude API)
  └── generate_pages.py             → Generador HTML (Jinja2)
templates/
  ├── index.html.j2                 → Plantilla informe diario
  └── valencia.html.j2              → Plantilla comparativa Valencia
docs/                               → GitHub Pages (público)
  ├── index.html                    → Página principal
  ├── valencia.html                 → Comparativa Valencia
  ├── latest.json                   → Último informe (datos)
  ├── contracts.json                → Histórico completo de contratos
  └── archive/YYYY-MM-DD.json       → Archivo diario
data/timeline.json                  → Evolución temporal de costes
```

## ⏰ Horario

El agente se ejecuta cada día a las **21:00h hora Madrid**.

- Verano (CEST, UTC+2): cron `0 19 * * *`
- Invierno (CET, UTC+1): hay que cambiar el cron a `0 20 * * *`

## 💰 Coste estimado

| Concepto | Coste |
|----------|-------|
| GitHub Actions | 0 € (repositorio público) |
| GitHub Pages | 0 € (repositorio público) |
| Claude API (Sonnet 4.6) | ~0.08-0.15 €/día |
| **Total mensual** | **~3-5 €** |

## 📜 Licencia

MIT — Los datos son de fuentes públicas. El código es libre.
