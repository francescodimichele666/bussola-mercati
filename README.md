# Bussola dei Mercati

Sito di **sola informazione finanziaria**, completamente automatico. Ogni giorno lavorativo un programma scarica dati reali (mercati, economia, geopolitica), rifà i calcoli e ripubblica la pagina. Nessuno deve toccare niente.

Anteprima con dati reali: https://claude.ai/artifact/QYQh6Ur93AfGeBAKGbeRtC

---

## 1. Come funziona (in parole semplici)

```
 Fonti pubbliche                 Motore (Python)                  Sito (pagina web)
 ─────────────────               ───────────────────              ───────────────────
 Yahoo Finance  (prezzi)   ─┐                                     • Grafico 3D
 BCE            (tassi,    ─┤    engine/build.py                  • Quadro economico
                 inflazione)├──► scarica, controlla, calcola ──►   • L'Italia oggi
 Eurostat       (lavoro,   ─┤    scrive site/data/data.json       • Europa a confronto
                 PIL UE)    │                                     • Categorie e fondi più grandi
 FRED / Fed     (USA, VIX) ─┤                                     • Dal mondo
 Banca Mondiale (PIL)      ─┤                                     • Metodo e fonti
 Indice GPR     (geopol.)  ─┘                                     • Avvertenze legali
                     ▲
                     └── GitHub Actions lo avvia da solo 2 volte al giorno (lun-ven)
```

* **Il sito non inventa nulla.** Mostra solo numeri arrivati dalle fonti, con data e fonte su ogni riquadro. Se una fonte non risponde, resta il dato precedente marcato "non aggiornato".
* **Analisi tecnica**: media a 10 mesi, variazione a 12 mesi, RSI, distanza dal massimo.
* **Fondamentali**: rendimenti dei titoli di Stato, P/E e rendimento da dividendi degli indici quando disponibili.
* **Italia ed Europa al centro**: inflazione, disoccupazione, crescita del PIL e rendimenti a 10 anni di Italia, Germania, Francia, Spagna e area euro; spread sul Bund; borse nazionali (FTSE MIB, DAX, CAC 40, IBEX 35, Euro Stoxx 50).
* **Categorie in euro**: ogni categoria è misurata con un ETF UCITS quotato in euro (niente più ETF americani).
* **Fondi più grandi per categoria**: per ogni categoria gli ETF/ETC con più patrimonio, con ISIN, emittente, costo annuo e politica dei proventi. Elenco oggettivo, ordinato solo per patrimonio.
* **Dal mondo**: tassi e inflazione USA, curva dei Treasury, VIX, PIL di USA e Cina.
* **Geopolitica**: indice GPR della Federal Reserve (Caldara e Iacoviello).
* Il simulatore del capitale è stato tolto su richiesta di Francesco: al suo posto la tabella mostra "anni in perdita" e il calo massimo, uguali per tutti.

## 2. Costi

| Voce | Costo |
|---|---|
| Hosting del sito (GitHub Pages, repository pubblico) | 0 € |
| Motore automatico (GitHub Actions, repository pubblico) | 0 € |
| Dati BCE, FRED, Banca Mondiale, GPR | 0 € |
| Dati di prezzo Yahoo Finance (yfinance) | 0 €, ma vedi punto 5 |
| Dominio tipo `bussoladeimercati.it` | circa 10–20 € all'anno |
| Revisione legale dei testi (consigliata, una tantum) | circa 500–1.500 € |
| **Totale per partire** | **circa 15 € all'anno + revisione legale** |

Se un giorno vuoi dati di prezzo con licenza commerciale: servizi come EODHD, Twelve Data o Financial Modeling Prep costano circa 20–80 € al mese. Il motore è fatto per cambiare fonte toccando una sola funzione.

## 3. Metterlo online, passo per passo

Tempo richiesto: circa 30 minuti. Non serve saper programmare.

1. **Crea un account GitHub** gratuito su https://github.com/signup (se non lo hai già).
2. **Crea un repository**: in alto a destra `+` → *New repository*. Nome: `bussola-mercati`. Seleziona **Public** (serve per avere tutto gratis). Clicca *Create repository*.
3. **Carica i file**: nella pagina del repository clicca *uploading an existing file* e trascina **tutto il contenuto** della cartella `bussola-mercati` (cartelle `engine`, `site`, `.github` e il file `README.md`). Clicca *Commit changes*.
   * Attenzione: la cartella `.github` è nascosta su Mac e Windows. Su Mac premi `Cmd + Shift + .` nel Finder per vederla. In alternativa dimmi quando il repository esiste e la carico io.
4. **Attiva il sito**: *Settings* → *Pages* → alla voce *Source* scegli **GitHub Actions**.
5. **Primo aggiornamento**: scheda *Actions* → a sinistra *Aggiorna dati e pubblica il sito* → pulsante **Run workflow**. Dopo 2–4 minuti compare una spunta verde.
6. **Apri il sito**: torna in *Settings* → *Pages*: in alto trovi l'indirizzo, del tipo `https://tuonome.github.io/bussola-mercati/`.

Da qui in poi il sito si aggiorna da solo alle 6:30 e alle 22:30 (ora UTC), dal lunedì al venerdì.

**Dominio personale (facoltativo)**: compra il dominio (Aruba, Register.it, Cloudflare), poi in *Settings* → *Pages* → *Custom domain* scrivi il dominio e segui le istruzioni DNS che GitHub mostra.

