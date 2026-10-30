"""Motore dati di Bussola dei Mercati.

Scarica dati reali da fonti pubbliche, calcola statistiche storiche e indicatori
e scrive un unico file JSON che il sito legge. Non inventa nulla: se una fonte
non risponde, il dato viene tenuto dall'ultimo aggiornamento riuscito e marcato
come "non aggiornato", oppure lasciato vuoto.

Uso:  python engine/build.py --out site/data/data.json
"""

import argparse
import io
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
UA = {"User-Agent": "Mozilla/5.0 (BussolaDeiMercati data bot)"}


def log(msg):
    print(msg, file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------
# Fonti dati (usate solo quando il motore gira online, es. su GitHub Actions)
# ---------------------------------------------------------------------------

def fetch_prices_yahoo(ticker, start):
    """Prezzi giornalieri rettificati (dividendi e cedole reinvestiti) -> fine mese."""
    import yfinance as yf
    hist = yf.Ticker(ticker).history(start=start, auto_adjust=True, actions=False)
    if hist is None or hist.empty:
        raise RuntimeError(f"nessun dato per {ticker}")
    s = hist["Close"].dropna()
    s.index = s.index.tz_localize(None)
    m = s.resample("ME").last().dropna()
    return [d.strftime("%Y-%m") for d in m.index], [round(float(v), 6) for v in m.values]


def fetch_first(tickers, start):
    """Prova i simboli in ordine e restituisce (simbolo usato, date, valori)."""
    last = None
    for t in tickers:
        try:
            d, v = fetch_prices_yahoo(t, start)
            if len(v) >= 24:
                return t, d, v
        except Exception as e:  # noqa: BLE001
            last = e
    raise RuntimeError(f"nessun simbolo ha risposto ({last})")


def fetch_aum_yahoo(ticker):
    """Patrimonio del fondo in miliardi di euro, solo se Yahoo lo dà in euro."""
    import yfinance as yf
    info = yf.Ticker(ticker).info or {}
    ta, cur = info.get("totalAssets"), info.get("currency")
    if isinstance(ta, (int, float)) and ta > 0 and cur == "EUR":
        return round(ta / 1e9, 3)
    return None


def fetch_fundamentals_yahoo(ticker):
    import yfinance as yf
    info = yf.Ticker(ticker).info or {}
    out = {}
    pe = info.get("trailingPE")
    if isinstance(pe, (int, float)) and 0 < pe < 200:
        out["pe"] = round(float(pe), 1)
    y = info.get("yield") or info.get("dividendYield")
    if isinstance(y, (int, float)) and 0 <= y < 1:
        out["yield"] = round(float(y) * 100, 2)
    return out


def _get(url):
    import requests
    r = requests.get(url, headers=UA, timeout=40)
    r.raise_for_status()
    return r


def fetch_fred(series_id):
    import pandas as pd
    r = _get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}")
    df = pd.read_csv(io.StringIO(r.text))
    df.columns = ["date", "value"]
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna()
    return [(str(d)[:10], float(v)) for d, v in zip(df["date"], df["value"])]


def fetch_ecb(flow, key):
    import pandas as pd
    url = f"https://data-api.ecb.europa.eu/service/data/{flow}/{key}?format=csvdata&startPeriod=2015-01"
    df = pd.read_csv(io.StringIO(_get(url).text))
    df = df[["TIME_PERIOD", "OBS_VALUE"]].dropna()
    return [(str(d), float(v)) for d, v in zip(df["TIME_PERIOD"], df["OBS_VALUE"])]


