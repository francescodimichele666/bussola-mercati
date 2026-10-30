"""
Calendario economico costruito ogni giorno dalle fonti ufficiali.

Fonti (tutte pubbliche e gratuite):
  Eurostat  calendario degli "euro indicators" (area euro)
  Istat     calendario dei comunicati stampa (Italia)
  BCE       date delle riunioni di politica monetaria
  Fed       date delle riunioni del FOMC
  BLS, BEA  calendari ufficiali degli Stati Uniti (lavoro, inflazione, PIL, consumi)

Per ogni appuntamento: data e ora, nome e spiegazione in italiano, l'ultimo dato
disponibile preso da site/data/data.json (le stesse serie ufficiali del sito).
Le previsioni degli analisti non ci sono: non esiste una fonte gratuita e lecita.

Se una fonte non risponde, le altre bastano. Se non risponde quasi nessuna,
il file già pubblicato resta com'è.

Uso:  python engine/calendario.py --out site/data/calendario.json
"""
import argparse
import http.cookiejar
import json
import re
import sys
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pagine import FAMIGLIE  # spiegazioni in italiano, uguali a quelle già scritte

ROOT = Path(__file__).resolve().parent.parent
# Alcuni siti (es. BLS) rifiutano le richieste senza un User-Agent "da browser".
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) BussolaMercati/1.0 (+https://github.com/francescodimichele666/bussola-mercati)"}
ROMA, NY, LUX = ZoneInfo("Europe/Rome"), ZoneInfo("America/New_York"), ZoneInfo("Europe/Luxembourg")
MESI = "gennaio febbraio marzo aprile maggio giugno luglio agosto settembre ottobre novembre dicembre".split()
MONTHS = "January February March April May June July August September October November December".split()
PAESI = {"IT": "Italia", "EU": "Area euro", "US": "Stati Uniti"}

FONTI = {
    "Eurostat": "https://ec.europa.eu/eurostat/news/euro-indicators/release-calendar",
    "Istat": "https://www.istat.it/attivita-e-servizi-per-tipo-di-utenti/giornalisti/appuntamenti/calendario-delle-diffusioni-e-degli-eventi/",
    "BCE": "https://www.ecb.europa.eu/press/calendars/mgcgc/html/index.en.html",
    "Fed": "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm",
    "BLS": "https://www.bls.gov/schedule/news_release/",
    "BEA": "https://www.bea.gov/news/schedule",
}
ISTAT_ICS = "https://www.google.com/calendar/ical/4s57ih6d08n330qrm9ee575nog%40group.calendar.google.com/public/basic.ics"

# (regex sul titolo originale, nome italiano, famiglia, molto seguito, serie per l'ultimo dato)
EUROSTAT = [
    (r"^Flash estimate inflation", "Inflazione, stima rapida", "inflazione", True, "infl_EA"),
    (r"^Inflation \(HICP\)", "Inflazione, dato definitivo", "inflazione", False, "infl_EA"),
    (r"^Unemployment$", "Tasso di disoccupazione", "lavoro", False, "disocc_EA"),
    (r"^Preliminary flash estimate GDP", "PIL, stima preliminare", "pil", True, "pil_EA"),
    (r"^Flash estimate GDP", "PIL e occupazione, stima rapida", "pil", False, "pil_EA"),
    (r"^GDP main aggregates", "PIL, dato completo", "pil", False, "pil_EA"),
    (r"^Retail trade", "Vendite al dettaglio", "consumi", False, None),
    (r"^Industrial production", "Produzione industriale", "produzione", False, None),
    (r"^Production in construction", "Produzione nelle costruzioni", "produzione", False, None),
    (r"^Services production", "Produzione nei servizi", "produzione", False, None),
    (r"^Economic Sentiment", "Fiducia di famiglie e imprese", "fiducia", False, None),
    (r"^Industrial producer prices", "Prezzi alla produzione", "prezzi_imprese", False, None),
    (r"^International trade in goods", "Commercio estero", "commercio", False, None),
    (r"^Building permits", "Permessi di costruzione", "casa", False, None),
]
ISTAT = [
    (r"^Prezzi al consumo \(stima provvisoria\)", "Inflazione, stima preliminare", "inflazione", True, "infl_IT"),
    (r"^Prezzi al consumo$", "Inflazione, dato definitivo", "inflazione", False, "infl_IT"),
    (r"^Occupati e disoccupati", "Occupati e disoccupati", "lavoro", True, "disocc_IT"),
    (r"^Stima preliminare del Pil$", "PIL, stima preliminare", "pil", True, "pil_IT"),
    (r"^Conti economici trimestrali$", "PIL, conti trimestrali", "pil", False, "pil_IT"),
    (r"^Produzione industriale", "Produzione industriale", "produzione", False, None),
    (r"^Commercio al dettaglio", "Vendite al dettaglio", "consumi", False, None),
    (r"^Fiducia dei consumatori e delle imprese", "Fiducia di consumatori e imprese", "fiducia", False, None),
    (r"^Prezzi alla produzione dell", "Prezzi alla produzione", "prezzi_imprese", False, None),
    (r"^Commercio estero extra Ue", "Commercio estero con i Paesi extra Ue", "commercio", False, None),
    (r"^Commercio estero e prezzi", "Commercio estero", "commercio", False, None),
    (r"^Retribuzioni contrattuali", "Salari dei contratti", "salari", False, None),
    (r"^Prezzi delle abitazioni", "Prezzi delle case", "casa", False, None),
]
BLS = [
    (r"^Employment Situation$", "Rapporto sul lavoro: occupati e disoccupazione", "lavoro", True, None),
    (r"^Consumer Price Index$", "Inflazione (prezzi al consumo)", "inflazione", True, "infl_us"),
    (r"^Producer Price Index$", "Prezzi alla produzione", "prezzi_imprese", False, None),
    (r"^Job Openings and Labor Turnover Survey$", "Posti di lavoro vacanti (JOLTS)", "lavoro", False, None),
    (r"^Employment Cost Index$", "Indice del costo del lavoro", "salari", False, None),
]
BEA = [
    (r"^GDP \(Advance Estimate\)", "PIL, prima stima", "pil", True, None),
    (r"^GDP \(Second Estimate\)", "PIL, seconda stima", "pil", False, None),
    (r"^GDP \(Third Estimate\)", "PIL, terza stima", "pil", False, None),
    (r"^Personal Income and Outlays", "Redditi, spesa delle famiglie e inflazione PCE", "consumi", True, None),
    (r"^U\.S\. International Trade in Goods and Services, (?!Annual)", "Commercio estero", "commercio", False, None),
]


def _opener():
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))


