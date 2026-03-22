# CRM Signals

Local web app: paste a company website URL, extract **signals** (name, description, contacts, social links, coverage score), preview them, then append a row to a **Notion** database.

**Requirements**

- **Python 3.10+** (3.11 or 3.12 recommended). Check with `python3 --version`. If your default is older (for example pyenv only has 3.6), install a current Python via [pyenv](https://github.com/pyenv/pyenv) or [Homebrew](https://brew.sh) (`brew install python@3.12`) and use that binary for the venv.
- **Node.js 18+** for the React dev server and production build (`node --version`).

## 1. Clone / open the project

```bash
cd /path/to/CRM
```

## 2. Backend (FastAPI)

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -U pip
pip install -r requirements.txt
```

Copy environment template and fill in what you need:

```bash
cp .env.example .env
```

- **Preview-only** (no Notion): leave `NOTION_*` empty. You can still use **Run preview**.
- **Notion push**: create an [internal integration](https://www.notion.so/my-integrations), copy the secret into `NOTION_TOKEN`, create a database, copy its ID from the URL into `NOTION_DATABASE_ID`, and **connect** the integration to that database (database → `⋯` → **Connections**).

### Notion database columns

Create a database with these properties (names must match unless you override with `NOTION_PROP_*` in `.env`):

| Property name   | Type        |
|----------------|-------------|
| Name           | Title       |
| Source URL     | URL         |
| Description    | Text        |
| Industry       | Text        |
| Location       | Text        |
| Emails         | Text        |
| Phones         | Text        |
| Social         | Text        |
| Funding / size | Text        |
| Coverage       | Number      |
| Scraped at     | Date        |
| Method         | Text        |

Optional: set `OPENAI_API_KEY` in `.env` and use **Use LLM** (or low coverage) for hybrid extraction.

## 3. Frontend (React + Vite)

```bash
cd frontend
npm install
```

## 4. Run locally (two terminals)

**Terminal A — API**

From the project root (with `.venv` activated):

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**Terminal B — UI (development)**

```bash
cd frontend
npm run dev
```

Open **http://localhost:5173** in your browser. Vite proxies `/api` to `http://127.0.0.1:8000`, so the React app can call the backend without CORS issues.

- Try **Run preview** on a public marketing site (respect robots.txt; some URLs may be blocked).
- After Notion is configured, use **Send to Notion** to create a row.

API docs (optional): **http://127.0.0.1:8000/docs**

## 5. Tests

```bash
pytest -q
```

## 6. Production-like run (single server)

Build the frontend, then serve API + static files from FastAPI:

```bash
cd frontend && npm run build && cd ..
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open **http://127.0.0.1:8000** — the built SPA is served from `frontend/dist` when that folder exists.

## Makefile shortcuts

```bash
make install    # backend venv + pip + frontend npm install
make test       # pytest
make dev-api    # uvicorn from .venv
make dev-ui     # Vite dev server
```

Ensure `.venv` was created with Python 3.10+ before `make install`.

## Export `plan.md` to Google Docs

There is no real “`.gdoc` file” on disk—Google Docs live in Drive. The usual workflow is to make a **Word document** and open it with Google Docs.

1. Install [Pandoc](https://pandoc.org/) for best results (`brew install pandoc` on macOS). Optional fallback: `pip install python-docx` if Pandoc is missing.
2. From the repo root:

   ```bash
   python3 scripts/export_plan_docx.py
   ```

   This reads [`plan.md`](plan.md) and writes **`CRM_Plan.docx`** in the project root.

3. In [Google Drive](https://drive.google.com): **New → File upload** → choose `CRM_Plan.docx`, then **right‑click the file → Open with → Google Docs**. Drive converts it into an editable Google Doc you can rename or move.

To use a different source or output path:

```bash
python3 scripts/export_plan_docx.py /path/to/plan.md /path/to/out.docx
```
