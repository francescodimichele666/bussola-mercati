import re, urllib.request, urllib.parse
UA={"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) BussolaMercati/1.0","Accept":"*/*"}
def get(u):
    try:
        r=urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=40); return r.status, r.read().decode("utf-8","ignore")
    except Exception as e: return str(e)[:80], ""
U=["https://ec.europa.eu/eurostat/news/euro-indicators/release-calendar",
"https://ec.europa.eu/eurostat/web/main/news/release-calendar",
"https://ec.europa.eu/eurostat/en/news/euro-indicators",
"https://www.bls.gov/schedule/news_release/bls.ics",
"https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm",
"https://www.ecb.europa.eu/press/calendars/mgcgc/html/index.en.html",
"https://www.istat.it/calendario-comunicati-stampa/",
"https://www.istat.it/it/calendario-comunicati-stampa",
"https://www.bea.gov/news/schedule",
"https://www.bankofengland.co.uk/monetary-policy/upcoming-mpc-dates"]
for u in U:
    st,h=get(u); print("\n=== ",st,len(h),u)
    links=set(urllib.parse.urljoin(u,x) for x in re.findall(r'(?:href|src|data-url)="([^"]+)"',h) if re.search(r'\.ics|json|\.xml|csv|export|api|calendar|ical|rss',x,re.I))
    for l in sorted(links)[:25]: print("  L",l)
    if u.endswith(".ics"): print(h[:1500])
    txt=re.sub(r"<[^>]+>"," ",h); txt=re.sub(r"\s+"," ",txt)
    for k in ["November 2026","novembre 2026","2026-11","Nov 2026","December 2026"]:
        i=txt.find(k)
        if i>=0: print("  T",k,"::",txt[max(0,i-200):i+300]); break
