# Working rules for AI assistants in this repo

Read `README.md`, `ARCHITECTURE.md` and `IMPLEMENTATION_PLAN.md` before writing code.

## Scope and size
- This is a junior-sized portfolio project. Choose the simplest design that works and can be explained in an interview. No enterprise patterns, no extra services, no thesis-level evaluation.
- Follow the phases in `IMPLEMENTATION_PLAN.md` in order. Do not add features from the "Explicitly not doing" list.
- New decisions go into `DECISIONS.md` in a few lines.

## Stack (fixed)
- Backend: Python, FastAPI, LangGraph, Gemini free tier, yfinance, SQLite.
- Frontend: React, Vite, Tailwind. Not Streamlit.
- Deploy: Render for the backend, Vercel for the frontend.

## Code rules
- Type hints on public functions, small modules, prompts in `graph/prompts.py`.
- Tools return dicts and never raise to the model.
- Every loop has a cap (steps 6, tool calls 3 per worker, revisions 2).
- Keep LLM calls per answer between 6 and 10. If a change adds calls, say so.
- Tests must run offline with fixtures and a fake LLM.

## Honesty rules
- Only write numbers in the README, article or CV text that were measured by the demo-set script. If something was not measured, leave it out or label it as not measured.
- The critic checks evidence against findings; do not describe it as verifying truth.
- Keep the disclaimer in the UI, in reports and in the README. Never add trading or brokerage features.

## Secrets and setup
- Never commit `.env`. `GOOGLE_API_KEY` lives only in `backend/.env` locally and in Render's secret settings.
- The owner's internet is slow. Before installing large packages or downloading models, check the size and ask.
- Do not touch `../AlphaSwarm`, it is live on Render.

## Publishing flow (after the app works)
Medium article, then a Sanity project card under the AI Engineer category, then the CV update. Follow the owner's earlier workflow notes for these steps.
