# Agents

## Cursor Cloud specific instructions

### Architecture Overview

This is a **Trade Reconciliation MVP** with two services:

| Service | Directory | Port | Run Command |
|---------|-----------|------|-------------|
| Streamlit Frontend + Matching Engine | `/workspace` (root) | 8501 | `streamlit run app.py --server.port 8501 --server.headless true` |
| AI Resolution Agent Backend | `/workspace/agent-backend` | 3001 | `npx tsx server.ts` (from `agent-backend/`) |

### Running the services

- **Streamlit frontend** requires `streamlit`, `pandas`, `requests` Python packages (install via `pip install streamlit pandas requests`).
- **Agent backend** requires `npm install` in `agent-backend/`. After a fresh clone on a new architecture, run `npm rebuild sqlite3` to rebuild the native sqlite3 binding for the current platform.
- The agent backend requires the `CURSOR_API_KEY` environment variable to be set (available as a Cursor secret).

### Key gotchas

- There is no `requirements.txt` in the repo. Python deps are: `streamlit`, `pandas`, `requests`.
- The `node_modules/sqlite3` native binary may be compiled for a different architecture (e.g., darwin-arm64 vs linux-x64). If you see `ERR_DLOPEN_FAILED: invalid ELF header`, run `npm rebuild sqlite3` in `agent-backend/`.
- `pip install` puts scripts in `~/.local/bin` which may not be on PATH. Ensure `export PATH="$HOME/.local/bin:$PATH"` is set.
- The Streamlit app calls the agent backend at `http://localhost:3001/resolve-break`. If the backend is not running, the frontend still works but all breaks will show as "escalated" with connection errors.
- There is no formal lint or test suite configured. TypeScript can be checked with `npx tsc --noEmit` (from `agent-backend/`); Python code quality can be checked with standard tools like `ruff` or `flake8` if installed.

### Testing the app

Upload `/workspace/sample_pb_statement.csv` through the sidebar file uploader. The matching engine will identify 6 breaks (3 unmatched + 3 mismatched). The AI agent will process each break autonomously.
