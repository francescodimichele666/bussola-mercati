import re, urllib.request, pathlib
UA={"User-Agent":"Mozilla/5.0 BussolaMercati/1.0"}
def get(u): return urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=60).read()
base="https://www.dt.mef.gov.it/export/sites/sitodt/modules/documenti_it/debito_pubblico/"
for name,u in [("scadenze.csv",base+"scadenze_titoli_suddivise_per_anno/Scadenze-suddivise-per-anno-aggiornamento-al-30-settembre-2026.csv"),
               ("cedole_cct.csv",base+"cedole_cct_e_ccteu/Cedole-CCTeu-in-corso-al-30-Settembre-2026-.csv"),
               ("pagina.html","https://www.dt.mef.gov.it/it/debito_pubblico/dati_statistici/scadenze_titoli_suddivise_anno/")]:
    pathlib.Path("mef_raw").mkdir(exist_ok=True); pathlib.Path("mef_raw/"+name).write_bytes(get(u)); print("ok",name)
