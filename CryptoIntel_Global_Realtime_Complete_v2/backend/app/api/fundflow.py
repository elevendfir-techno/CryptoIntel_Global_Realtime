from fastapi import APIRouter, HTTPException, Query
import httpx,re
router=APIRouter()
MEMPOOL="https://mempool.space/api"
ETH_RPC="https://ethereum-rpc.publicnode.com"

@router.get("/fundflow/{address}")
async def fundflow(address:str, network:str=Query(...), hops:int=Query(1,ge=1,le=2)):
    network=network.lower()
    async with httpx.AsyncClient(timeout=20) as c:
        if network=="bitcoin":
            r=await c.get(f"{MEMPOOL}/address/{address}/txs")
            if not r.is_success: raise HTTPException(r.status_code,"Bitcoin transaction source unavailable")
            txs=r.json()[:50]
            nodes=[{"id":address,"label":address[:12]+"…","type":"root"}]; edges=[]
            seen={address}
            for tx in txs:
                for vin in tx.get("vin",[])[:10]:
                    a=vin.get("prevout",{}).get("scriptpubkey_address")
                    if a and a not in seen:
                        seen.add(a); nodes.append({"id":a,"label":a[:12]+"…","type":"wallet"}); edges.append({"source":a,"target":address,"value":vin.get("prevout",{}).get("value",0),"asset":"BTC"})
                for vout in tx.get("vout",[])[:10]:
                    a=vout.get("scriptpubkey_address")
                    if a and a not in seen:
                        seen.add(a); nodes.append({"id":a,"label":a[:12]+"…","type":"wallet"}); edges.append({"source":address,"target":a,"value":vout.get("value",0),"asset":"BTC"})
            return {"network":"bitcoin","root":address,"hops":hops,"nodes":nodes[:40],"edges":edges[:80],"transactions":len(txs),"source":"mempool.space"}
        if network=="ethereum" and re.match(r"^0x[a-fA-F0-9]{40}$",address):
            # JSON-RPC is intentionally used for live balance; historical graph requires an indexer.
            r=await c.post(ETH_RPC,json={"jsonrpc":"2.0","id":1,"method":"eth_getBalance","params":[address,"latest"]})
            if not r.is_success: raise HTTPException(r.status_code,"Ethereum RPC unavailable")
            return {"network":"ethereum","root":address,"hops":hops,"nodes":[{"id":address,"label":address[:12]+"…","type":"root"}],"edges":[],"transactions":0,"note":"Public RPC mode: enable an indexed Blockscout source for historical edges.","source":"PublicNode"}
        raise HTTPException(400,"Fund flow currently supports bitcoin and ethereum in this keyless build")
