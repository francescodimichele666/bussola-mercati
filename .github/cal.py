import urllib.request, pathlib
UA={"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) BussolaMercati/1.0","Accept":"*/*"}
def get(u):
    try: return urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=40).read()
    except Exception as e: print("ERR",u,e); return b""
P=pathlib.Path("cal_raw"); P.mkdir(exist_ok=True)
for n,u in {"eurostat.html":"https://ec.europa.eu/eurostat/news/euro-indicators/release-calendar",
 "bls.ics":"https://www.bls.gov/schedule/news_release/bls.ics",
 "bea.ics":"https://www.bea.gov/news/schedule/ics/online-calendar-subscription.ics",
 "fomc.html":"https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm",
 "ecb.html":"https://www.ecb.europa.eu/press/calendars/mgcgc/html/index.en.html",
 "istat_home.html":"https://www.istat.it/",
 "istat_cal.html":"https://www.istat.it/calendario-diffusione/",
 "istat_cal2.html":"https://www.istat.it/it/archivio/calendario"}.items():
    b=get(u); (P/n).write_bytes(b); print(n,len(b))