def fetch_eurostat(dataset, since="2015-01", **params):
    """Serie Eurostat (formato JSON-stat). Mesi come AAAA-MM, trimestri come AAAA-T#.
    L'API accetta solo lang EN, FR o DE; per i dati trimestrali `since` va scritto come 2015-Q1."""
    import re
    import requests
    q = {"format": "JSON", "lang": "EN", "sinceTimePeriod": since}
    q.update(params)
    url = f"https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/{dataset}"
    r = requests.get(url, params=q, headers=UA, timeout=60)
    r.raise_for_status()
    js = r.json()
    times = js["dimension"]["time"]["category"]["index"]
    values = js.get("value", {})
    rows = []
    for label, pos in sorted(times.items(), key=lambda kv: kv[1]):
        v = values.get(str(pos))
        if v is None:
            continue
        m = re.match(r"^(\d{4})-?M?(\d{2})$", label)
        qm = re.match(r"^(\d{4})-?Q(\d)$", label)
        if qm:
            label = f"{qm.group(1)}-T{qm.group(2)}"
        elif m:
            label = f"{m.group(1)}-{m.group(2)}"
        rows.append((label, float(v)))
    if not rows:
        raise RuntimeError(f"Eurostat {dataset}: nessun dato")
    return rows


def fetch_worldbank(country, indicator):
    url = f"https://api.worldbank.org/v2/country/{country}/indicator/{indicator}?format=json&per_page=60"
    data = _get(url).json()
    rows = [(x["date"], float(x["value"])) for x in data[1] if x.get("value") is not None]
    return sorted(rows)


def fetch_gpr():
    """Indice di rischio geopolitico (Caldara & Iacoviello, Federal Reserve Board)."""
    import pandas as pd
    r = _get("https://www.matteoiacoviello.com/gpr_files/data_gpr_export.xls")
    df = pd.read_excel(io.BytesIO(r.content))
    cols = {c.lower(): c for c in df.columns}
    month_col, gpr_col = cols.get("month"), cols.get("gpr")
    if not month_col or not gpr_col:
        raise RuntimeError("colonne GPR non trovate")
    df = df[[month_col, gpr_col]].dropna()
    return [(pd.Timestamp(d).strftime("%Y-%m"), float(v)) for d, v in zip(df[month_col], df[gpr_col])]


def yoy(rows):
    """Variazione % su 12 mesi da una serie mensile di livelli (es. indice prezzi)."""
    out = []
    for i in range(12, len(rows)):
        prev = rows[i - 12][1]
        if prev:
            out.append((rows[i][0], (rows[i][1] / prev - 1) * 100))
    return out


# Indicatori macro, di mercato e geopolitici. Ogni voce dice da dove arriva.
# Paesi europei confrontati nel sito: Italia, Germania, Francia, Spagna e area euro.
PAESI = [("IT", "Italia", "IT"), ("DE", "Germania", "DE"), ("FR", "Francia", "FR"), ("ES", "Spagna", "ES"), ("EA", "Area euro", "U2")]
BCE, ESTAT = "Banca Centrale Europea", "Eurostat"
BCE_URL, ESTAT_URL = "https://data.ecb.europa.eu/", "https://ec.europa.eu/eurostat/"


def _eu_sources():
    out = []
    for code, name, ecb in PAESI:
        geo = "EA20" if code == "EA" else code
        # Da gennaio 2026 l'inflazione armonizzata usa la classificazione ECOICOP 2 (dataset prc_hicp_minr);
        # la vecchia serie BCE ICP ...000000.4.ANR si è fermata a dicembre 2025.
        out.append((f"infl_{code}", f"Inflazione {name}", "%", ESTAT, ESTAT_URL,
                    lambda g=("EA" if code == "EA" else code): fetch_eurostat("prc_hicp_minr", geo=g, unit="RCH_A", coicop18="TOTAL")))
        out.append((f"disocc_{code}", f"Disoccupazione {name}", "%", ESTAT, ESTAT_URL,
                    lambda g=geo: fetch_eurostat("une_rt_m", geo=g, age="TOTAL", sex="T", s_adj="SA", unit="PC_ACT")))
        out.append((f"pil_{code}", f"Crescita PIL {name} (su anno prima)", "%", ESTAT, ESTAT_URL,
                    lambda g=geo: fetch_eurostat("namq_10_gdp", since="2015-Q1", geo=g, unit="CLV_PCH_SM", s_adj="SCA", na_item="B1GQ")))
        if code != "EA":
            out.append((f"y10_{code}", f"Rendimento titoli di Stato 10 anni {name}", "%", BCE, BCE_URL,
                        lambda c=code: fetch_ecb("IRS", f"M.{c}.L.L40.CI.0000.EUR.N.Z")))
    return out


