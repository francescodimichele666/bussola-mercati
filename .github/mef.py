import re, urllib.request
UA={"User-Agent":"Mozilla/5.0 BussolaMercati/1.0"}
def get(u): return urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=60).read()
P="https://www.dt.mef.gov.it/it/debito_pubblico/dati_statistici/scadenze_titoli_suddivise_anno/"
h=get(P).decode("utf-8","ignore")
for m in re.finditer(r'href="([^"]+\.csv)"[^>]*>(.{0,120})',h): print("LINK",m.group(1),"|",re.sub(r"<[^>]+>","",m.group(2))[:80])
U="https://www.dt.mef.gov.it/export/sites/sitodt/modules/documenti_it/debito_pubblico/scadenze_titoli_suddivise_per_anno/Scadenze-suddivise-per-anno-aggiornamento-al-30-settembre-2026.csv"
b=get(U); print("BYTES",b[:4])
for enc in ("utf-8","cp1252"):
    try: t=b.decode(enc); print("ENC",enc); break
    except: pass
L=t.splitlines(); print("NLINES",len(L))
for i,l in enumerate(L):
    if i<45 or i%25==0 or i>len(L)-12: print(i,"|",l)
