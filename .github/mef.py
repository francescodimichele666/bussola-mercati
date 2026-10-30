import re, urllib.request, urllib.parse, sys
UA={"User-Agent":"Mozilla/5.0 BussolaMercati/1.0"}
def get(u):
    try:
        r=urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=30)
        return r.status, r.read()
    except Exception as e:
        return str(e), b""
seeds=["https://www.dt.mef.gov.it/it/debito_pubblico/dati_statistici/",
"https://www.dt.mef.gov.it/it/debito_pubblico/titoli_di_stato/",
"https://www.dt.mef.gov.it/it/debito_pubblico/"]
seen=set(); files=set(); queue=[(s,0) for s in seeds]
while queue and len(seen)<60:
    u,d=queue.pop(0)
    if u in seen: continue
    seen.add(u); st,b=get(u); print("PAGE",st,u)
    for h in re.findall(r'href="([^"#]+)"',b.decode("utf-8","ignore")):
        a=urllib.parse.urljoin(u,h)
        if re.search(r'\.(xlsx?|csv|zip)(\?|$)',a,re.I): files.add(a)
        elif d<2 and "dt.mef.gov.it/it/debito_pubblico" in a and a not in seen: queue.append((a,d+1))
for f in sorted(files): print("FILE",f)
for f in sorted(files):
    if re.search(r'circolaz|titoli',f,re.I):
        st,b=get(f); print("GET",st,len(b),f)