MACRO_SOURCES = _eu_sources() + [
    ("rate_ecb", "Tasso BCE (rifinanziamento)", "%", BCE, BCE_URL, lambda: fetch_ecb("FM", "B.U2.EUR.4F.KR.MRR_FR.LEV")),
    ("hy_spread_eu", "Spread obbligazioni high yield in euro", "%", "FRED, St. Louis Fed (dati ICE BofA)", "https://fred.stlouisfed.org/series/BAMLHE00EHYIOAS", lambda: fetch_fred("BAMLHE00EHYIOAS")),
    # Dal mondo
    ("infl_us",  "Inflazione USA",              "%",  "FRED, St. Louis Fed",    "https://fred.stlouisfed.org/series/CPIAUCSL", lambda: yoy(fetch_fred("CPIAUCSL"))),
    ("rate_fed", "Tasso Fed (limite superiore)","%",  "FRED, St. Louis Fed",    "https://fred.stlouisfed.org/series/DFEDTARU", lambda: fetch_fred("DFEDTARU")),
    ("y10_us",   "Rendimento Treasury 10 anni", "%",  "FRED, St. Louis Fed",    "https://fred.stlouisfed.org/series/DGS10", lambda: fetch_fred("DGS10")),
    ("y2_us",    "Rendimento Treasury 2 anni",  "%",  "FRED, St. Louis Fed",    "https://fred.stlouisfed.org/series/DGS2", lambda: fetch_fred("DGS2")),
    ("vix",      "Volatilità attesa S&P 500 (VIX)", "pt", "FRED, St. Louis Fed (dati CBOE)", "https://fred.stlouisfed.org/series/VIXCLS", lambda: fetch_fred("VIXCLS")),
    ("gdp_us",   "Crescita PIL USA (annua)",    "%",  "Banca Mondiale",         "https://data.worldbank.org/", lambda: fetch_worldbank("USA", "NY.GDP.MKTP.KD.ZG")),
    ("gdp_cn",   "Crescita PIL Cina (annua)",   "%",  "Banca Mondiale",         "https://data.worldbank.org/", lambda: fetch_worldbank("CHN", "NY.GDP.MKTP.KD.ZG")),
    ("gpr",      "Indice di rischio geopolitico (GPR)", "pt", "Caldara & Iacoviello (Federal Reserve Board)", "https://www.matteoiacoviello.com/gpr.htm", fetch_gpr),
]


# ---------------------------------------------------------------------------
# Calcoli (puri: non usano internet, così si possono verificare)
# ---------------------------------------------------------------------------

