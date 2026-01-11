# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Python Learning Support Application - an AI-powered adaptive learning tool that helps users understand Python programming concepts through interactive explanations, practice problems, and progress tracking.

**Stack:** FastAPI backend, Vanilla JavaScript frontend, SQLite database, Anthropic Claude API, Monaco Editor, Chart.js for analytics.

## Commands

### Setup & Run
```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt

# Run backend server (from project root)
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### Key URLs
- Frontend: `http://localhost:8000/app`
- API Docs (Swagger): `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/health`

### Database
```bash
# Database is SQLite at data/learning.db
# To add new columns (example):
python3 -c "
import sqlite3
conn = sqlite3.connect('data/learning.db')
cursor = conn.cursor()
cursor.execute('ALTER TABLE table_name ADD COLUMN column_name TYPE DEFAULT value')
conn.commit()
conn.close()
"
```

## Architecture

### Backend (`backend/`)
- **main.py** - FastAPI app with all API endpoints, CORS config, code execution sandbox, Pydantic models
- **database.py** - SQLAlchemy ORM models (User, SearchHistory, UnderstandingLevel, ExplanationCache), DB operations, analytics queries
- **claude_service.py** - Claude API wrapper, multi-level explanation generation, practice problem generation

### Frontend (`frontend/`)
- **app.js** - Single-page app with state management, DOM caching, REST API integration, Monaco Editor, Chart.js
- **index.html** - HTML structure with modals, dashboard, practice card
- **styles.css** - CSS with custom properties for theming

### Database Schema
- **Users**: id, username, created_at
- **SearchHistory**: id, user_id, term, searched_at, search_count
- **UnderstandingLevel**: id, user_id, term, level (1-3), updated_at
- **ExplanationCache**: id, term, level, explanation, created_at

## Key Concepts

### Learning Levels (1-3)
- **Level 1**: Simple explanation with one code example, concrete analogy
- **Level 2**: Continues same scenario, adds related keyword
- **Level 3**: Multiple keywords combined, real-world application

Each level maintains narrative continuity (same functions/scenarios).

### Code Execution Safety
Sandboxed Python execution with restricted builtins. Blocks: `import os/sys`, `subprocess`, `exec`, `eval`, `__import__`, `open`.

### API Endpoints
- `POST /search` - Get term explanation (params: term, level)
- `POST /feedback` - Record understanding (params: term, understood, current_level)
- `POST /practice` - Get practice problem
- `POST /execute` - Execute Python code safely
- `GET /analytics/*` - Dashboard data (daily, keywords, progress, recommendations)

## Environment Variables

Required in `.env`:
```
ANTHROPIC_API_KEY=sk-ant-xxxxx
```

## Important Notes

- Single-user prototype (uses "default_user")
- Japanese UI text throughout
- Explanation caching reduces API calls
- Chart.js must load before Monaco Editor's loader.js (AMD conflict)
- Frontend expects backend at `http://localhost:8000`
