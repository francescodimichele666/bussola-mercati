"""
Prepara i dati delle tre pagine: Titoli di Stato, ETF del mondo, Calendario economico.

Legge i file grezzi in engine/anteprima_raw_pagine/ (scaricati da TradingView)
e scrive in site/data/:
  titoli.json      rendimenti dei titoli di riferimento per Paese e scadenza
  etf.json         ETF quotati su Xetra (UCITS, in euro) e negli USA
  calendario.json  appuntamenti economici con spiegazione in italiano

Nessun numero viene inventato: se un campo manca resta vuoto.
Le spiegazioni sono descrizioni generali di come il mercato legge di solito
un dato, non previsioni né consigli.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "engine" / "anteprima_raw_pagine"
OUT = ROOT / "site" / "data"

# ---------------------------------------------------------------- titoli

NOMI_PAESI = {
    "IT": "Italia", "DE": "Germania", "FR": "Francia", "ES": "Spagna",
    "PT": "Portogallo", "GR": "Grecia", "NL": "Paesi Bassi", "BE": "Belgio",
    "AT": "Austria", "IE": "Irlanda", "FI": "Finlandia", "GB": "Regno Unito",
    "US": "Stati Uniti", "JP": "Giappone", "CH": "Svizzera",
}
VALUTA_PAESE = {"GB": "GBP", "US": "USD", "JP": "JPY", "CH": "CHF"}
NOME_TITOLO = {"IT": "BTP", "DE": "Bund", "FR": "OAT", "ES": "Bonos",
               "GB": "Gilt", "US": "Treasury", "JP": "JGB"}


def build_titoli():
    raw = json.loads((RAW / "titoli_tv.json").read_text())
    paesi = []
    for code, rows in raw["paesi"].items():
        paesi.append({
            "codice": code,
            "nome": NOMI_PAESI.get(code, code),
            "valuta": VALUTA_PAESE.get(code, "EUR"),
            "titolo": NOME_TITOLO.get(code, "Titolo di Stato"),
            "curva": sorted(rows, key=lambda r: r["scadenza_anni"]),
        })
    return {"aggiornato": raw["aggiornato"], "ora": raw.get("ora"), "fonte": raw["fonte"], "paesi": paesi}


# ---------------------------------------------------------------- ETF

CLASSE = {
    "c05f85d35d1cd0be6ebb2af4be16e06a": "Azioni",
    "b6e443a6c4a8a2e7918c5dbf3d45c796": "Obbligazioni",
    "8fe80395f389e29e3ea42210337f0350": "Materie prime",
    "1af0389838508d7016a9841eb6273962": "Cripto",
    "b090e99b8d95f5837ec178c2d3d3fc50": "Bilanciati",
}
AREA = {
    "460491fc520f4dbfcff22d1a45f6b056": "Stati Uniti",
    "176a9161fef684328415321c640ada1a": "Paesi sviluppati",
    "9c70933aff6b2a6d08c687a6cbb6b765": "Globale",
    "cb2afe0cf8f6511856c8a73ea8de821e": "Mondo esclusi USA",
    "55a6587f79a2d84489e92e46d0a83f09": "Emergenti",
    "7612e84033b6f5f1a8b8039d9e25d9b5": "Europa",
    "2402e241d9f16aa08de32421e0fa211f": "Asia e Giappone",
    "a48e5d3946d87117fc67cd7de5f2c02a": "America Latina",
}
FOCUS = {
    "52": "Mercato ampio", "53": "Grandi società", "55": "Piccole società",
    "56": "Medie società", "58": "Temi e ESG", "63": "Tecnologia",
    "64": "Dividendi", "54": "Finanza", "61": "Industria e difesa",
    "68": "Salute", "59": "Energia", "62": "Immobiliare", "70": "Servizi pubblici",
    "106": "Beni di consumo", "2127": "Comunicazioni", "115": "Miniere",
    "73": "Obbligazioni", "78": "Alto rendimento", "2025": "Monetari e altri",
    "29": "Oro", "32": "Argento", "25": "Rame", "20": "Petrolio",
    "10": "Paniere materie prime", "102": "Paniere materie prime",
    "2111": "Bitcoin", "9": "Bilanciato",
}
POLITICA = {"Capitalizes": "Accumulo", "Distributes": "Distribuzione"}


def _etf_rows(rows, mercato, fx):
    out, seen = [], set()
    for r in rows:
        if not r.get("aum") or not r.get("description"):
            continue
        # la stessa quota quotata due volte ha lo stesso patrimonio: la teniamo una volta
        key = (round(r["aum"], -5), r["description"])
        if key in seen:
            continue
        seen.add(key)
        aum_eur = r["aum"] / fx
        exch, tick = r["symbol"].split(":", 1)
        out.append({
            "ticker": tick,
            "borsa": exch,
            "nome": re.sub(r"\s+", " ", r["description"]).strip(),
            "emittente": r.get("brand"),
            "indice": r.get("index_tracked") if r.get("index_tracked") not in (None, "No Underlying Index") else None,
            "classe": CLASSE.get(r.get("asset_class"), "Altro"),
            "area": AREA.get(r.get("holdings_region"), "Altro"),
            "tema": FOCUS.get(r.get("focus")),
            "ter": round(r["expense_ratio"], 2) if r.get("expense_ratio") is not None else None,
            "aum_mld_eur": round(aum_eur / 1e9, 2),
            "rend_1a": round(r["nav_total_return.1Y"], 1) if r.get("nav_total_return.1Y") is not None else None,
            "rend_5a": round(r["nav_total_return.5Y"], 1) if r.get("nav_total_return.5Y") is not None else None,
            "politica": POLITICA.get(r.get("dividend_treatment")),
            "mercato": mercato,
            "ucits": mercato == "Europa",
        })
    return out


def build_etf():
    fx = json.loads((RAW / "cambi_tv.json").read_text())
    xetra = json.loads((RAW / "etf_xetra_tv.json").read_text())
    usa = json.loads((RAW / "etf_usa_tv.json").read_text())
    rows = _etf_rows(xetra, "Europa", 1.0) + _etf_rows(usa, "USA", fx["EURUSD"])
    rows.sort(key=lambda r: -r["aum_mld_eur"])
    return {
        "aggiornato": fx["data"],
        "fonte": "TradingView (dati di borsa Xetra, NYSE, Nasdaq)",
        "cambio": {"EURUSD": fx["EURUSD"], "data": fx["data"]},
        "nota_rendimenti": "Rendimento totale sul valore della quota (NAV), nella valuta del fondo, dividendi inclusi.",
        "etf": rows,
    }


# ---------------------------------------------------------------- calendario

MESI = {"Jan": "gen", "Feb": "feb", "Mar": "mar", "Apr": "apr", "May": "mag", "Jun": "giu",
        "Jul": "lug", "Aug": "ago", "Sep": "set", "Oct": "ott", "Nov": "nov", "Dec": "dic"}
PAESI_CAL = {"IT": "Italia", "EU": "Area euro", "DE": "Germania", "FR": "Francia",
             "ES": "Spagna", "US": "Stati Uniti"}

# Famiglie: cosa misura il dato e come viene letto di solito. Linguaggio prudente.
FAMIGLIE = {
    "inflazione": {
        "nome": "Inflazione",
        "cosa": "Di quanto sono saliti i prezzi al consumo, rispetto a un anno prima o al mese prima.",
        "lettura": "Se esce più alta delle attese, di solito il mercato pensa che la banca centrale terrà i tassi alti più a lungo: i rendimenti dei titoli di Stato tendono a salire, le obbligazioni già in circolazione perdono un po' di valore e le borse possono soffrire. Un dato più basso delle attese in genere ha l'effetto opposto.",
    },
    "inflazione_core": {
        "nome": "Inflazione di fondo",
        "cosa": "L'inflazione senza energia e alimentari freschi, i prezzi che cambiano di più da un mese all'altro. Mostra la tendenza di fondo.",
        "lettura": "Le banche centrali la guardano con molta attenzione. Una sorpresa al rialzo di solito spinge su i rendimenti e rafforza la valuta; una sorpresa al ribasso tende a fare il contrario.",
    },
    "prezzi_imprese": {
        "nome": "Prezzi alla produzione",
        "cosa": "I prezzi che le imprese pagano o praticano tra loro, prima che i beni arrivino al consumatore.",
        "lettura": "Spesso anticipano di qualche mese i prezzi al consumo. Di solito muovono il mercato meno dell'inflazione, ma una sorpresa ampia può far salire o scendere i rendimenti.",
    },
    "banca_centrale": {
        "nome": "Banca centrale",
        "cosa": "La decisione sul costo del denaro, il comunicato che la spiega e la conferenza stampa che segue.",
        "lettura": "Il mercato si muove soprattutto se la decisione è diversa da quella attesa. Se è in linea, conta di più cosa viene detto sulle prossime mosse. Tassi più alti di solito rafforzano la valuta e pesano su obbligazioni e borse; tassi più bassi tendono a fare il contrario.",
    },
    "discorso": {
        "nome": "Discorso",
        "cosa": "Un intervento pubblico di un membro della banca centrale.",
        "lettura": "Non ci sono numeri, ma le parole possono cambiare le attese sui tassi futuri. Per questo a volte muovono valuta e rendimenti, soprattutto se chi parla è il presidente.",
    },
    "pil": {
        "nome": "Crescita dell'economia",
        "cosa": "Quanto è cresciuto il prodotto interno lordo, cioè il valore di tutto ciò che il Paese produce.",
        "lettura": "Una crescita più forte delle attese di solito sostiene le borse, ma può far salire i rendimenti. Un dato debole tende a fare l'opposto e aumenta i timori di recessione. La prima stima viene spesso corretta nei mesi successivi.",
    },
    "stima_pil": {
        "nome": "Stima in tempo reale",
        "cosa": "La stima della crescita americana calcolata dalla Fed di Atlanta con i dati man mano disponibili. Non è il dato ufficiale.",
        "lettura": "Si aggiorna più volte al mese. Di solito ha un effetto limitato sui mercati, ma aiuta a capire che cosa aspettarsi dal dato ufficiale.",
    },
    "lavoro": {
        "nome": "Lavoro",
        "cosa": "Quante persone lavorano, quante cercano lavoro, quanti posti si creano.",
        "lettura": "Un mercato del lavoro forte di solito significa più consumi, ma anche più pressione su salari e prezzi. Negli Stati Uniti il dato mensile sugli occupati (Non Farm Payrolls) è tra i più seguiti al mondo e può muovere molto dollaro, titoli di Stato e borse.",
    },
    "salari": {
        "nome": "Salari e costo del lavoro",
        "cosa": "Quanto crescono le paghe e il costo del lavoro per le imprese.",
        "lettura": "Salari che crescono in fretta possono alimentare l'inflazione. Per questo una sorpresa al rialzo di solito fa salire i rendimenti.",
    },
    "fiducia": {
        "nome": "Fiducia",
        "cosa": "Sondaggi che chiedono a famiglie o imprese come vedono la situazione e i prossimi mesi.",
        "lettura": "Anticipano i comportamenti di spesa e di investimento. In genere l'effetto sul mercato è limitato, salvo sorprese ampie.",
    },
    "pmi": {
        "nome": "Indice dei direttori acquisti",
        "cosa": "Un sondaggio tra i responsabili acquisti delle aziende. Sopra 50 indica attività in crescita, sotto 50 in calo.",
        "lettura": "È tra i primi dati disponibili di ogni mese e per questo è molto seguito. Un dato sopra le attese di solito sostiene le borse e la valuta del Paese.",
    },
    "attivita_regionale": {
        "nome": "Attività regionale",
        "cosa": "Indici sull'attività economica in una singola zona degli Stati Uniti. Lo zero indica la media.",
        "lettura": "Di solito hanno un effetto modesto: servono come anticipo dei dati nazionali.",
    },
    "produzione": {
        "nome": "Produzione e ordini",
        "cosa": "Quanto producono le fabbriche e quanti ordini ricevono.",
        "lettura": "Dati più forti delle attese indicano un'industria in salute e in genere sostengono le borse. L'effetto è di solito moderato.",
    },
    "consumi": {
        "nome": "Consumi e redditi",
        "cosa": "Quanto spendono e quanto guadagnano le famiglie.",
        "lettura": "I consumi sono la parte più grande dell'economia. Una spesa più forte delle attese di solito sostiene le borse, ma può far salire i rendimenti.",
    },
    "casa": {
        "nome": "Casa",
        "cosa": "Compravendite, permessi di costruzione, prezzi delle case e tassi sui mutui.",
        "lettura": "Il settore immobiliare reagisce presto ai tassi d'interesse. Di solito l'effetto sui mercati è modesto, salvo variazioni ampie.",
    },
    "commercio": {
        "nome": "Commercio estero",
        "cosa": "Differenza tra quanto un Paese vende all'estero e quanto compra.",
        "lettura": "In genere ha poco effetto sulle borse; può influire sulla valuta del Paese.",
    },
    "energia": {
        "nome": "Petrolio",
        "cosa": "Variazione settimanale delle scorte di greggio e benzina negli Stati Uniti, o stime sul mercato dell'energia.",
        "lettura": "Scorte in calo più delle attese di solito spingono in su il prezzo del petrolio, e viceversa. Conta per l'inflazione e per le società energetiche.",
    },
    "conti_pubblici": {
        "nome": "Conti pubblici",
        "cosa": "Il saldo tra entrate e spese dello Stato nel mese.",
        "lettura": "Deficit più ampi significano più titoli di Stato da emettere. Di solito l'effetto immediato è piccolo.",
    },
    "politica": {
        "nome": "Politica",
        "cosa": "Un appuntamento politico, come un'elezione.",
        "lettura": "Può portare oscillazioni perché cambia le attese su tasse, spesa pubblica e regole. L'effetto dipende dal risultato e da quanto era atteso.",
    },
}

# (regex sul titolo, nome italiano, famiglia). Il primo che corrisponde vince.
REGOLE = [
    (r"^Core PCE", "Inflazione PCE di fondo, mese su mese", "inflazione_core"),
    (r"^PCE Price Index YoY", "Inflazione PCE, anno su anno", "inflazione"),
    (r"^PCE Price Index MoM", "Inflazione PCE, mese su mese", "inflazione"),
    (r"^Core Inflation Rate YoY", "Inflazione di fondo, anno su anno", "inflazione_core"),
    (r"^Core Inflation Rate MoM", "Inflazione di fondo, mese su mese", "inflazione_core"),
    (r"^Inflation Rate YoY", "Inflazione, anno su anno", "inflazione"),
    (r"^Inflation Rate MoM", "Inflazione, mese su mese", "inflazione"),
    (r"^CPI s\.a", "Indice dei prezzi al consumo destagionalizzato", "inflazione"),
    (r"^CPI", "Indice dei prezzi al consumo", "inflazione"),
    (r"^Core PPI", "Prezzi alla produzione di fondo, mese su mese", "prezzi_imprese"),
    (r"^PPI", "Prezzi alla produzione, mese su mese", "prezzi_imprese"),
    (r"^Wholesale Prices MoM", "Prezzi all'ingrosso, mese su mese", "prezzi_imprese"),
    (r"^Wholesale Prices YoY", "Prezzi all'ingrosso, anno su anno", "prezzi_imprese"),
    (r"^GDP Price Index", "Deflatore del PIL, trimestre su trimestre", "prezzi_imprese"),
    (r"^(Fed|ECB) Interest Rate Decision", "Decisione sui tassi", "banca_centrale"),
    (r"^Deposit Facility Rate", "Tasso sui depositi BCE", "banca_centrale"),
    (r"^FOMC Statement", "Comunicato della Fed", "banca_centrale"),
    (r"^ECB Monetary Policy Statement", "Comunicato della BCE", "banca_centrale"),
    (r"^Fed Press Conference", "Conferenza stampa della Fed", "banca_centrale"),
    (r"^ECB Press Conference", "Conferenza stampa della BCE", "banca_centrale"),
    (r"^ECB President (\w+) Speech", "Discorso della presidente BCE \\1", "discorso"),
    (r"^Fed (\w+) Speech", "Discorso di \\1 (Fed)", "discorso"),
    (r"^Atlanta Fed GDPNow", "Stima del PIL della Fed di Atlanta (GDPNow)", "stima_pil"),
    (r"^GDP Growth Rate QoQ", "PIL, trimestre su trimestre", "pil"),
    (r"^GDP Growth Rate YoY", "PIL, anno su anno", "pil"),
    (r"^Non Farm Payrolls", "Nuovi occupati non agricoli (Non Farm Payrolls)", "lavoro"),
    (r"^Unemployment Rate", "Tasso di disoccupazione", "lavoro"),
    (r"^Unemployment Change", "Variazione dei disoccupati", "lavoro"),
    (r"^Unemployed Persons", "Numero di disoccupati", "lavoro"),
    (r"^Unemployment Benefit Claims", "Richieste di sussidio di disoccupazione", "lavoro"),
    (r"^Initial Jobless Claims", "Nuove richieste di sussidio di disoccupazione", "lavoro"),
    (r"^ADP Employment Change Weekly", "Occupati nel settore privato ADP, media settimanale", "lavoro"),
    (r"^ADP Employment Change", "Occupati nel settore privato ADP", "lavoro"),
    (r"^JOLTs Job Openings", "Posti di lavoro vacanti (JOLTS)", "lavoro"),
    (r"^Participation Rate", "Tasso di partecipazione al lavoro", "lavoro"),
    (r"^Employment Change QoQ", "Occupati, trimestre su trimestre", "lavoro"),
    (r"^Employment Change YoY", "Occupati, anno su anno", "lavoro"),
    (r"^Average Hourly Earnings MoM", "Salario orario medio, mese su mese", "salari"),
    (r"^Average Hourly Earnings YoY", "Salario orario medio, anno su anno", "salari"),
    (r"^Employment Cost - Benefits", "Costo del lavoro: benefit", "salari"),
    (r"^Employment Cost - Wages", "Costo del lavoro: salari", "salari"),
    (r"^Employment Cost Index", "Indice del costo del lavoro", "salari"),
    (r"^Nonfarm Productivity", "Produttività del lavoro", "salari"),
    (r"^Ifo Business Climate", "Clima di fiducia delle imprese Ifo", "fiducia"),
    (r"^GfK Consumer Confidence", "Fiducia dei consumatori GfK", "fiducia"),
    (r"^CB Consumer Confidence", "Fiducia dei consumatori del Conference Board", "fiducia"),
    (r"^Michigan Consumer Sentiment", "Fiducia dei consumatori dell'Università del Michigan", "fiducia"),
    (r"^Consumer Confidence", "Fiducia dei consumatori", "fiducia"),
    (r"^Business Confidence", "Fiducia delle imprese", "fiducia"),
    (r"^Economic Sentiment", "Indice del sentimento economico", "fiducia"),
    (r"^S&P Global Manufacturing PMI", "PMI manifatturiero", "pmi"),
    (r"^S&P Global Services PMI", "PMI dei servizi", "pmi"),
    (r"^ISM Manufacturing PMI", "ISM manifatturiero", "pmi"),
    (r"^ISM Manufacturing Employment", "ISM manifatturiero: occupazione", "pmi"),
    (r"^ISM Services PMI", "ISM servizi", "pmi"),
    (r"^Chicago PMI", "PMI di Chicago", "pmi"),
    (r"^Chicago Fed National Activity", "Indice di attività della Fed di Chicago", "attivita_regionale"),
    (r"^Dallas Fed Manufacturing", "Indice manifatturiero della Fed di Dallas", "attivita_regionale"),
    (r"^Durable Goods Orders Ex Transp", "Ordini di beni durevoli esclusi i trasporti", "produzione"),
    (r"^Durable Goods Orders", "Ordini di beni durevoli", "produzione"),
    (r"^Factory Orders", "Ordini all'industria", "produzione"),
    (r"^Industrial Production", "Produzione industriale, mese su mese", "produzione"),
    (r"^Retail Inventories", "Scorte dei commercianti esclusa l'auto", "produzione"),
    (r"^Wholesale Inventories", "Scorte dei grossisti", "produzione"),
    (r"^Retail Sales MoM", "Vendite al dettaglio, mese su mese", "consumi"),
    (r"^Retail Sales YoY", "Vendite al dettaglio, anno su anno", "consumi"),
    (r"^Personal Income", "Reddito delle famiglie", "consumi"),
    (r"^Personal Spending", "Spesa delle famiglie", "consumi"),
    (r"^Building Permits", "Permessi di costruzione", "casa"),
    (r"^S&P/Case-Shiller", "Prezzi delle case Case-Shiller, anno su anno", "casa"),
    (r"^New Home Sales MoM", "Vendite di case nuove, mese su mese", "casa"),
    (r"^New Home Sales", "Vendite di case nuove", "casa"),
    (r"^Existing Home Sales MoM", "Vendite di case esistenti, mese su mese", "casa"),
    (r"^Existing Home Sales", "Vendite di case esistenti", "casa"),
    (r"^MBA 30-Year Mortgage Rate", "Tasso dei mutui a 30 anni", "casa"),
    (r"^Goods Trade Balance", "Bilancia commerciale dei beni", "commercio"),
    (r"^Balance of Trade", "Bilancia commerciale", "commercio"),
    (r"^Exports", "Esportazioni", "commercio"),
    (r"^Imports", "Importazioni", "commercio"),
    (r"^API Crude Oil", "Scorte di greggio (stima API)", "energia"),
    (r"^EIA Crude Oil", "Scorte di greggio (dato ufficiale EIA)", "energia"),
    (r"^EIA Gasoline", "Scorte di benzina (EIA)", "energia"),
    (r"^EIA Short-Term Energy Outlook", "Previsioni sull'energia dell'EIA", "energia"),
    (r"^Monthly Budget Statement", "Saldo mensile del bilancio federale", "conti_pubblici"),
    (r"Elections", "Elezioni di metà mandato", "politica"),
]
FASE = {"Prel": "stima preliminare", "Flash": "stima rapida", "Adv": "prima stima", "Final": "dato definitivo"}


def _periodo(p):
    if not p:
        return None
    q = re.fullmatch(r"Q([1-4])", p)
    if q:
        return q.group(1) + "° trimestre"
    return MESI.get(p, p)


def _traduci(titolo):
    for pat, nome, fam in REGOLE:
        m = re.search(pat, titolo)
        if m:
            nome = m.expand(nome) if "\\" in nome else nome
            fase = next((v for k, v in FASE.items() if re.search(rf"\b{k}\b", titolo)), None)
            return nome, fam, fase
    return titolo, None, None


def build_calendario():
    raw = json.loads((RAW / "calendario_tv.json").read_text())
    eventi, mancanti = [], set()
    for e in raw:
        nome, fam, fase = _traduci(e["title"])
        if fam is None:
            mancanti.add(e["title"])
        eventi.append({
            "data": e["date"],
            "paese": e["country"],
            "nome": nome,
            "originale": e["title"],
            "fase": fase,
            "famiglia": fam,
            "importanza": "alta" if e.get("importance", 0) >= 1 else "normale",
            "periodo": _periodo(e.get("period")),
            "effettivo": e.get("actual"),
            "previsto": e.get("forecast"),
            "precedente": e.get("previous"),
            "unita": e.get("unit"),
            "scala": e.get("scale"),
            "fonte": e.get("source"),
        })
    if mancanti:
        print("  calendario: titoli senza traduzione:", sorted(mancanti))
    eventi.sort(key=lambda x: x["data"])
    return {
        "aggiornato": "2026-10-30",
        "fonte": "TradingView, calendario economico (fonti ufficiali: istituti di statistica e banche centrali)",
        "paesi": PAESI_CAL,
        "famiglie": FAMIGLIE,
        "eventi": eventi,
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, fn in [("titoli", build_titoli), ("etf", build_etf), ("calendario", build_calendario)]:
        data = fn()
        (OUT / f"{name}.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
        print(f"  scritto site/data/{name}.json")


if __name__ == "__main__":
    main()