def scarica(url, op=None, headers=None):
    req = urllib.request.Request(url, headers={**UA, **(headers or {})})
    with (op or _opener()).open(req, timeout=60) as r:
        return r.read().decode("utf-8", "ignore")


def regola(titolo, regole):
    for pat, nome, fam, alta, serie in regole:
        if re.search(pat, titolo):
            return nome, fam, alta, serie
    return None


def evento(quando, paese, titolo, regola_trovata, fonte, periodo=None):
    nome, fam, alta, serie = regola_trovata
    return {
        "data": quando.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "paese": paese, "nome": nome, "originale": titolo, "fase": None, "famiglia": fam,
        "importanza": "alta" if alta else "normale", "periodo": periodo,
        "effettivo": None, "previsto": None, "precedente": None, "unita": None, "scala": None,
        "fonte": fonte, "fonte_url": FONTI[fonte], "serie": serie,
    }


def ics_eventi(testo):
    """Legge un file .ics: restituisce (inizio, titolo) con l'ora già nel fuso giusto."""
    testo = re.sub(r"\r?\n[ \t]", "", testo)  # righe spezzate
    out = []
    for blocco in re.findall(r"BEGIN:VEVENT(.*?)END:VEVENT", testo, re.S):
        m = re.search(r"^DTSTART(;[^:\n]*)?:(\d{8})(T(\d{6})(Z)?)?", blocco, re.M)
        s = re.search(r"^SUMMARY:(.*)$", blocco, re.M)
        if not m or not s:
            continue
        giorno, ora, utc = m.group(2), m.group(4) or "000000", m.group(5)
        tz = timezone.utc if utc else (NY if "US-Eastern" in (m.group(1) or "") or "New_York" in (m.group(1) or "") else ROMA)
        quando = datetime.strptime(giorno + ora, "%Y%m%d%H%M%S").replace(tzinfo=tz)
        titolo = s.group(1).strip().replace("\\,", ",").replace("\\;", ";")
        out.append((quando, titolo))
    return out


