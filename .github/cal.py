import urllib.request, pathlib
UA={"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) BussolaMercati/1.0","Accept":"*/*"}
def get(u):
    try: return urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=40).read()
    except Exception as e: print("ERR",u,e); return b""
P=pathlib.Path("cal_raw"); P.mkdir(exist_ok=True)
for n,u in {"eurostat_ev.json":"https://ec.europa.eu/eurostat/o/calendars/eventsJson?start=2026-10-26T00:00:00&end=2026-12-07T00:00:00&theme=0&category=0&keywords=&isEuroindicator=true&authorInclude=&authorExclude=&timeZone=Europe/Luxembourg",
 "eurostat_ev2.json":"https://ec.europa.eu/eurostat/o/calendars/eventsJson?start=2026-10-26&end=2026-12-07",
 "istat_cal.html":"https://www.istat.it/attivita-e-servizi-per-tipo-di-utenti/giornalisti/appuntamenti/calendario-delle-diffusioni-e-degli-eventi/"}.items():
    b=get(u); (P/n).write_bytes(b); print(n,len(b))
