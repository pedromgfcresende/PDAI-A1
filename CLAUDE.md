# Extremo Ambiente — Event Automation System

## Project Overview
Automated corporate event quoting system for Extremo Ambiente, a Portugal-based adventure tourism company.
Transforms a 2-hour manual quoting process into a 10-minute intelligent workflow.

**Goal**: Client emails in → structured itinerary + branded PDF proposal out, with human review at key steps.

## Current State
The project started as a single-file Streamlit prototype (`app.py`). We are actively refactoring into
a proper multi-module structure. Key UX concepts from the prototype to preserve:
- Multi-proposal system (A/B/C versions per client event)
- Sub-group splitting (assign activities to "All", "Group A", "Group B", etc.)
- Phase progress bar (Email Parsed → Planning → Review → Finalized)
- Session badge per event (e.g. `evt-89234`)

---

## Target Tech Stack
- **Orchestration**: n8n (open-source, self-hosted on AWS EC2)
- **LLM / Parsing**: OpenAI GPT-4o via LangChain
- **Frontend Dashboard**: Streamlit (Python) with AgGrid for drag-drop itinerary editing
- **Route Optimization**: Google OR-Tools (TSP solver, <200ms for 10 stops)
- **Maps**: Google Maps Platform (not Folium/OSM — use Google Maps embed + Distance Matrix API)
- **PDF Generation**: ReportLab (Python) via AWS Lambda
- **Email Integration**: Microsoft Graph API (Outlook drafts — never auto-send)
- **Database**: AWS RDS PostgreSQL (not st.session_state — that's prototype only)
- **Infrastructure**: Docker on AWS EC2 (t3.medium), AWS Lambda, AWS S3
- **Auth**: Azure AD / OIDC for staff login
- **Styling**: Custom CSS design system (see Design System section below)

---

## Target Project Structure
```
extremo_ambiente/
├── app.py                      ← Streamlit entry point (thin — just imports & routing)
├── style.css                   ← Global CSS design system (do not break)
├── pyproject.toml              ← uv dependencies (source of truth — not requirements.txt)
├── uv.lock                     ← Lockfile (commit this)
├── CLAUDE.md
├── .env                        ← Never commit (use .env.example)
├── .env.example
│
├── assets/
│   ├── logo.png
│   ├── logo_sidebar.png
│   └── favicon.png
│
├── components/                 ← Reusable Streamlit UI components
│   ├── header.py               ← EA header band + session badge
│   ├── metrics_bar.py          ← Client metrics row (group size, cost, budget status)
│   ├── phase_bar.py            ← Phase progress indicator
│   ├── itinerary_editor.py     ← AgGrid drag-drop table
│   ├── map_view.py             ← Google Maps embed
│   ├── chat_panel.py           ← AI assistant chat bubbles
│   ├── pricing_panel.py        ← Cost breakdown + manual overrides
│   └── proposal_selector.py    ← A/B/C proposal tabs + new proposal button
│
├── agents/
│   ├── email_parser.py         ← GPT-4o extraction via LangChain
│   └── chat_agent.py           ← Context-aware chatbot (sees itinerary + budget)
│
├── optimization/
│   └── route_solver.py         ← OR-Tools TSP solver (isolated — do not inline)
│
├── pricing/
│   ├── engine.py               ← Cost calculations, group discounts, add-ons
│   └── catalog.py              ← Activity catalog (reads from RDS, not hardcoded)
│
├── db/
│   ├── schema.sql              ← PostgreSQL schema
│   ├── models.py               ← SQLAlchemy ORM models
│   └── session.py              ← DB connection + session management
│
├── lambda/
│   ├── pdf_generator/          ← ReportLab PDF Lambda function
│   │   └── handler.py
│   └── email_draft/            ← Microsoft Graph email drafting
│       └── handler.py
│
├── n8n/
│   └── workflows/              ← n8n workflow exports (JSON) — edit via n8n UI only
│
└── docker-compose.yml          ← n8n + PostgreSQL stack
```

---

## Package Manager — uv
This project uses [uv](https://docs.astral.sh/uv/) for dependency management. Do not use pip directly.

```bash
# Install uv (once, on a new machine)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install all dependencies from lockfile
uv sync

# Add a new runtime dependency
uv add some-package

# Add a dev-only dependency
uv add --dev some-package

# Run any command inside the managed venv
uv run streamlit run app.py
uv run pytest
```

**What to commit:** `pyproject.toml` and `uv.lock`
**What to gitignore:** `.venv/`
**Do not use:** `pip install`, `requirements.txt` (kept only as fallback for Lambda build steps)

---

## How to Run Locally

```bash
# Start n8n + PostgreSQL
docker-compose up -d

# Install dependencies and run dashboard
uv sync
uv run streamlit run app.py

# Dashboard at http://localhost:8501
# n8n at http://localhost:5678
```

---

## Environment Variables
```
OPENAI_API_KEY=
GOOGLE_MAPS_API_KEY=
GOOGLE_PLACES_API_KEY=
AZURE_TENANT_ID=
AZURE_CLIENT_ID=
AZURE_CLIENT_SECRET=
AWS_S3_BUCKET=
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
DATABASE_URL=postgresql://user:pass@rds-host:5432/extremo
N8N_HOST=events.extremoambiente.pt
```

---

## Three-Agent Workflow

### Agent 1 — Email Parser (n8n)
- Monitors `events@extremoambiente.pt` via IMAP
- Sends email body to GPT-4o for structured JSON extraction
- Extracted fields: `client_name`, `email`, `group_size`, `date`, `locations`,
  `duration_hours`, `preferences`, `budget_per_person`, `special_requests`
- POSTs JSON to AWS Lambda to create a new session in RDS
- On failure: flags email for manual review; retries 3x before alerting staff
- Raw email body deleted from memory after parsing (GDPR)

### Agent 2 — Planning Dashboard (Streamlit)
- Receives session JSON, generates unique session URL per event
  (e.g. `events.extremoambiente.pt/session/evt-12345`)
- Auto-queries Google Places for local activities and restaurants
- OR-Tools optimizes initial route (TSP)
- Staff uses AgGrid drag-drop table to reorder activities
- Staff can create multiple proposal versions (A/B/C) for same client
- Sub-group splitting: activities can be assigned to "All", "Group A", "Group B", etc.
- Chatbot (LangChain + GPT-4o) is context-aware: sees full itinerary, budget, preferences
- All session state persisted to RDS PostgreSQL (not st.session_state)
- Sessions expire after 24h

### Agent 3 — PDF + Email Draft (AWS Lambda)
- Triggered when staff clicks [Finalize] in dashboard
- ReportLab renders branded PDF: itinerary table, pricing summary,
  embedded Google Map, QR code, next steps
- PDF saved to S3 (30-day retention)
- Microsoft Graph API creates Outlook draft with PDF attached
- Staff reviews draft in Outlook and sends manually — NEVER auto-sent

---

## Key Features to Preserve from Prototype

### Multi-Proposal System
Each event session can have multiple proposal versions (A, B, C...).
- Staff can create a new proposal version with one click
- Each proposal has its own itinerary, pricing, and sub-group config
- Proposals are compared side-by-side in the Finalize tab before sending

### Sub-Group Splitting
Activities can be assigned to sub-groups within the same event.
- Useful when large groups split for parallel activities
- Each activity has a `subgroup` field: "All", "Group A", "Group B", "Group C"
- Pricing engine handles sub-group cost splits automatically

### AgGrid Itinerary Editor
Use `streamlit-aggrid` for the itinerary table — NOT `st.data_editor`.
- Drag-drop row reordering is required
- Inline cell editing for activity name, duration, notes, subgroup
- On row reorder: trigger OR-Tools reoptimization automatically
- Column config: Time (read-only), Activity, Type (dropdown), Duration (min),
  Cost (read-only, calculated), Sub-group (dropdown), Notes

### Google Maps Integration
Use Google Maps embed (not Folium/OSM).
- Display route as polyline
- Color-coded markers: adventure=red, cultural=blue, food=green, transport=gray
- On itinerary change: re-render map with updated stop order
- Distance Matrix API used by OR-Tools for travel times between stops

---

## Design System (style.css)
The CSS design system is based on extremoambiente.pt's brand palette.
**Do not change CSS variable names or remove existing classes.**

### Color Palette
```css
--orange:       #E86825   /* Primary CTA, accents */
--orange-light: #F07A3A
--orange-pale:  #FFB088
--orange-dark:  #C04E10
--charcoal:     #2C2C2C   /* Nav/header background */
--deep:         #1A1A1A   /* Page depth, map bg */
--surface:      #242424   /* Main page background */
--card:         #2E2E2E   /* Card surfaces */
--raised:       #363636   /* Elevated elements */
--border:       #3D3D3D
--muted:        #888888   /* Secondary text */
--text:         #F0F0F0
--white:        #FFFFFF
```

### Typography
- Display/headings: `Montserrat` (bold, uppercase, letter-spaced)
- Body: `Open Sans`
- Prices/times/codes: `JetBrains Mono`

### Key CSS Classes (do not rename)
- `.ea-header` — top header band with logo
- `.ea-logo` / `.ea-tagline` — brand name + subtitle
- `.ea-session-badge` — session ID badge (top right)
- `.ea-card` — standard card container
- `.metric-row` / `.metric-badge` — KPI metrics strip
- `.section-title` — orange left-border section headers
- `.phase-bar` / `.phase-seg` — workflow phase progress bar
- `.itin-table` — itinerary table styles
- `.type-pill` + `.type-adventure/cultural/food/transport` — activity type badges
- `.chat-window` / `.bubble-bot` / `.bubble-user` — chat panel
- `.price-row` / `.price-val` — pricing breakdown rows
- `.warn-box` / `.info-box` — alert banners
- `.map-placeholder` — shown when map fails to load

---

## Coding Conventions
- Python 3.11+, snake_case everywhere
- All Streamlit components in `/components/` — one function per component
- Never inline OR-Tools logic outside `optimization/route_solver.py`
- All API keys from environment variables — never hardcoded
- Database queries via SQLAlchemy ORM only (no raw SQL except in `db/schema.sql`)
- CloudWatch structured logging in all Lambda functions
- Type hints on all function signatures

---

## Business Rules
- Quotes must complete end-to-end in under 10 minutes
- OR-Tools must solve in <200ms for up to 10 stops
- Lunch window constraint: 12:00–14:00 (enforced in OR-Tools time windows)
- Group discount: >10 people → 5% off total automatically
- Photography surcharge: +€200 flat
- Sessions expire after 24h of inactivity
- PDFs are NEVER auto-sent — always require staff review in Outlook
- Raw email bodies deleted after parsing (GDPR)
- Client PII encrypted at rest in RDS (AWS KMS)

---

## Database Schema (Key Tables)
```sql
-- Events / sessions
CREATE TABLE events (
  id VARCHAR PRIMARY KEY,         -- evt-XXXXX
  client_name VARCHAR,
  email VARCHAR,
  group_size INT,
  date DATE,
  location VARCHAR,
  duration_hours INT,
  preferences JSONB,
  budget_per_person FLOAT,
  special_requests TEXT,
  phase VARCHAR,                  -- 'parsed', 'planning', 'review', 'finalized'
  created_at TIMESTAMP,
  expires_at TIMESTAMP
);

-- Proposals (multiple per event)
CREATE TABLE proposals (
  id SERIAL PRIMARY KEY,
  event_id VARCHAR REFERENCES events(id),
  label VARCHAR,                  -- 'A', 'B', 'C'
  name VARCHAR,                   -- 'Adventure Mix', 'Cultural Focus', etc.
  itinerary JSONB,
  subgroups JSONB,
  total_cost FLOAT,
  created_at TIMESTAMP
);

-- Activity catalog
CREATE TABLE activities (
  id SERIAL PRIMARY KEY,
  name VARCHAR,
  type VARCHAR,                   -- 'adventure', 'cultural', 'food', 'transport'
  location VARCHAR,
  lat FLOAT, lng FLOAT,
  duration_minutes INT,
  base_price FLOAT,
  price_per_person BOOLEAN,
  provider VARCHAR,               -- 'extremo_ambiente', 'google_places', 'custom'
  tags JSONB
);
```

---

## Do Not Touch
- `n8n/workflows/` — edit only via n8n UI, then export JSON
- `.env` — never commit (`.env.example` only)
- CSS variable names in `style.css`
- AWS IAM roles — do not modify without approval
- `db/schema.sql` — propose changes in a PR, don't edit directly

---

## Testing
```bash
uv run pytest tests/

# Email parsing accuracy (requires fixtures in tests/fixtures/)
uv run pytest tests/test_parser.py

# OR-Tools solver performance (<200ms target)
uv run pytest tests/test_optimizer.py

# Pricing engine
uv run pytest tests/test_pricing.py
```

- Target: 95%+ extraction accuracy on test email fixtures
- OR-Tools: must solve 10-stop scenarios in <200ms

---

## Git Workflow
- `main` = production (never push directly)
- `dev` = staging
- `feature/*` = new features
- Always open a PR into `dev`, then promote to `main`
- Commit messages: `feat:`, `fix:`, `refactor:`, `chore:` prefixes

---

## Deployment
- All services run in Docker on AWS EC2 (Ubuntu 22.04)
- Streamlit runs as a systemd service (auto-restarts on crash)
- Lambda functions deployed via AWS CLI or Terraform
- Production URL: https://events.extremoambiente.pt
- SSL via Let's Encrypt
