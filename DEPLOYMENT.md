# Deployment: Render (backend) and Vercel (frontend)

Both run on free plans. Order matters: backend first, then frontend, then a CORS update.

## 0. Before you start

- Code pushed to a GitHub repository (suggested name: `AlphaDesk`).
- A Gemini API key from Google AI Studio.
- Accounts on Render and Vercel (both can sign in with GitHub).

## 1. Backend on Render

1. In Render choose **New → Blueprint** and select the repository. Render reads `render.yaml` at the repo root.
2. Render creates a web service named `alphadesk-api` with `rootDir: backend`.
3. When prompted, set the secret environment variables:
   - `GOOGLE_API_KEY`: your Gemini key
   - `ALLOWED_ORIGINS`: leave a placeholder such as `http://localhost:5173` for now
4. Deploy. Check `https://<service>.onrender.com/health`. It should return `{"status":"ok", ...}`.

Free-tier behaviour to expect:

- The service sleeps after about 15 minutes without traffic and takes roughly 50 seconds to wake up. The frontend shows a "waking the server" message for this.
- The disk is ephemeral. SQLite memory resets when the service redeploys or restarts.

## 2. Frontend on Vercel

1. In Vercel choose **Add New → Project** and import the same repository.
2. Set **Root Directory** to `frontend`. Framework preset: Vite. Build command `npm run build`, output `dist`.
3. Add the environment variable `VITE_API_URL` with the Render URL (no trailing slash).
4. Deploy and note the production URL, for example `https://alphadesk.vercel.app`.

## 3. Connect them

1. Back in Render, set `ALLOWED_ORIGINS` to the Vercel production URL (comma-separate multiple origins, such as a custom domain).
2. Redeploy the backend (Render restarts automatically after an environment change).
3. Open the Vercel URL and ask a question.

## 4. Smoke test checklist

- [ ] `/health` returns ok
- [ ] Browser console has no CORS errors
- [ ] A question shows plan, tool calls, critic verdict and a final report in the trace panel
- [ ] A follow-up in the same thread uses the earlier context
- [ ] Setting a risk profile and reloading the page keeps it (until the next redeploy)
- [ ] An invalid ticker produces a friendly error, not a stack trace

## 5. Environment variables

| Variable | Where | Example | Notes |
|---|---|---|---|
| `GOOGLE_API_KEY` | Render | (secret) | Never commit it or expose it to the frontend |
| `MODEL_NAME` | Render | `gemini-3.8-flash` | Set in `render.yaml` |
| `OPENROUTER_API_KEY` | Render | (secret) | Free key from openrouter.ai/keys |
| `OPENROUTER_MODELS` | Render | comma-separated `:free` ids | Tried in order before Gemini |
| `ALLOWED_ORIGINS` | Render | `https://alphadesk.vercel.app` | Comma separated |
| `DB_PATH` | Render | `./alphadesk.db` | Ephemeral on the free plan |
| `RATE_LIMIT_PER_HOUR` | Render | `6` | Per IP |
| `VITE_API_URL` | Vercel | `https://alphadesk-api.onrender.com` | Baked in at build time |

## 6. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Browser shows a CORS error | `ALLOWED_ORIGINS` missing the Vercel URL | Update it in Render, redeploy |
| First request hangs for a minute | Render cold start | Wait; the UI explains it |
| `model_busy` error | Gemini free-tier rate limit | Wait a minute; the fallback model is tried automatically |
| Memory vanished | Render redeploy cleared the disk | Expected on the free plan |
| Frontend calls `localhost` | `VITE_API_URL` not set before the build | Set it in Vercel, then redeploy |