def periodo_it(testo):
    t = testo.strip()
    m = re.match(r"^(I{1,3}|IV) [Tt]rimestre (\d{4})$", t)
    if m:
        return {"I": "1°", "II": "2°", "III": "3°", "IV": "4°"}[m.group(1)] + " trimestre " + m.group(2)
    m = re.match(r"^(\w+) (\d{4})$", t)
    if m and m.group(1).lower() in MESI:
        return m.group(1).lower() + " " + m.group(2)
    m = re.match(r"^(\w+) (\d{4})$", t)
    if m and m.group(1) in MONTHS:
        return MESI[MONTHS.index(m.group(1))] + " " + m.group(2)
    m = re.match(r"^(\d)(?:st|nd|rd|th) Quarter (\d{4})", t)
    if m:
        return m.group(1) + "° trimestre " + m.group(2)
    return None


# ---------------------------------------------------------------- fonti

def da_eurostat(inizio, fine):
    op = _opener()
    scarica(FONTI["Eurostat"], op)  # la pagina dà il cookie di sessione richiesto dall'elenco
    url = ("https://ec.europa.eu/eurostat/o/calendars/eventsJson?theme=0&category=0&keywords="
           "&isEuroindicator=true&authorInclude=&authorExclude="
           f"&start={inizio.isoformat()}T00%3A00%3A00%2B01%3A00&end={fine.isoformat()}T00%3A00%3A00%2B01%3A00")
    dati = json.loads(scarica(url, op, {"X-Requested-With": "XMLHttpRequest", "Accept": "application/json",
                                        "Referer": FONTI["Eurostat"]}))
    out = []
    for e in dati:
        r = regola(e.get("title", ""), EUROSTAT)
        if not r:
            continue
        # Eurostat scrive l'ora di Lussemburgo con una "Z" impropria (le uscite sono alle 11:00 locali)
        quando = datetime.strptime(e["start"][:16], "%Y-%m-%dT%H:%M").replace(tzinfo=LUX)
        out.append(evento(quando, "EU", e["title"], r, "Eurostat"))
    return out


def da_istat():
    out = []
    for quando, titolo in ics_eventi(scarica(ISTAT_ICS)):
        nome, _, per = titolo.partition("|")
        r = regola(nome.strip(), ISTAT)
        if r:
            out.append(evento(quando, "IT", titolo, r, "Istat", periodo_it(per)))
    return out


def da_bls():
    out = []
    for quando, titolo in ics_eventi(scarica("https://www.bls.gov/schedule/news_release/bls.ics")):
        r = regola(titolo, BLS)
        if r:
            out.append(evento(quando, "US", titolo, r, "BLS"))
    return out


def da_bea():
    out = []
    for quando, titolo in ics_eventi(scarica("https://www.bea.gov/news/schedule/ics/online-calendar-subscription.ics")):
        r = regola(titolo, BEA)
        if r:
            per = re.search(r", ((?:January|February|March|April|May|June|July|August|September|October|November|December) \d{4}|\d(?:st|nd|rd|th) Quarter \d{4})", titolo)
            out.append(evento(quando, "US", titolo, r, "BEA", periodo_it(per.group(1)) if per else None))
    return out


def da_bce():
    html = scarica(FONTI["BCE"])
    out = []
    for g, testo in re.findall(r"<dt[^>]*>(.*?)</dt>\s*<dd[^>]*>(.*?)</dd>", html, re.S):
        g = re.sub(r"<[^>]+>|\s+", "", g)
        testo = re.sub(r"<[^>]+>|\s+", " ", testo).strip()
        if not re.fullmatch(r"\d{2}/\d{2}/\d{4}", g):
            continue
        if "monetary policy meeting" in testo and "non-monetary" not in testo and "Day 1" not in testo:
            quando = datetime.strptime(g + " 14:15", "%d/%m/%Y %H:%M").replace(tzinfo=ROMA)
            out.append(evento(quando, "EU", testo, ("Decisione sui tassi della BCE", "banca_centrale", True, "rate_ecb"), "BCE"))
    return out


