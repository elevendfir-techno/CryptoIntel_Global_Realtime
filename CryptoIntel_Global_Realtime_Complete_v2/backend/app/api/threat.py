from fastapi import APIRouter
import httpx, csv, io
router=APIRouter()
@router.get("/threat-intel")
async def threat_intel():
    feeds={}
    async with httpx.AsyncClient(timeout=20,headers={"User-Agent":"CryptoIntel/2.0"}) as c:
        try:
            r=await c.get("https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json")
            feeds["cisa_kev"]=r.json().get("vulnerabilities",[])[:100] if r.is_success else []
        except: feeds["cisa_kev"]=[]
        try:
            r=await c.get("https://feodotracker.abuse.ch/downloads/ipblocklist_recommended.txt")
            ips=[x.strip() for x in r.text.splitlines() if x.strip() and not x.startswith("#")] if r.is_success else []
            feeds["feodo_ips"]=ips[:200]
        except: feeds["feodo_ips"]=[]
    return {"sources":{"cisa_kev":len(feeds["cisa_kev"]),"feodo_ips":len(feeds["feodo_ips"])},"items":feeds}
