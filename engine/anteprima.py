"""Costruisce i dati dell'ANTEPRIMA del sito.

Usa prezzi mensili reali scaricati da TradingView il 30/10/2026 (cartella
anteprima_raw_eu/, da ottobre 2015 o dalla prima quotazione disponibile) e
indicatori macro della stessa fonte (macro_eu.json). Differenza importante
rispetto al motore online: questi prezzi NON includono dividendi e cedole dei
fondi a distribuzione, quindi per BTP, immobiliare e Spagna (indice di prezzo)
i rendimenti risultano più bassi del vero. Il motore online (build.py) usa
prezzi rettificati. Serve solo per mostrare il sito prima del primo
aggiornamento automatico.
"""

import json
from pathlib import Path

from build import build_payload, summarize_macro, PAESI

HERE = Path(__file__).resolve().parent
RAW = HERE / "anteprima_raw_eu"
TV = "TradingView (anteprima)"
TV_URL = "https://www.tradingview.com/"

# id categoria -> (file, primo mese disponibile)
FILES = {
    "az_italia": ("SXRY", "2015-10"), "az_germania": ("EXS1", "2015-10"),
    "az_francia": ("PX1GR", "2015-10"), "az_spagna": ("IY", "2015-10"),
    "az_eurozona": ("SXRT", "2015-10"), "az_europa": ("EUNK", "2015-10"),
    "az_mondo": ("EUNL", "2015-10"), "az_usa": ("SXR8", "2015-10"),
    "az_emergenti": ("IS3N", "2015-10"), "ob_monetario": ("XEON", "2022-11"),
    "ob_stato_ea": ("XGLE", "2022-11"), "ob_btp": ("IS0M", "2015-10"),
    "ob_corporate": ("D5BG", "2015-10"), "ob_highyield": ("XHYA", "2017-03"),
    "mp_oro": ("4GLD", "2015-10"), "im_europa": ("IQQP", "2015-10"),
    "cr_bitcoin": ("BTCEUR", "2015-10"),
}
# Nell'anteprima Francia e Spagna sono misurate con l'indice, non con l'ETF.
PREVIEW_PROXY = {
    "az_francia": ("CAC 40 Gross Return (indice con dividendi)", "PX1GR"),
    "az_spagna": ("IBEX 35 (indice di solo prezzo)", "IBEX"),
}


def months(start, n):
    y, m = map(int, start.split("-"))
    out = []
    for _ in range(n):
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def read(name):
    return [float(x) for x in (RAW / f"{name}.txt").read_text().strip().split(",")]


def main():
    config = json.loads((HERE / "config.json").read_text(encoding="utf-8"))
    for c in config["categorie"]:
        c["ticker"] = c["tickers"][0]
        if c["id"] in PREVIEW_PROXY:
            c["proxy"], c["ticker"] = PREVIEW_PROXY[c["id"]]
    prices = {}
    for cid, (f, start) in FILES.items():
        v = read(f)
        prices[cid] = (months(start, len(v)), v)

    eu = json.loads((RAW / "macro_eu.json").read_text())

    def m(sid, label, unit, rows):
        return summarize_macro(sid, label, unit, TV, TV_URL, [tuple(x) for x in rows])

    macro = []
    for code, name, _ in PAESI:
        macro.append(m(f"infl_{code}", f"Inflazione {name}", "%", eu["infl"][code]))
        macro.append(m(f"disocc_{code}", f"Disoccupazione {name}", "%", eu["disocc"][code]))
        macro.append(m(f"pil_{code}", f"Crescita PIL {name} (su anno prima)", "%", eu["pil"][code]))
        if code in eu["y10"]:
            rows = [list(x) for x in eu["y10"][code]]
            rows[-1][0] = "2026-10-30"
            macro.append(m(f"y10_{code}", f"Rendimento titoli di Stato 10 anni {name}", "%", rows))
    macro += [
        m("rate_ecb", "Tasso BCE (rifinanziamento)", "%", [("2026-06", 2.4), ("2026-09", 2.65), ("2026-10", 2.65)]),
        m("infl_us", "Inflazione USA", "%", [("2026-06", 3.5), ("2026-07", 3.4), ("2026-08", 3.4), ("2026-09", 3.7)]),
        m("rate_fed", "Tasso Fed", "%", [("2026-08", 3.75), ("2026-09", 4.0), ("2026-10", 4.0)]),
        m("y10_us", "Rendimento Treasury 10 anni", "%", [("2026-10-30", 4.925)]),
        m("y2_us", "Rendimento Treasury 2 anni", "%", [("2026-10-30", 4.585)]),
        m("vix", "Volatilità attesa S&P 500 (VIX)", "pt", [("2026-10-30", 18.13)]),
        m("gdp_us", "Crescita PIL USA (su anno prima)", "%", [("2026-T2", 2.2), ("2026-T3", 3.4)]),
    ]
    notes = [
        "Anteprima con prezzi reali di borsa (TradingView) da ottobre 2015. Per i fondi a distribuzione "
        "(BTP, immobiliare) e per l'indice spagnolo cedole e dividendi non sono inclusi, quindi i rendimenti sono più bassi del vero. "
        "Il sito online userà prezzi con dividendi reinvestiti e dati di BCE ed Eurostat.",
        "Monetario e titoli di Stato area euro hanno qui solo 4 anni di storia. Rischio geopolitico, spread high yield e crescita della Cina arrivano con il primo aggiornamento automatico.",
    ]
    payload = build_payload(config, prices, ([], []), macro, preview=True, notes=notes)
    out = HERE.parent / "site" / "data" / "data.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    for c in payload["categorie"]:
        s = c["statistiche"]
        print(f"{c['id']:14s} r{c['classe_rischio']} 1a {s['rend_1a']} 5a {s['rend_5a']} vol5 {s['vol_5a']} dd {s['max_ribasso']} perd12 {s['anni_in_perdita']}")
    print(len(payload["macro"]), "indicatori;", out.stat().st_size, "byte")


if __name__ == "__main__":
    main()
