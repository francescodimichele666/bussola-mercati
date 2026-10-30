import urllib.request, pathlib, http.cookiejar
cj=http.cookiejar.CookieJar(); op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
UA={"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) BussolaMercati/1.0","Accept":"*/*"}
def get(u,h=None):
    try: return op.open(urllib.request.Request(u,headers={**UA,**(h or {})}),timeout=40).read()
    except Exception as e: print("ERR",u,e); return b""
P=pathlib.Path("cal_raw"); P.mkdir(exist_ok=True)
get("https://ec.europa.eu/eurostat/news/euro-indicators/release-calendar")
b=get("https://ec.europa.eu/eurostat/o/calendars/eventsJson?theme=0&category=0&keywords=&isEuroindicator=true&authorInclude=&authorExclude=&start=2026-10-26T00%3A00%3A00%2B01%3A00&end=2026-12-07T00%3A00%3A00%2B01%3A00",{"X-Requested-With":"XMLHttpRequest","Accept":"application/json","Referer":"https://ec.europa.eu/eurostat/news/euro-indicators/release-calendar"})
(P/"eurostat_ev.json").write_bytes(b); print("eurostat cookies",len(b))
for i,c in enumerate(["3vk31mkd3ocvufmqol6ie25mso","4s57ih6d08n330qrm9ee575nog","gd4th8t929jsuj3nh4np8r25as","tbv42ne55nm9f3u83plt96tio4","vfjfh1jpkirilum8s3eu7932c8"]):
    b=get(f"https://www.google.com/calendar/ical/{c}%40group.calendar.google.com/public/basic.ics"); (P/f"istat_{i}.ics").write_bytes(b); print("istat",i,len(b))
