import asyncio, json, time, hashlib
from collections import deque
import httpx, websockets

BINANCE_REST="https://api.binance.com/api/v3"
BINANCE_WS="wss://stream.binance.com:9443/stream?streams=btcusdt@ticker/ethusdt@ticker/solusdt@ticker/trxusdt@ticker/xrpusdt@ticker/adausdt@ticker/ltcusdt@ticker"
MEMPOOL="https://mempool.space/api"
PUBLICNODE_ETH="https://ethereum-rpc.publicnode.com"
SOLANA_RPC="https://api.mainnet-beta.solana.com"
TRON_RPC="https://api.trongrid.io/wallet/getnowblock"
KOIOS="https://api.koios.rest/api/v1/tip"
XRPL="https://xrplcluster.com/"

class Engine:
    def __init__(self):
        self.clients=set()
        self.running=False
        self.tasks=[]
        self.markets={}
        self.activity=deque(maxlen=2000)
        self.alerts=deque(maxlen=500)
        self.alert_keys=set()
        self.events_received=0
        self.sources={}
        self.http=httpx.AsyncClient(timeout=15, headers={"User-Agent":"CryptoIntel/2.0"})
    async def start(self):
        self.running=True
        self.tasks=[
            asyncio.create_task(self.binance_loop()),
            asyncio.create_task(self.chain_loop()),
            asyncio.create_task(self.refresh_sources()),
        ]
    async def stop(self):
        self.running=False
        for t in self.tasks: t.cancel()
        await self.http.aclose()
    async def publish(self, payload):
        dead=[]
        for ws in list(self.clients):
            try: await ws.send_json(payload)
            except Exception: dead.append(ws)
        for ws in dead: self.clients.discard(ws)
    def add_activity(self, item):
        item["ts"]=item.get("ts",time.time())
        self.activity.append(item); self.events_received+=1
    def alert(self, kind, severity, title, detail, entity=None):
        raw=f"{kind}|{title}|{detail}|{entity or ''}"
        key=hashlib.sha256(raw.encode()).hexdigest()
        if key in self.alert_keys: return
        self.alert_keys.add(key)
        a={"id":key[:16],"ts":time.time(),"kind":kind,"severity":severity,"title":title,"detail":detail,"entity":entity}
        self.alerts.append(a)
        asyncio.create_task(self.publish({"type":"alert","alert":a}))
    async def binance_loop(self):
        while self.running:
            try:
                async with websockets.connect(BINANCE_WS,ping_interval=20,ping_timeout=20) as ws:
                    self.sources["binance"]="connected"
                    async for msg in ws:
                        d=json.loads(msg).get("data",{})
                        if not d: continue
                        sym=d.get("s","").upper()
                        item={"type":"market","source":"Binance","symbol":sym,"price":float(d.get("c",0)),"change24h":float(d.get("P",0)),"volume":float(d.get("v",0)),"ts":d.get("E",time.time()*1000)/1000}
                        self.markets[sym]=item
                        self.add_activity({"type":"trade","source":"Binance","symbol":sym,"price":item["price"],"change24h":item["change24h"]})
                        if abs(item["change24h"])>=8:
                            self.alert("MARKET_MOVE","HIGH",f"{sym} 24h move {item['change24h']:.2f}%","Large market movement detected",sym)
                        await self.publish({"type":"market","item":item})
            except Exception as e:
                self.sources["binance"]=f"error: {str(e)[:80]}"
                await asyncio.sleep(5)
    async def chain_loop(self):
        while self.running:
            try:
                r=await self.http.get(MEMPOOL+"/blocks/tip/height")
                if r.is_success:
                    h=int(r.text)
                    self.sources["bitcoin"]="connected"
                    self.add_activity({"type":"block","network":"bitcoin","height":h,"source":"mempool.space"})
                    await self.publish({"type":"chain","item":self.activity[-1]})
            except Exception as e: self.sources["bitcoin"]=f"error: {str(e)[:80]}"
            try:
                r=await self.http.post(PUBLICNODE_ETH,json={"jsonrpc":"2.0","id":1,"method":"eth_blockNumber","params":[]})
                if r.is_success:
                    h=int(r.json()["result"],16)
                    self.sources["ethereum"]="connected"
                    self.add_activity({"type":"block","network":"ethereum","height":h,"source":"PublicNode"})
                    await self.publish({"type":"chain","item":self.activity[-1]})
            except Exception as e: self.sources["ethereum"]=f"error: {str(e)[:80]}"
            await asyncio.sleep(10)
    async def refresh_sources(self):
        while self.running:
            for name,url,method in [
                ("solana",SOLANA_RPC,"rpc"),("cardano",KOIOS,"get"),("tron",TRON_RPC,"get"),("xrpl",XRPL,"get")
            ]:
                try:
                    if method=="rpc":
                        r=await self.http.post(url,json={"jsonrpc":"2.0","id":1,"method":"getHealth"})
                    elif name=="xrpl":
                        r=await self.http.post(url,json={"jsonrpc":"2.0","id":1,"method":"server_info","params":[]})
                    else: r=await self.http.get(url)
                    self.sources[name]="connected" if r.is_success else f"http {r.status_code}"
                except Exception as e: self.sources[name]=f"error: {str(e)[:60]}"
            await asyncio.sleep(30)
    def market_snapshot(self):
        return {"items":list(self.markets.values()),"sources":self.sources}
    def health(self):
        return {"status":"ok","events_received":self.events_received,"markets":len(self.markets),"alerts":len(self.alerts),"sources":self.sources}
engine=Engine()
