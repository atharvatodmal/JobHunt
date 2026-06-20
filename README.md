# JobHunter

Minimalist job search app — searches **Talent.com**, **Dice**, **LinkedIn**, **Adzuna**, and **Jooble** simultaneously.

Crafted by **Atharva Todmal**

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://YOUR_USERNAME-jobhunter.streamlit.app)

## Quick Start

```bash
pip install -r requirements.txt
cp .env.example .env   # edit with your API keys
streamlit run app.py
```

## API Keys (Free)

| Source | Sign Up | Required |
|--------|---------|----------|
| **Adzuna** | [developer.adzuna.com](https://developer.adzuna.com) | Yes |
| **Jooble** | [jooble.org/api/about](https://jooble.org/api/about) | Optional |

Set them as environment variables or add to `.env`:
```
ADZUNA_APP_ID=your_id
ADZUNA_API_KEY=your_key
JOOBLE_API_KEY=your_key   # optional
```

On **Streamlit Cloud**, add them via Settings → Secrets → `[env]` section.

## Deploy on Streamlit Cloud (Free)

1. Push this repo to **GitHub**
2. Go to **[share.streamlit.io](https://share.streamlit.io)** and sign in with GitHub
3. Click **New app** → select your repo → branch `main` → file `app.py`
4. Click **Deploy**
5. Settings → Secrets → add API keys under `[env]`

No credit card needed.

## Sources

| Source | Type | Coverage |
|--------|------|----------|
| Talent.com | Scraper | Global |
| Dice | Scraper | US |
| LinkedIn | Scraper | Global |
| Adzuna | API | India + 20 countries |
| Jooble | API | India + 69 countries |

## Tech

- **Streamlit** — UI
- **cloudscraper + BeautifulSoup** — scraping (3 sources)
- **Adzuna + Jooble REST APIs** — stable data (2 sources)
- Input validation, XSS escaping, relevance filtering
- 5 dependencies, zero runtime fees
