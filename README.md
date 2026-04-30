# Hawkeye - Autonomous Reconciliation Engine

Hawkeye is an institutional trade reconciliation demo for macro hedge fund operations.
It ingests a Prime Broker statement CSV, reconciles against internal OMS trades, and uses a Cursor Agent backend to auto-stage or escalate trade breaks.

## Core Capabilities

- CSV ingestion pipeline via Streamlit sidebar uploader.
- Deterministic reconciliation between OMS and PB records.
- Autonomous break triage using a policy-driven AI agent.
- Checker workflow for approving staged breaks.
- Compliance audit log with timestamped approvals.

## Project Structure

- `app.py` - Streamlit front-end, ingestion, triage workflow, staged approval, audit log.
- `data_generator.py` - Sample OMS/PB trade generation and PB CSV export utility.
- `matching_engine.py` - Reconciliation logic returning matches, unmatched, and mismatches.
- `sample_pb_statement.csv` - Example PB statement for ingestion tests.
- `agent-backend/server.ts` - Express API that calls Cursor SDK (`/resolve-break`).

## Prerequisites

- Python 3.10+
- Node.js 18+
- A valid Cursor API key in `agent-backend/.env`:

```env
CURSOR_API_KEY=your_key_here
```

## Local Setup

### 1) Python app

```bash
cd "/Users/dimuthu.muththettuwage/Documents/trade-break-ai-python/hawkeye"
python3 -m venv .venv
source .venv/bin/activate
pip install streamlit pandas requests
```

### 2) Agent backend

```bash
cd "/Users/dimuthu.muththettuwage/Documents/trade-break-ai-python/hawkeye/agent-backend"
npm install
```

## Run

Start backend:

```bash
cd "/Users/dimuthu.muththettuwage/Documents/trade-break-ai-python/hawkeye/agent-backend"
npx tsx server.ts
```

Start Streamlit UI:

```bash
cd "/Users/dimuthu.muththettuwage/Documents/trade-break-ai-python/hawkeye"
streamlit run app.py
```

If you use `uv` and see `Failed to spawn: streamlit`, install Streamlit in the active environment first:

```bash
uv pip install streamlit
```

## Data Ingestion Flow

1. Upload `Prime Broker Statement (CSV)` in the sidebar.
2. App reads CSV with `pandas.read_csv`.
3. App generates internal OMS snapshot via `generate_trade_data()`.
4. App reconciles data using `reconcile_trades(oms_df, pb_df)`.
5. Autonomous agent kicks off automatically per upload (one run per unique file signature).

## Autonomous Decision Contract

Backend returns strict JSON:

- `status`: `staged_for_approval` or `escalated`
- `policy_cited`: exact policy identifier
- `audit_rationale`: professional rationale / math
- `drafted_email`: escalation email draft (for escalations)

## Checker + Compliance

- `Staged by AI (Pending Approval)` uses editable table controls.
- Checker can adjust `Resolution Action` and `Policy Cited`.
- `Checker: Approve & Commit Batch` moves items into immutable-style audit entries.
- `Compliance Audit Log` shows:
  - Timestamp
  - Ticker
  - Resolution Action
  - Policy Cited
  - Approved By