**Se un giorno l'aggiornamento fallisce**: GitHub ti manda una mail. Il sito resta online con i dati del giorno prima. Basta premere di nuovo *Run workflow* o scrivermi.

## 4. Normativa: cosa puoi e non puoi fare

Questo punto è il più importante per un'attività che vuoi far crescere.

* In Italia la **consulenza in materia di investimenti** (art. 1, comma 5-septies del TUF, direttiva MiFID II) è riservata a soggetti autorizzati e iscritti all'Albo OCF. È consulenza dare **raccomandazioni personalizzate** su **strumenti finanziari specifici**, presentate come adatte alla persona.
* Il sito è costruito per restare dalla parte dell'**informazione**:
  * mostra **categorie** (azioni Europa, oro, titoli di Stato…) con dati storici uguali per tutti, senza chiedere nulla all'utente;
  * i **fondi più grandi** sono un elenco oggettivo per patrimonio, con la scritta "non è una classifica di qualità né un consiglio" e l'invito a leggere il KID. Mai scrivere "migliori", mai link di affiliazione accanto all'elenco;
  * avvertenza ben visibile in cima, ripetuta nella sezione fondi e per esteso in fondo;
  * nessun dato personale raccolto, nessun cookie.
  * privacy: la pagina carica i caratteri da Google Fonts, che riceve l'indirizzo IP del visitatore. Prima del lancio pubblico conviene ospitare i font dentro il sito (te lo preparo io) e aggiungere una breve informativa privacy.
* **Cosa evitare**: frasi come "ti consigliamo", "il portafoglio giusto per te", percentuali di ripartizione per profilo, link di affiliazione a broker accanto ai risultati, nomi di singoli prodotti come "migliori".
* **Prima di guadagnarci** (pubblicità, abbonamenti, affiliazioni) fai rivedere testi e modello di guadagno da un avvocato esperto di diritto dei mercati finanziari. La Consob negli ultimi anni ha posto molta attenzione ai siti e ai "finfluencer" che sconfinano nella consulenza.

Questo non è un parere legale: è il motivo per cui il sito è progettato così.

## 5. Licenze dei dati

* **BCE, Banca Mondiale**: riutilizzo libero citando la fonte (già fatto sul sito).
* **FRED**: libero per la maggior parte delle serie. Alcune (VIX di CBOE, spread ICE BofA) appartengono ai rispettivi proprietari: per uso commerciale verifica le condizioni.
* **Indice GPR**: dati pubblici di ricerca, da citare (già fatto).
* **TradingView**: i riquadri (widget) gratuiti si possono inserire nel sito così come sono, con il marchio TradingView visibile e i dati in ritardo. Non bisogna copiare i loro numeri in tabelle proprie per uso commerciale: per quello serve un contratto con un fornitore di dati.
* **Yahoo Finance**: yfinance è una libreria non ufficiale; le condizioni di Yahoo permettono l'uso personale. Per un sito commerciale conviene passare a un fornitore con licenza (vedi costi).

## 6. Struttura dei file

| File | A cosa serve |
|---|---|
| `engine/config.json` | Elenco delle categorie e dei fondi più grandi (ISIN, costo, patrimonio). Patrimonio e costi vanno ricontrollati ogni 3 mesi; il motore prova ad aggiornare il patrimonio da solo. |
| `engine/build.py` | Il motore: scarica i dati e fa i calcoli. |
| `engine/requirements.txt` | Librerie Python usate dal motore. |
| `engine/anteprima.py`, `engine/anteprima_raw_eu/` | Dati reali di anteprima (TradingView, prezzi senza cedole per i fondi a distribuzione), usati solo prima del primo aggiornamento. |
| `site/index.html`, `site/style.css`, `site/app.js` | La pagina principale. |
| `site/titoli-di-stato.html`, `site/etf.html`, `site/calendario.html`, `site/pagine.js` | Le tre pagine interne: titoli di Stato per Paese, ETF del mondo con filtri, calendario economico spiegato. |
| `engine/pagine.py`, `engine/anteprima_raw_pagine/` | Prepara `titoli.json`, `etf.json` e `calendario.json` (nomi e spiegazioni in italiano, cambi, doppioni tolti) dai dati grezzi di TradingView. |
| `site/data/data.json` | I dati che la pagina legge. Lo riscrive il motore. |
| `.github/workflows/aggiorna-sito.yml` | Le istruzioni per l'aggiornamento automatico. |

Per provarlo sul tuo computer: `python3 -m http.server` dentro la cartella `site`, poi apri http://localhost:8000.

## 7. Prossimi passi possibili

* Elenco completo dei BTP (ISIN, cedola, scadenza) dal file pubblico del Ministero dell'Economia.
* Aggiornamento automatico giornaliero delle tabelle delle tre pagine interne. Oggi le quotazioni dal vivo arrivano dai riquadri gratuiti di TradingView (ritardo di almeno 15–20 minuti); le tabelle sotto sono una fotografia del 30 ottobre 2026. Il motore su GitHub non può leggere TradingView: servirà una fonte con licenza o gratuita (per esempio i rendimenti giornalieri della BCE) per aggiornarle da sole.
* Newsletter settimanale automatica con il "quadro di oggi".
* Pagine di spiegazione (cos'è uno spread, cos'è la volatilità) per farsi trovare su Google.