def da_fed():
    html = scarica(FONTI["Fed"])
    out = []
    for anno in re.findall(r"(\d{4}) FOMC Meetings", html):
        inizio = html.find(f"{anno} FOMC Meetings")
        fine = html.find("FOMC Meetings", inizio + 20)
        blocco = html[inizio: fine if fine > 0 else None]
        for mese, giorni in re.findall(r'fomc-meeting__month[^>]*>\s*<strong>([^<]+)</strong>.*?fomc-meeting__date[^>]*>([^<]+)<', blocco, re.S):
            mesi = [m.strip() for m in mese.split("/")]
            gg = re.findall(r"\d+", giorni)
            if not gg or mesi[-1] not in MONTHS:
                continue
            m = MONTHS.index(mesi[-1] if len(mesi) > 1 and int(gg[-1]) < int(gg[0]) else mesi[0]) + 1
            quando = datetime(int(anno), m, int(gg[-1]), 14, 0, tzinfo=NY)
            out.append(evento(quando, "US", f"FOMC {mese} {giorni}".strip(),
                              ("Decisione sui tassi della Fed", "banca_centrale", True, "rate_fed"), "Fed"))
    return out


# ---------------------------------------------------------------- insieme

def ultimo_dato(serie_id, macro):
    s = macro.get(serie_id)
    if not s or s.get("valore") in (None, ""):
        return None
    return {"valore": float(s["valore"]), "periodo": s.get("data"), "nome": s.get("nome"),
            "unita": s.get("unita"), "fonte": s.get("fonte")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="site/data/calendario.json")
    a = ap.parse_args()
    oggi = datetime.now(ROMA).date()
    inizio, fine = oggi - timedelta(days=7), oggi + timedelta(days=60)

    eventi, esito = [], {}
    for nome, fn in [("Eurostat", lambda: da_eurostat(inizio, fine)), ("Istat", da_istat), ("BCE", da_bce),
                     ("Fed", da_fed), ("BLS", da_bls), ("BEA", da_bea)]:
        try:
            ev = [e for e in fn() if inizio <= datetime.fromisoformat(e["data"].replace("Z", "+00:00")).astimezone(ROMA).date() <= fine]
            eventi += ev
            esito[nome] = len(ev)
        except Exception as e:  # una fonte giù non ferma le altre
            esito[nome] = f"errore: {e}"
    print("  calendario:", esito)
    if sum(1 for v in esito.values() if isinstance(v, int) and v > 0) < 3:
        print("  calendario non aggiornato: troppe fonti senza risposta", file=sys.stderr)
        return

    try:
        macro = {m["id"]: m for m in json.loads((ROOT / "site" / "data" / "data.json").read_text())["macro"]}
    except Exception:
        macro = {}
    visti = set()
    finali = []
    for e in sorted(eventi, key=lambda x: (x["data"], x["paese"], x["nome"])):
        chiave = (e["data"][:10], e["paese"], e["nome"])
        if chiave in visti:
            continue
        visti.add(chiave)
        serie = e.pop("serie")
        e["ultimo"] = ultimo_dato(serie, macro) if serie else None
        finali.append(e)

    out = {
        "aggiornato": oggi.isoformat(),
        "automatico": True,
        "fonte": "Eurostat, Istat, Banca Centrale Europea, Federal Reserve, Bureau of Labor Statistics e Bureau of Economic Analysis",
        "fonti": FONTI,
        "paesi": PAESI,
        "famiglie": FAMIGLIE,
        "eventi": finali,
    }
    Path(a.out).write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
    print(f"  scritto {a.out}: {len(finali)} appuntamenti dal {inizio} al {fine}")


if __name__ == "__main__":
    main()
