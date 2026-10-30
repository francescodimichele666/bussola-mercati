"""
Elenco dei singoli titoli di Stato italiani in circolazione (BOT, BTP, CCTeu...).

Fonte: Ministero dell'Economia e delle Finanze, Dipartimento del Tesoro,
file pubblico "Scadenze suddivise per anno" (aggiornato ogni fine mese).
Il motore cerca sulla pagina del Ministero il file CSV più recente, lo legge
e scrive site/data/btp.json.

Se il sito del Ministero non risponde, il file già pubblicato resta com'è:
meglio un elenco di un mese fa, con la sua data, che una tabella vuota.

Uso:  python engine/btp.py --out site/data/btp.json
"""
import argparse
import csv
import io
import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

PAGINA = "https://www.dt.mef.gov.it/it/debito_pubblico/dati_statistici/scadenze_titoli_suddivise_anno/"
UA = {"User-Agent": "Mozilla/5.0 (BussolaMercati; +https://github.com/francescodimichele666/bussola-mercati)"}
MESI = {m: i for i, m in enumerate(
    "gennaio febbraio marzo aprile maggio giugno luglio agosto settembre ottobre novembre dicembre".split(), 1)}
ISIN = re.compile(r"^IT[0-9A-Z]{9}[0-9]$")

# Ordine importante: i nomi più specifici prima di "BTP".
FAMIGLIE = [
    ("BOT", "BOT"),
    ("BTP Italia", "BTP Italia"),
    ("BTP€i", "BTP€i"),
    ("BTP Valore", "BTP Valore"),
    ("BTP Più", "BTP Più"),
    ("BTP Futura", "BTP Futura"),
    ("BTP Green", "BTP Green"),
    ("CCTeu", "CCTeu"),
    ("BTP", "BTP"),
]


def scarica(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def file_piu_recente(html):
    """Tra i CSV linkati sulla pagina sceglie quello con la data più recente nel nome."""
    migliori = []
    for href in re.findall(r'href="([^"]+Scadenze[^"]+\.csv)"', html, re.I):
        m = re.search(r"al-(\d{1,2})-([a-z]+)-(\d{4})", href, re.I)
        if not m or m.group(2).lower() not in MESI:
            continue
        d = date(int(m.group(3)), MESI[m.group(2).lower()], int(m.group(1)))
        migliori.append((d, urllib.parse.urljoin(PAGINA, href)))
    if not migliori:
        raise RuntimeError("nessun file CSV trovato sulla pagina del Ministero")
    return max(migliori)


def famiglia(tipo):
    t = tipo.replace("€I", "€i").replace("GREEN", "Green")
    for prefisso, nome in FAMIGLIE:
        if t.startswith(prefisso):
            return nome
    return None


def numero_it(s):
    s = s.strip().replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def data_it(s):
    return datetime.strptime(s.strip(), "%d/%m/%Y").date()


def cedola(testo, fam):
    """Restituisce (valore, nota). Nessun valore se il Ministero non lo indica."""
    t = testo.replace('"', " ").strip()
    m = re.match(r"(-?\d+(?:,\d+)?)", t)
    if not m:
        return None, ""
    v = float(m.group(1).replace(",", "."))
    if fam == "CCTeu":
        return v, "spread"
    low = t.lower()
    if "reale" in low:
        return v, "reale"
    if "step" in low:
        return v, "step-up"
    return v, ""


def leggi(testo, oggi):
    righe = list(csv.reader(io.StringIO(testo), delimiter=";"))
    inizio = next(i for i, r in enumerate(righe) if r and r[0].strip() == "Codice ISIN")
    titoli = []
    for r in righe[inizio + 1:]:
        if len(r) > 5 and r[5].strip() == "Totale":
            break  # dopo il totale il file contiene altre tabelle (es. REPO)
        if len(r) < 8:
            continue
        isin, tipo = r[0].strip(), r[1].strip()
        fam = famiglia(tipo)
        if not ISIN.match(isin) or not fam or r[5].strip() != "EUR":
            continue
        scad = data_it(r[3])
        if scad < oggi:
            continue  # già rimborsato
        val, nota = cedola(r[4], fam)
        circ = numero_it(r[7])
        titoli.append({
            "isin": isin,
            "tipo": tipo.replace("€I", "€i").replace("GREEN", "Green"),
            "famiglia": fam,
            "emissione": data_it(r[2]).isoformat(),
            "scadenza": scad.isoformat(),
            "cedola": val,
            "nota": nota,
            "circolante_mld": round(circ / 1e9, 2) if circ else None,
        })
    titoli.sort(key=lambda x: (x["scadenza"], x["isin"]))
    return titoli


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="site/data/btp.json")
    ap.add_argument("--file", help="CSV già scaricato (per prove senza rete)")
    a = ap.parse_args()
    oggi = date.today()
    try:
        if a.file:
            raw, rif, url = Path(a.file).read_bytes(), None, PAGINA
        else:
            rif, url = file_piu_recente(scarica(PAGINA).decode("utf-8", "ignore"))
            raw = scarica(url)
        testo = raw.decode("cp1252")
        if rif is None:
            m = re.search(r"Aggiornamento al (\d{1,2}) ([a-z]+) (\d{4})", testo, re.I)
            rif = date(int(m.group(3)), MESI[m.group(2).lower()], int(m.group(1)))
        titoli = leggi(testo, oggi)
        if len(titoli) < 50:
            raise RuntimeError(f"solo {len(titoli)} titoli letti, il formato del file potrebbe essere cambiato")
    except Exception as e:  # il sito resta con l'ultimo elenco buono
        print(f"  BTP dal Ministero non aggiornati: {e}", file=sys.stderr)
        return
    out = {
        "riferimento": rif.isoformat(),
        "scaricato": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "fonte": "Ministero dell'Economia e delle Finanze, Dipartimento del Tesoro",
        "fonte_url": PAGINA,
        "file_url": url,
        "titoli": titoli,
    }
    Path(a.out).write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
    fam = {}
    for t in titoli:
        fam[t["famiglia"]] = fam.get(t["famiglia"], 0) + 1
    print(f"  scritto {a.out}: {len(titoli)} titoli al {rif} {fam}")


if __name__ == "__main__":
    main()
