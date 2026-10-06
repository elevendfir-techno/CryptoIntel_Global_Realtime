import asyncio, time
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from .services.engine import engine
from .api.wallets import router as wallet_router
from .api.fundflow import router as fundflow_router
from .api.threat import router as threat_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    await engine.start()
    yield
    await engine.stop()

app=FastAPI(title="CryptoIntel", version="2.0.0", description="Global real-time crypto intelligence platform")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(wallet_router, prefix="/api")
app.include_router(fundflow_router, prefix="/api")
app.include_router(threat_router, prefix="/api")

@app.get("/")
async def root():
    return {"name":"CryptoIntel","status":"online","scope":"global real-time crypto intelligence","version":"2.0.0"}

@app.get("/api/health")
async def health():
    return engine.health()

@app.get("/api/markets")
async def markets():
    return engine.market_snapshot()

@app.get("/api/activity")
async def activity(limit:int=Query(100, ge=1, le=500)):
    return {"items":engine.activity[-limit:]}

@app.get("/api/alerts")
async def alerts(limit:int=Query(100, ge=1, le=500)):
    return {"items":engine.alerts[-limit:]}

@app.websocket("/ws/live")
async def ws_live(ws: WebSocket):
    await ws.accept()
    engine.clients.add(ws)
    try:
        await ws.send_json({"type":"snapshot","markets":engine.market_snapshot(),"alerts":engine.alerts[-50:],"activity":engine.activity[-100:]})
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        engine.clients.discard(ws)
    except Exception:
        engine.clients.discard(ws)
