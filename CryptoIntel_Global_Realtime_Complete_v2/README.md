# CryptoIntel Global Real-Time Intelligence v2

A keyless/public-source, Render-ready cyber-security style crypto intelligence platform.

## Included
- FastAPI backend + WebSocket live bus
- Binance public market ticker stream
- Bitcoin live block telemetry through mempool.space
- Ethereum live block telemetry through PublicNode
- Solana, TRON, XRP and Cardano source health
- Wallet investigation: BTC, ETH, SOL, XRP
- BTC fund-flow graph data; ETH public-RPC mode
- Deduplicated detections/alerts
- Threat intelligence ingestion from CISA KEV and Feodo Tracker
- Responsive SOC-style React/Vite frontend
- Geo-attribution guardrail: on-chain transactions do not contain physical sender/receiver location

## Local
Backend:
`cd backend`
`pip install -r requirements.txt`
`uvicorn app.main:app --reload --port 8000`

Frontend:
`cd frontend`
`npm install`
`npm run dev`

Set `VITE_API_URL` for production frontend.

## Render
Backend: Root Directory `backend`; Build `pip install -r requirements.txt`; Start `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.

Frontend: Static Site; Root Directory `frontend`; Build `npm install && npm run build`; Publish `dist`; Environment variable `VITE_API_URL=https://YOUR-BACKEND.onrender.com`.

## Important
Public endpoints are rate-limited and can change. The application reports degraded sources rather than inventing data.
