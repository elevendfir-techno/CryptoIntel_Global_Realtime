import re, httpx
from fastapi import APIRouter, HTTPException, Query
router=APIRouter()
ETH_RPC="https://ethereum-rpc.publicnode.com"
SOL_RPC="https://api.mainnet-beta.solana.com"
MEMPOOL="https://mempool.space/api"
XRPL="https://xrplcluster.com/"

def net_for(addr):
    if re.match(r"^0x[a-fA-F0-9]{40}$",addr): return "ethereum"
    if re.match(r"^(bc1|[13])[a-zA-Z0-9]{20,}$",addr): return "bitcoin"
    if re.match(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$",addr):
        if addr.startswith("r"): return "xrp"
        return "solana"
    return "unknown"

@router.get("/wallet/{address}")
async def wallet(address:str, network:str|None=None):
    network=(network or net_for(address)).lower()
    async with httpx.AsyncClient(timeout=15) as c:
        if network=="bitcoin":
            r=await c.get(f"{MEMPOOL}/address/{address}")
            if not r.is_success: raise HTTPException(r.status_code,"Bitcoin source unavailable")
            d=r.json()
            return {"network":"bitcoin","address":address,"balance_sat":d.get("chain_stats",{}).get("funded_txo_sum",0)-d.get("chain_stats",{}).get("spent_txo_sum",0),"tx_count":d.get("chain_stats",{}).get("tx_count",0),"source":"mempool.space","geo":{"status":"not exposed by blockchain","from":None,"to":None}}
        if network=="ethereum":
            payload={"jsonrpc":"2.0","id":1,"method":"eth_getBalance","params":[address,"latest"]}
            r=await c.post(ETH_RPC,json=payload)
            if not r.is_success: raise HTTPException(r.status_code,"Ethereum RPC unavailable")
            bal=int(r.json()["result"],16)/1e18
            return {"network":"ethereum","address":address,"balance_native":bal,"tx_count":"RPC basic mode","source":"PublicNode","geo":{"status":"not exposed by blockchain","from":None,"to":None}}
        if network=="xrp":
            r=await c.post(XRPL,json={"jsonrpc":"2.0","id":1,"method":"account_info","params":[{"account":address,"ledger_index":"validated"}]})
            if not r.is_success: raise HTTPException(r.status_code,"XRPL unavailable")
            d=r.json().get("result",{})
            return {"network":"xrp","address":address,"balance_xrp":int(d.get("account_data",{}).get("Balance",0))/1e6,"sequence":d.get("account_data",{}).get("Sequence"),"source":"xrplcluster","geo":{"status":"not exposed by blockchain","from":None,"to":None}}
        if network=="solana":
            r=await c.post(SOL_RPC,json={"jsonrpc":"2.0","id":1,"method":"getBalance","params":[address]})
            if not r.is_success: raise HTTPException(r.status_code,"Solana RPC unavailable")
            return {"network":"solana","address":address,"balance_sol":r.json().get("result",{}).get("value",0)/1e9,"source":"Solana public RPC","geo":{"status":"not exposed by blockchain","from":None,"to":None}}
        raise HTTPException(400,"Unsupported or ambiguous wallet format")