def _std(xs):
    if len(xs) < 2:
        return None
    m = sum(xs) / len(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def _ann_return(p, months):
    if len(p) <= months or p[-1 - months] <= 0:
        return None
    return (p[-1] / p[-1 - months]) ** (12 / months) - 1


def _max_drawdown(p):
    peak, mdd = p[0], 0.0
    for v in p:
        peak = max(peak, v)
        mdd = min(mdd, v / peak - 1)
    return mdd


def _rsi(p, n=14):
    if len(p) <= n:
        return None
    gains, losses = [], []
    for a, b in zip(p[:-1], p[1:]):
        d = b - a
        gains.append(max(d, 0))
        losses.append(max(-d, 0))
    ag, al = sum(gains[:n]) / n, sum(losses[:n]) / n
    for g, l in zip(gains[n:], losses[n:]):
        ag, al = (ag * (n - 1) + g) / n, (al * (n - 1) + l) / n
    if al == 0:
        return 100.0
    return 100 - 100 / (1 + ag / al)


# Classi di volatilità della scala 1-7 del Regolamento UE PRIIPs (rischio di mercato).
VOL_CLASSES = [(0.005, 1), (0.05, 2), (0.12, 3), (0.20, 4), (0.30, 5), (0.80, 6)]


def vol_class(vol):
    if vol is None:
        return None
    for limit, cls in VOL_CLASSES:
        if vol < limit:
            return cls
    return 7


def to_eur(dates, values, fx_dates, fx_values, currency):
    if currency == "EUR":
        return dates, values
    fx = dict(zip(fx_dates, fx_values))
    d_out, v_out = [], []
    for d, v in zip(dates, values):
        if d in fx and fx[d]:
            d_out.append(d)
            v_out.append(v / fx[d])
    return d_out, v_out


def r(x, nd=4):
    return None if x is None else round(x, nd)


def compute_category(cfg, dates, eur):
    p = eur
    rets = [b / a - 1 for a, b in zip(p[:-1], p[1:])]
    rolling12 = [p[i] / p[i - 12] - 1 for i in range(12, len(p))]
    vol_all = _std(rets) * math.sqrt(12) if len(rets) > 2 else None
    vol_5y = _std(rets[-60:]) * math.sqrt(12) if len(rets) >= 36 else vol_all
    sma10 = sum(p[-10:]) / 10 if len(p) >= 10 else None
    years = (len(p) - 1) / 12
    stats = {
        "anni_storia": round(years, 1),
        "rend_1a": r(_ann_return(p, 12)),
        "rend_3a": r(_ann_return(p, 36)),
        "rend_5a": r(_ann_return(p, 60)),
        "rend_10a": r(_ann_return(p, 120)),
        "rend_tutto": r((p[-1] / p[0]) ** (1 / years) - 1) if years >= 1 else None,
        "vol": r(vol_all),
        "vol_5a": r(vol_5y),
        "max_ribasso": r(_max_drawdown(p)),
        "miglior_12m": r(max(rolling12)) if rolling12 else None,
        "peggior_12m": r(min(rolling12)) if rolling12 else None,
        "mesi_positivi": r(sum(1 for x in rets if x > 0) / len(rets)) if rets else None,
        "anni_in_perdita": r(sum(1 for x in rolling12 if x < 0) / len(rolling12)) if rolling12 else None,
    }
    tech = {
        "media_10m": r(sma10, 6),
        "sopra_media": None if sma10 is None else p[-1] > sma10,
        "momento_12m": r(_ann_return(p, 12)),
        "rsi_14m": r(_rsi(p), 1),
        "dal_massimo": r(p[-1] / max(p) - 1),
    }
    return {
        "id": cfg["id"], "nome": cfg["nome"], "gruppo": cfg["gruppo"], "paese": cfg.get("paese"),
        "ticker": cfg.get("ticker") or cfg["tickers"][0], "proxy": cfg["proxy"], "nota": cfg["nota"],
        "prodotti": sorted(cfg.get("prodotti", []), key=lambda x: -(x.get("aum") or 0)),
        "classe_rischio": vol_class(vol_5y),
        "date": dates, "eur": [round(v, 4) for v in p],
        "statistiche": stats, "tecnica": tech,
    }


def summarize_macro(sid, label, unit, source, url, rows, stale=False):
    if not rows:
        return None
    hist = [v for _, v in rows]
    item = {
        "id": sid, "nome": label, "unita": unit, "fonte": source, "url": url,
        "valore": round(rows[-1][1], 3), "data": rows[-1][0],
        "precedente": round(rows[-2][1], 3) if len(rows) > 1 else None,
        "storico": [[d, round(v, 3)] for d, v in rows[-36:]],
    }
    if sid in ("gpr", "vix") and len(hist) > 24:
        item["media_storica"] = round(sum(hist) / len(hist), 2)
        item["percentile"] = round(sum(1 for v in hist if v <= hist[-1]) / len(hist) * 100)
    if stale:
        item["non_aggiornato"] = True
    return item


def build_payload(config, prices, fx, macro, fundamentals=None, preview=False, notes=None):
    """prices: {id: (dates, values in valuta originale)}; fx: (dates, eurusd); macro: list."""
    cats = []
    for cfg in config["categorie"]:
        if cfg["id"] not in prices:
            continue
        d, v = prices[cfg["id"]]
        d, eur = to_eur(d, v, fx[0], fx[1], cfg["valuta"])
        if len(eur) < 24:
            continue
        c = compute_category(cfg, d, eur)
        if fundamentals and cfg["id"] in fundamentals:
            c["fondamentali"] = fundamentals[cfg["id"]]
        cats.append(c)
    return {
        "generato_il": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "anteprima": preview,
        "note": notes or [],
        "valuta": "EUR",
        "prodotti_aggiornati_al": config.get("prodotti_aggiornati_al"),
        "prodotti_fonte": config.get("prodotti_fonte"),
        "categorie": cats,
        "macro": [m for m in macro if m],
    }


# ---------------------------------------------------------------------------
# Esecuzione online
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE.parent / "site" / "data" / "data.json"))
    args = ap.parse_args()
    out = Path(args.out)
    config = json.loads((HERE / "config.json").read_text(encoding="utf-8"))
    previous = {}
    if out.exists():
        try:
            previous = json.loads(out.read_text(encoding="utf-8"))
        except ValueError:
            previous = {}
    if previous.get("anteprima"):
        previous = {}  # i dati di anteprima non sono rettificati: non riusarli
    prev_macro = {m["id"]: m for m in previous.get("macro", [])}
    notes, errors = [], 0

    fx = ([], [])
    if any(c["valuta"] != "EUR" for c in config["categorie"]):
        try:
            fx = fetch_prices_yahoo(config["cambio_eurusd"], config["storia_dal"])
        except Exception as e:  # noqa: BLE001
            log(f"ERR cambio EUR/USD: {e}. Tengo il file precedente.")
            sys.exit(1)
    prices, fundamentals, reused = {}, {}, set()
    for cfg in config["categorie"]:
        try:
            used, d, v = fetch_first(cfg["tickers"], config["storia_dal"])
            cfg["ticker"] = used
            prices[cfg["id"]] = (d, v)
            log(f"ok  prezzi {used}: {len(d)} mesi")
        except Exception as e:  # noqa: BLE001
            errors += 1
            log(f"ERR prezzi {cfg['tickers']}: {e}")
            notes.append(f"Prezzi di {cfg['nome']} non aggiornati in questo giro.")
            old = next((c for c in previous.get("categorie", []) if c["id"] == cfg["id"]), None)
            if old:  # riusa la serie in euro già salvata
                prices[cfg["id"]] = (old["date"], old["eur"])
                reused.add(cfg["id"])
        for prod in cfg.get("prodotti", []):
            if not prod.get("yahoo"):
                continue
            try:
                a = fetch_aum_yahoo(prod["yahoo"])
                if a:
                    prod["aum"], prod["aum_live"] = a, True
            except Exception as e:  # noqa: BLE001
                log(f"--  patrimonio {prod['yahoo']}: {e}")
        if cfg["gruppo"] in ("Azioni", "Immobiliare", "Obbligazioni") and cfg["id"] in prices:
            try:
                f = fetch_fundamentals_yahoo(cfg.get("ticker") or cfg["tickers"][0])
                if f:
                    fundamentals[cfg["id"]] = f
            except Exception as e:  # noqa: BLE001
                log(f"--  fondamentali {cfg['id']}: {e}")

    macro = []
    for sid, label, unit, source, url, fn in MACRO_SOURCES:
        try:
            macro.append(summarize_macro(sid, label, unit, source, url, fn()))
            log(f"ok  macro {sid}")
        except Exception as e:  # noqa: BLE001
            errors += 1
            log(f"ERR macro {sid}: {e}")
            if sid in prev_macro:
                macro.append(dict(prev_macro[sid], non_aggiornato=True))

    # Le serie riusate dal giro precedente sono già in euro.
    for cfg in config["categorie"]:
        if cfg["id"] in reused:
            cfg["valuta"] = "EUR"

    payload = build_payload(config, prices, fx, macro, fundamentals, preview=False, notes=notes)
    if not payload["categorie"]:
        log("Nessuna categoria calcolata: non sovrascrivo il file precedente.")
        sys.exit(1)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    log(f"Scritto {out} ({len(payload['categorie'])} categorie, {len(payload['macro'])} indicatori, {errors} errori)")


if __name__ == "__main__":
    main()
