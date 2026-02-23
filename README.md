# Extremo Ambiente — Event Automation Dashboard

An AI-powered corporate event quoting system for [Extremo Ambiente](https://extremoambiente.pt), a Portugal-based adventure tourism company. The dashboard transforms a manual quoting process into an intelligent workflow: client emails go in, structured itineraries and branded proposals come out.

---

## Table of Contents

- [Features Overview](#features-overview)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Environment Variables](#environment-variables)
- [Running the Application](#running-the-application)
- [How to Use the Dashboard](#how-to-use-the-dashboard)
  - [Tab 1 — Email Parser](#tab-1--email-parser)
  - [Tab 2 — Planner](#tab-2--planner)
  - [Tab 3 — Pricing](#tab-3--pricing)
  - [Tab 4 — Finalize](#tab-4--finalize)
- [AI Features](#ai-features)
- [Google Maps Integration](#google-maps-integration)
- [Proposal System](#proposal-system)
- [Activity Catalog](#activity-catalog)
- [Business Rules](#business-rules)
- [Project Structure](#project-structure)
- [Troubleshooting](#troubleshooting)

---

## Features Overview

- **AI Email Parsing** — Paste a client email and GPT-4o extracts structured event data (client name, group size, date, location, budget, preferences, special requests). Falls back to keyword matching when no API key is set.
- **Multi-Proposal System** — Create multiple proposal versions (A, B, C...) per client event, each with independent itinerary, activities, pricing, and start time.
- **Itinerary Editor** — Drag-and-drop AgGrid table for route stops with automatic time recalculation, configurable event start time (15-minute increments), Google Places location search, and per-stop travel duration estimation.
- **Activities & Billing** — Separate billing table with catalog-based transport options (Jeeps, Walking, RZR) featuring auto-calculated pricing, plus manual custom activities.
- **Interactive Route Map** — Folium map with color-coded markers by activity type, real road route polylines via Google Routes API, and automatic re-rendering on itinerary changes.
- **AI Chat Assistant** — Context-aware chatbot that sees the full itinerary, budget, and client preferences. Powered by GPT-4o with keyword fallback.
- **Pricing Panel** — Full cost breakdown with manual price overrides per activity, automatic group discounts, and per-person calculations.
- **Metrics Bar** — Live KPI strip showing client name, date, group size, location, per-person cost, total cost, and budget status.

---

## Prerequisites

- **Python >= 3.14**
- **[uv](https://docs.astral.sh/uv/)** package manager (do not use pip directly)

### Installing uv

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

---

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd ExtremoAmbiente-A1

# Install all dependencies from the lockfile
uv sync
```

This creates a virtual environment in `.venv/` and installs all packages defined in `pyproject.toml`.

---

## Environment Variables

Copy the example file and fill in your API keys:

```bash
cp .env.example .env
```

Edit `.env` with your keys:

```
OPENAI_API_KEY=sk-your-key-here
GOOGLE_MAPS_API_KEY=your-google-maps-api-key-here
```

| Variable | Required | What It Enables |
|---|---|---|
| `OPENAI_API_KEY` | No | **AI Email Parsing**: GPT-4o extracts structured data from client emails. **AI Chat Assistant**: context-aware responses based on the current itinerary and budget. Without it, both features fall back to keyword-based matching. |
| `GOOGLE_MAPS_API_KEY` | No | **Places Autocomplete**: search and assign Google Maps locations to itinerary stops. **Geocoding**: plot custom locations on the map. **Route Polylines**: draw real road routes between stops (via Routes API). **Travel Duration**: estimate travel time between consecutive stops (via Routes API). Without it, the map uses only catalog coordinates and travel times default to 15 minutes. |

### Google Maps API — Required APIs

If you use a Google Maps API key, make sure the following APIs are enabled in your Google Cloud Console project:

1. **Places API (New)** — for autocomplete search and text search geocoding
2. **Routes API** — for travel duration estimation and route polylines
3. **Maps JavaScript API** — for Google Maps tile rendering on the map (optional; falls back to OpenStreetMap)

---

## Running the Application

```bash
uv run streamlit run app.py
```

The dashboard opens at **http://localhost:8501**.

### Sidebar Status Indicators

When the app loads, the sidebar shows the status of external integrations:

- **AI Status**: "GPT-4o Active" (green) when `OPENAI_API_KEY` is set, "Fallback Mode" (amber) otherwise
- **Maps**: "Google Maps Active" (green) when `GOOGLE_MAPS_API_KEY` is set, "Catalog-only Mode" (amber) otherwise

---

## How to Use the Dashboard

The dashboard has four tabs that represent the workflow stages: **Email Parser**, **Planner**, **Pricing**, and **Finalize**. You must start with the Email Parser to load a client before the other tabs become available.

### Tab 1 — Email Parser

This is the entry point. It uses GPT-4o (or keyword fallback) to extract structured event data from a client email.

**Steps:**

1. **Paste a client email** into the text area on the left. The email should contain event details like company name, group size, date, location, budget, and preferences.
2. Click **"Load Sample Email"** to try a pre-loaded example email (InnovaTech Solutions, 20 people, Porto, April 15 2026).
3. Click **"Parse with AI"** to extract the data. GPT-4o analyzes the email and populates the form fields on the right.
4. **Review and edit** the extracted data in the form fields:
   - **Client Name** — company or person name
   - **Email** — client email address
   - **Group Size** — number of attendees
   - **Date** — event date in dd/mm/yyyy format
   - **Location** — primary location (e.g., Porto, Sintra, Algarve)
   - **Duration (hours)** — total event duration
   - **Budget per Person** — set to 0 for no budget cap
   - **Preferences** — comma-separated: adventure, cultural, food
   - **Special Requests** — free text for accessibility needs, dietary requirements, etc.
5. Click **"Start Planning"** to create a session and move to the Planner tab.

**Without an API key**: The parser uses keyword matching to extract basic information (group size, location, preferences) from the email text.

---

### Tab 2 — Planner

The main workspace for building the event itinerary and selecting activities. This tab has several sections from top to bottom:

#### Proposal Selector

At the top, a dropdown lets you switch between proposals (A, B, C...). Next to it:
- A text field to **rename** the current proposal (e.g., "Adventure Mix", "Cultural Focus")
- A **"+ New Proposal"** button to create additional proposal versions

Each proposal is fully independent with its own itinerary, activities, pricing, tour type, and start time.

#### Itinerary Editor (Route Stops)

The itinerary is a table of route stops (waypoints) that appear on the map. These are the physical locations the group will visit.

**Event Start Time**: Above the table, a time picker sets when the event begins (default: 09:30, adjustable in 15-minute increments). Changing this automatically recalculates all activity times in the itinerary. Each proposal can have a different start time.

**Table columns:**
| Column | Editable | Description |
|---|---|---|
| # | No | Row number, drag handle for reordering |
| Time | No | Auto-calculated start time for this stop |
| Activity | Yes | Name of the activity/stop |
| Google Maps Location | No | Set via the location editor below the table |
| Duration (min) | Yes | How long the group spends at this stop |
| Travel (min) | No | Travel time to the next stop (auto-calculated or 15 min default) |
| Notes | Yes | Free-text notes |
| X | Yes | Check to delete the row |

**How to use:**

1. Click **"+ Add Stop"** to add a new route stop. Enter a name and optionally search for a Google Maps location.
2. **Drag rows** up/down to reorder stops. Times recalculate automatically.
3. **Edit cells** by clicking on Activity, Duration, or Notes.
4. **Delete a stop** by checking the X checkbox on that row.
5. **Update a location** using the "Update Location" section below the table: select an activity from the dropdown, search for a Google Maps place, and click "Set".
6. Click **"Recalculate Times"** to force a recalculation of all start times and travel durations.

**Time calculation logic**: The first activity starts at the configured event start time. Each subsequent activity starts after the previous activity's duration plus the travel time to the next stop. Travel times use the Google Routes API when locations have coordinates; otherwise, a 15-minute default is used.

#### Activities & Billing

Below the itinerary, the Activities & Billing section manages billable services — these are separate from route stops.

**Catalog selector**: Three buttons at the top let you add pre-configured transport options:
- **Jeeps** — EUR 400 per jeep per 4-hour block, 6 people per jeep
- **Walking** — EUR 10 per person per hour
- **RZR** — EUR 200 per car per 2-hour block, 2 people per car

Catalog items have **auto-calculated pricing** (greyed out, locked). The system automatically computes the number of vehicles/blocks needed based on group size and event duration.

**Custom activities**: Click **"+ Add Activity"** to add manual items (e.g., Photography, Wine Tasting). Set a unit price and the quantity is automatically set to the group size. The total is calculated as unit price times quantity.

**Table columns:**
| Column | Editable | Description |
|---|---|---|
| # | No | Row number |
| Activity | Yes | Activity name |
| Type | Yes | Dropdown: adventure, cultural, food, transport, service |
| Unit Price | Yes* | Price per unit (*locked for catalog items) |
| Qty | No | Quantity (auto-set: group size for manual, calculated for catalog) |
| Total | No | Auto-calculated: unit price x quantity |
| Notes | Yes | Auto-generated for catalog items, free-text for manual |
| X | Yes | Check to delete |

Selecting a catalog transport option also sets the **tour type** for the proposal (walking vs. jeeps), which affects how travel times are calculated on the map (walking mode vs. driving mode).

#### Route Map

Displays all itinerary stops on an interactive Folium map:
- **Color-coded markers**: red = adventure, blue = cultural, orange = food, gray = transport
- **Route polylines**: real road routes drawn between consecutive stops (requires Google Routes API)
- **Auto-updates**: the map re-renders whenever the itinerary changes
- **Map tiles**: Google Maps tiles when API key is set, OpenStreetMap otherwise

#### AI Chat Assistant

A context-aware chatbot at the bottom-right of the Planner tab. The AI sees:
- Client information (name, group size, location, budget)
- Current itinerary (times, activities, types)
- Current activities and their costs
- Tour type and budget status

Ask it questions like:
- "Add a lunch break at 13:00"
- "What wine tasting options are near our route?"
- "Are we within budget?"
- "Suggest an alternative for the afternoon"

**Without an API key**: The chat uses keyword matching for common topics (lunch, wine, transport, photo, budget, route, etc.).

---

### Tab 3 — Pricing

A read-only cost breakdown for the active proposal. Shows:

- Each activity with its **calculated price** and **your price** (with optional manual override)
- **Override checkbox**: tick it to enter a custom price for any activity
- **Subtotal**: sum of all activity costs
- **Group Discount**: 5% automatically applied when group size > 10 people
- **Total**: final cost after discount
- **Per Person**: total divided by group size

Manual price overrides persist per proposal and are reflected in the metrics bar and finalize tab.

---

### Tab 4 — Finalize

A summary card showing:
- Client name, event date, group size, location
- Final cost and per-person cost

Click **"Generate PDF Proposal"** to create a branded PDF (placeholder in the prototype — the production version uses ReportLab via AWS Lambda).

---

## AI Features

### Email Parser (GPT-4o)

- **Model**: GPT-4o with temperature 0.1 for deterministic extraction
- **System prompt**: instructs the model to return valid JSON with specific fields
- **Fallback**: keyword-based matching extracts group size, location, and preferences from the email text
- **Normalization**: missing fields get sensible defaults (location: Porto, duration: 6h, budget: null)

### Chat Assistant (GPT-4o)

- **Model**: GPT-4o with temperature 0.7 for more creative responses
- **Context injection**: the system prompt includes a JSON dump of the current event context (client, itinerary, activities, budget)
- **Max tokens**: 200 per response to keep answers concise
- **Fallback**: keyword-to-response map covering common topics (lunch, wine, transport, budget, etc.)

---

## Google Maps Integration

The app uses three Google APIs (all via the same API key):

| Feature | API Used | Fallback Without Key |
|---|---|---|
| Location search in itinerary editor | Places API (New) — autocomplete + searchText | Search disabled |
| Travel time between stops | Routes API — computeRoutes | 15-minute default |
| Route drawing on map | Routes API — computeRoutes (polyline) | Dashed straight lines |
| Map tiles | Google Maps tile URL | OpenStreetMap tiles |
| Coordinate resolution | Places API — searchText | No coordinates, marker not shown |

All API responses are cached for 1 hour via `@st.cache_data(ttl=3600)`.

---

## Proposal System

Each event session can have multiple proposal versions:

- **Independent data**: each proposal has its own itinerary (route stops), activities (billing items), price overrides, tour type, and start time
- **Create**: click "+ New Proposal" on the Planner tab; proposals are labelled A, B, C, etc.
- **Rename**: edit the proposal name inline (e.g., "Adventure Mix", "Cultural Focus")
- **Switch**: use the dropdown to switch between proposals; all tabs reflect the active proposal
- **Pricing tab**: shows a read-only indicator of which proposal is active
- **Finalize tab**: shows the summary for the active proposal

---

## Activity Catalog

Three built-in transport activity types with auto-calculated pricing:

| Name | Pricing | Capacity | Time Block |
|---|---|---|---|
| Jeeps | EUR 400 per jeep | 6 people per jeep | 4-hour block |
| Walking | EUR 10 per person per hour | N/A | 1-hour block |
| RZR | EUR 200 per car | 2 people per car | 2-hour block |

**Auto-calculation example** (Jeeps, 20 people, 8 hours):
- Vehicles needed: ceil(20 / 6) = 4 jeeps
- Time blocks: ceil(8 / 4) = 2 blocks
- Quantity: 4 jeeps x 2 blocks = 8
- Total: 8 x EUR 400 = EUR 3,200

Custom activities added via "+ Add Activity" have editable unit prices and quantity locked to the group size.

---

## Business Rules

| Rule | Detail |
|---|---|
| Group discount | Groups > 10 people receive 5% off the total automatically |
| Budget tracking | Per-person cost compared against the client's budget (if provided); over-budget shows a warning banner |
| Tour type | Selecting Jeeps or RZR sets driving mode; Walking sets walking mode — affects travel time calculations |
| Travel time default | 15 minutes between stops when Google Routes API is unavailable |
| Event start time | Configurable per proposal in 15-minute increments, default 09:30 |
| Date format | Stored as YYYY-MM-DD internally, displayed as dd/mm/yyyy in the UI |

---

## Project Structure

```
ExtremoAmbiente-A1/
├── app.py                          # Streamlit entry point — routing, layout, tabs
├── style.css                       # Global CSS design system (brand palette)
├── pyproject.toml                  # uv dependency definitions
├── uv.lock                         # uv lockfile (committed)
├── .env.example                    # Template for environment variables
├── CLAUDE.md                       # Development instructions
├── README.md                       # This file
│
├── assets/
│   ├── logo.png                    # Header logo
│   ├── logo_sidebar.png            # Sidebar logo
│   └── favicon.png                 # Browser tab icon
│
├── components/                     # Reusable Streamlit UI components
│   ├── header.py                   # Top header band with logo + session badge
│   ├── metrics_bar.py              # KPI metrics strip (client, cost, budget)
│   ├── proposal_selector.py        # A/B/C proposal dropdown + rename + create
│   ├── itinerary_editor.py         # AgGrid drag-drop route table + start time picker
│   ├── activities_editor.py        # AgGrid billing table + catalog selector
│   ├── map_view.py                 # Folium route map with markers + polylines
│   ├── chat_panel.py               # AI assistant chat bubbles + input
│   └── pricing_panel.py            # Cost breakdown with manual overrides
│
├── ai/
│   ├── email_parser.py             # GPT-4o email extraction + keyword fallback
│   └── chat_agent.py               # Context-aware chatbot + keyword fallback
│
├── data/
│   ├── engine.py                   # Pricing calculations, time rebuilding, cost aggregation
│   └── catalog.py                  # Activity catalog, demo clients, add-ons, pickup locations
│
└── services/
    └── geocoding.py                # Google Maps geocoding, Places, Routes API integration
```

---

## Troubleshooting

| Issue | Solution |
|---|---|
| `ModuleNotFoundError` on import | Run `uv sync` to install all dependencies |
| "Parse with AI" does nothing | Set `OPENAI_API_KEY` in `.env`; without it the fallback parser runs (less accurate) |
| Map shows no markers | Assign Google Maps locations to itinerary stops via the location editor; locations without coordinates are skipped |
| Map shows dashed lines instead of roads | Enable the **Routes API** in your Google Cloud project |
| Map shows OpenStreetMap instead of Google Maps | Enable the **Maps JavaScript API** and check `GOOGLE_MAPS_API_KEY` is set |
| Location search returns no results | Enable the **Places API (New)** in your Google Cloud project; ensure the API key has no IP restrictions blocking localhost |
| Travel times all show 15 min | Enable the **Routes API** and assign coordinates to at least two consecutive stops |
| "Fallback Mode" in sidebar | `OPENAI_API_KEY` is not set; AI features use keyword matching instead of GPT-4o |
| "Catalog-only Mode" in sidebar | `GOOGLE_MAPS_API_KEY` is not set; map and location features are limited |
| Planner/Pricing/Finalize tabs show "No Active Session" | Parse an email and click "Start Planning" in the Email Parser tab first |
| AgGrid not rendering | Ensure `streamlit-aggrid>=1.2.1` is installed; run `uv sync` |
| Port 8501 already in use | Stop the other Streamlit instance or run with `uv run streamlit run app.py --server.port 8502` |
