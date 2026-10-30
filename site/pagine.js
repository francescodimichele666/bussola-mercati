/* Bussola dei Mercati: pagine Titoli di Stato, ETF del mondo e Calendario economico.
   Ogni pagina legge il proprio file in data/ e, sul sito pubblicato, aggiunge un riquadro
   TradingView con quotazioni in ritardo. Tutti i numeri vengono dai file dati. */
(function () {
  "use strict";

  var PAGE = document.body.getAttribute("data-page");
  var MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"];
  var TZ = "Europe/Rome";

  function $(s, el) { return (el || document).querySelector(s); }
  function $$(s, el) { return Array.prototype.slice.call((el || document).querySelectorAll(s)); }
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function num(x, d) { return x.toLocaleString("it-IT", { minimumFractionDigits: d, maximumFractionDigits: d }); }
  function signed(x, d) { return (x > 0 ? "+" : x < 0 ? "−" : "") + num(Math.abs(x), d); }
  function cls(x) { return x == null ? "" : x > 0 ? "pos" : x < 0 ? "neg" : ""; }
  function dayLong(iso) { var m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso); return m ? +m[3] + " " + MESI[+m[2] - 1] + " " + m[1] : iso; }
  function dark() { var t = document.documentElement.getAttribute("data-theme"); return t ? t === "dark" : window.matchMedia && matchMedia("(prefers-color-scheme: dark)").matches; }

  function load(file, done) {
    fetch("data/" + file, { cache: "no-cache" })
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(done)
      .catch(function () { $("#updated").textContent = "I dati non si sono caricati. Ricarica la pagina tra qualche minuto."; });
  }

  // ---------- Riquadro TradingView (solo sul sito pubblicato) ----------
  // Il widget gratuito di TradingView mostra quotazioni con almeno 15-20 minuti di ritardo.
  // Se lo script non si carica (anteprima, blocchi del browser) resta un messaggio chiaro.
  function liveWidget(box, kind, config, height) {
    var holder = document.createElement("div");
    holder.className = "tradingview-widget-container";
    holder.style.height = height + "px";
    var inner = document.createElement("div");
    inner.className = "tradingview-widget-container__widget";
    holder.appendChild(inner);
    var sc = document.createElement("script");
    sc.src = "https://s3.tradingview.com/external-embedding/embed-widget-" + kind + ".js";
    sc.async = true;
    config.locale = "it";
    config.colorTheme = dark() ? "dark" : "light";
    config.isTransparent = true;
    config.width = "100%";
    config.height = height;
    sc.textContent = JSON.stringify(config);
    var failed = false;
    function fail() {
      if (failed) return; failed = true;
      holder.remove();
      box.classList.add("off");
      $(".live-off", box).hidden = false;
    }
    sc.onerror = fail;
    holder.appendChild(sc);
    $(".live-slot", box).appendChild(holder);
    setTimeout(function () { if (!holder.querySelector("iframe")) fail(); }, 9000);
  }

  // ======================================================== TITOLI DI STATO
  var EURO = ["IT", "DE", "FR", "ES", "PT", "GR", "NL", "BE", "AT", "IE", "FI"];

  function initTitoli(d) {
    var sel = "IT";
    var byCode = {}; d.paesi.forEach(function (p) { byCode[p.codice] = p; });
    var de = byCode.DE;
    function at(p, y) { return p && p.curva.find(function (r) { return r.scadenza_anni === y; }); }

    $("#updated").textContent = "Rendimenti di fine giornata del " + dayLong(d.aggiornato);
    $("#snap-date").textContent = dayLong(d.aggiornato);

    liveWidget($("#live"), "market-quotes", {
      showSymbolLogo: false,
      symbolsGroups: [
        { name: "Italia", symbols: [2, 5, 10, 30].map(function (y) { return { name: "TVC:IT" + (y < 10 ? "0" : "") + y + "Y", displayName: "BTP " + y + " anni" }; }) },
        { name: "10 anni in Europa", symbols: ["IT", "DE", "FR", "ES", "PT", "GR"].map(function (c) { return { name: "TVC:" + c + "10Y", displayName: byCode[c].nome }; }) }
      ]
    }, 420);

    // scelta del Paese
    var chips = $("#paesi");
    chips.innerHTML =
      '<span class="chip-group">Area euro</span>' + EURO.map(chip).join("") +
      '<span class="chip-group">Fuori dall\'euro</span>' + d.paesi.filter(function (p) { return EURO.indexOf(p.codice) < 0; }).map(function (p) { return chip(p.codice); }).join("");
    function chip(c) { return '<button type="button" data-c="' + c + '" aria-pressed="' + (c === sel) + '">' + esc(byCode[c].nome) + "</button>"; }
    chips.addEventListener("click", function (e) {
      var b = e.target.closest("button"); if (!b) return;
      sel = b.getAttribute("data-c");
      $$("button", chips).forEach(function (x) { x.setAttribute("aria-pressed", x === b); });
      draw();
    });

    function draw() {
      var p = byCode[sel], ten = at(p, 10), tde = at(de, 10), euro = p.valuta === "EUR";
      var spread = ten && tde && sel !== "DE" ? (ten.rendimento - tde.rendimento) * 100 : null;
      var dy = ten && ten.rendimento_1a_fa != null ? (ten.rendimento - ten.rendimento_1a_fa) * 100 : null;
      var head = '<div class="bond-kpis">';
      head += kpi("Rendimento a 10 anni", ten ? num(ten.rendimento, 2) + "%" : "n.d.", ten ? p.titolo + " con scadenza " + dayLong(ten.scadenza) : "");
      if (sel === "DE") head += kpi("Spread", "—", "La Germania è il riferimento per gli altri Paesi dell'euro");
      else if (spread != null) head += kpi(euro ? "Spread con il Bund" : "Differenza con il Bund", num(spread, 0) + " pb", euro ? "quanto in più paga " + p.nome + " rispetto alla Germania" : "valute diverse: il confronto è solo indicativo");
      head += kpi("Rispetto a un anno fa", dy != null ? signed(dy, 0) + " pb" : "n.d.", ten && ten.rendimento_1a_fa != null ? "un anno fa era " + num(ten.rendimento_1a_fa, 2) + "%" : "");
      head += "</div>";
      $("#bond-head").innerHTML = "<h3>" + esc(p.nome) + (euro ? "" : ' <span class="tag">in ' + esc(p.valuta) + "</span>") + "</h3>" + head;
      curveChart($("#curve"), p, de);
      $("#curve-cap").textContent = sel === "DE"
        ? "Rendimento per scadenza dei titoli tedeschi, oggi e un anno fa."
        : "Rendimento per scadenza: " + p.nome + " oggi, " + p.nome + " un anno fa e Germania oggi.";

      var rows = p.curva.map(function (r) {
        var g = at(de, r.scadenza_anni), sp = g && sel !== "DE" ? (r.rendimento - g.rendimento) * 100 : null;
        var ch = r.rendimento_1a_fa != null ? (r.rendimento - r.rendimento_1a_fa) * 100 : null;
        return "<tr><td><b>" + r.scadenza_anni + (r.scadenza_anni === 1 ? " anno" : " anni") + '</b></td><td><span class="cat-name">' + esc(p.titolo) + " " + (r.cedola ? num(r.cedola, r.cedola % 1 ? 2 : 0) + "%" : "zero coupon") + '</span><span class="cat-sub">scade il ' + dayLong(r.scadenza) + "</span></td>" +
          '<td class="num">' + num(r.prezzo, 2) + '</td><td class="num"><b>' + num(r.rendimento, 2) + '%</b></td><td class="num ' + cls(r.var_giorno_pb) + '">' + (r.var_giorno_pb != null ? signed(r.var_giorno_pb, 1) : "n.d.") + '</td><td class="num ' + cls(ch) + '">' + (ch != null ? signed(ch, 0) : "n.d.") + '</td><td class="num">' + (sp != null ? num(sp, 0) : "—") + "</td></tr>";
      }).join("");
      $("#bond-table tbody").innerHTML = rows;
      $("#bond-foot").textContent = "Per ogni scadenza c'è un titolo di riferimento: quello che il mercato usa come termometro per quella durata. Prezzo su 100 di valore nominale. " +
        (euro ? "" : "I titoli di " + p.nome + " sono in " + p.valuta + ": chi investe in euro è esposto anche al cambio. ") + "Fonte: " + d.fonte + ".";
    }
    function kpi(l, v, s) { return '<div class="kpi"><span class="lbl">' + esc(l) + '</span><span class="val">' + v + '</span><span class="sub">' + esc(s) + "</span></div>"; }

    // confronto a 10 anni
    var list = d.paesi.map(function (p) { return { p: p, r: at(p, 10) }; }).filter(function (x) { return x.r; });
    function bars(items) {
      var max = Math.max.apply(null, list.map(function (x) { return x.r.rendimento; }));
      return items.sort(function (a, b) { return b.r.rendimento - a.r.rendimento; }).map(function (x) {
        var sp = x.p.codice !== "DE" && x.p.valuta === "EUR" ? num((x.r.rendimento - at(de, 10).rendimento) * 100, 0) + " pb" : x.p.codice === "DE" ? "riferimento" : esc(x.p.valuta);
        return '<li class="' + (x.p.codice === "IT" ? "me" : "") + '"><span class="n">' + esc(x.p.nome) + '</span><span class="b"><i style="width:' + (x.r.rendimento / max * 100).toFixed(1) + '%"></i></span><span class="v">' + num(x.r.rendimento, 2) + '%</span><span class="s">' + sp + "</span></li>";
      }).join("");
    }
    $("#y10-euro").innerHTML = bars(list.filter(function (x) { return x.p.valuta === "EUR"; }));
    $("#y10-other").innerHTML = bars(list.filter(function (x) { return x.p.valuta !== "EUR"; }));

    draw();
    var lastW = 0;
    if (window.ResizeObserver) new ResizeObserver(function (e) { var w = Math.round(e[0].contentRect.width); if (w !== lastW) { lastW = w; curveChart($("#curve"), byCode[sel], de); } }).observe($("#curve"));
  }

  function curveChart(el, p, de) {
    var W = Math.max(280, el.clientWidth), H = W < 500 ? 220 : 260, padL = 40, padR = 16, padT = 14, padB = 30;
    var series = [{ name: p.nome, color: "var(--accent)", w: 2.6, pts: p.curva.map(function (r) { return [r.scadenza_anni, r.rendimento]; }) }];
    var old = p.curva.filter(function (r) { return r.rendimento_1a_fa != null; }).map(function (r) { return [r.scadenza_anni, r.rendimento_1a_fa]; });
    if (old.length > 1) series.push({ name: "un anno fa", color: "var(--muted)", w: 1.6, dash: "4 4", pts: old });
    if (p.codice !== "DE") series.push({ name: "Germania", color: "#c08a2b", w: 1.8, pts: de.curva.map(function (r) { return [r.scadenza_anni, r.rendimento]; }) });
    var all = []; series.forEach(function (s) { s.pts.forEach(function (q) { all.push(q[1]); }); });
    var lo = Math.min.apply(null, all), hi = Math.max.apply(null, all), pad = (hi - lo) * 0.15 || 0.3;
    lo = Math.max(0, lo - pad); hi += pad;
    var maxY = Math.max.apply(null, p.curva.map(function (r) { return r.scadenza_anni; }).concat([30]));
    function X(y) { return padL + Math.log(1 + y) / Math.log(1 + maxY) * (W - padL - padR); }
    function Y(v) { return padT + (hi - v) / (hi - lo) * (H - padT - padB); }
    var s = '<svg viewBox="0 0 ' + W + " " + H + '" width="' + W + '" height="' + H + '" role="img" aria-label="Curva dei rendimenti di ' + esc(p.nome) + '">';
    var step = hi - lo > 3 ? 1 : 0.5;
    for (var t = Math.ceil(lo / step) * step; t <= hi; t += step) {
      var y = Y(t).toFixed(1);
      s += '<line x1="' + padL + '" x2="' + (W - padR) + '" y1="' + y + '" y2="' + y + '" stroke="var(--line-soft)"/><text x="' + (padL - 6) + '" y="' + (+y + 4) + '" text-anchor="end">' + num(t, step < 1 ? 1 : 0) + "%</text>";
    }
    [1, 2, 5, 10, 20, 30, 50].filter(function (y) { return y <= maxY; }).forEach(function (y) {
      s += '<text x="' + X(y).toFixed(1) + '" y="' + (H - 8) + '" text-anchor="middle">' + y + "a</text>";
    });
    series.slice().reverse().forEach(function (sr) {
      var dd = sr.pts.map(function (q, i) { return (i ? "L" : "M") + X(q[0]).toFixed(1) + "," + Y(q[1]).toFixed(1); }).join("");
      s += '<path d="' + dd + '" fill="none" stroke="' + sr.color + '" stroke-width="' + sr.w + '"' + (sr.dash ? ' stroke-dasharray="' + sr.dash + '"' : "") + ' stroke-linejoin="round" stroke-linecap="round"/>';
      if (!sr.dash) sr.pts.forEach(function (q) { s += '<circle cx="' + X(q[0]).toFixed(1) + '" cy="' + Y(q[1]).toFixed(1) + '" r="3" fill="' + sr.color + '"/>'; });
    });
    el.innerHTML = s + "</svg>";
    $("#curve-legend").innerHTML = series.map(function (sr) {
      return '<span><i style="background:' + sr.color + (sr.dash ? ";opacity:.7" : "") + '"></i>' + esc(sr.name === "un anno fa" ? p.nome + " un anno fa" : sr.name + " oggi") + "</span>";
    }).join("");
  }

  // ======================================================== ETF DEL MONDO
  var PAGE_SIZE = 40;

  function initEtf(d) {
    var all = d.etf, shown = PAGE_SIZE, cellN = 0;
    var f = { q: "", mercato: "Europa", classe: "", area: "", ter: "", politica: "", ordine: "aum" };
    $("#updated").textContent = "Dati di borsa del " + dayLong(d.aggiornato);
    $("#snap-date").textContent = dayLong(d.aggiornato);

    // nel riquadro dal vivo: i 4 ETF UCITS più grandi per patrimonio in ogni classe
    function top(c) { return all.filter(function (e) { return e.ucits && e.classe === c; }).slice(0, 4).map(function (e) { return { name: e.borsa + ":" + e.ticker, displayName: e.nome.slice(0, 38) }; }); }
    liveWidget($("#live"), "market-quotes", {
      showSymbolLogo: false,
      symbolsGroups: [{ name: "Azioni", symbols: top("Azioni") }, { name: "Obbligazioni", symbols: top("Obbligazioni") }, { name: "Materie prime", symbols: top("Materie prime") }]
    }, 420);

    function opts(field) {
      var seen = {}; all.forEach(function (e) { if (e[field]) seen[e[field]] = (seen[e[field]] || 0) + 1; });
      return Object.keys(seen).sort(function (a, b) { return seen[b] - seen[a]; });
    }
    fill("#f-classe", opts("classe"), "Tutte");
    fill("#f-area", opts("area").filter(function (a) { return a !== "Altro"; }), "Tutte");
    function fill(id, values, first) { $(id).innerHTML = '<option value="">' + first + "</option>" + values.map(function (v) { return '<option value="' + esc(v) + '">' + esc(v) + "</option>"; }).join(""); }

    $("#etf-filters").addEventListener("input", function (e) {
      var t = e.target; if (!t.name) return;
      f[t.name] = t.value; shown = PAGE_SIZE; draw();
    });
    $("#etf-more").addEventListener("click", function () { shown += PAGE_SIZE; draw(); });

    function draw() {
      var q = f.q.trim().toLowerCase();
      var rows = all.filter(function (e) {
        if (f.mercato && e.mercato !== f.mercato) return false;
        if (f.classe && e.classe !== f.classe) return false;
        if (f.area && e.area !== f.area) return false;
        if (f.politica && e.politica !== f.politica) return false;
        if (f.ter && (e.ter == null || e.ter > +f.ter)) return false;
        if (q && (e.nome + " " + e.ticker + " " + (e.indice || "") + " " + (e.emittente || "")).toLowerCase().indexOf(q) < 0) return false;
        return true;
      });
      var key = f.ordine;
      rows.sort(function (a, b) {
        if (key === "ter") return (a.ter == null ? 9 : a.ter) - (b.ter == null ? 9 : b.ter) || b.aum_mld_eur - a.aum_mld_eur;
        if (key === "nome") return a.nome.localeCompare(b.nome, "it");
        return b.aum_mld_eur - a.aum_mld_eur;
      });
      $("#etf-count").textContent = rows.length === 1 ? "1 ETF" : num(rows.length, 0) + " ETF";
      $("#usa-note").hidden = f.mercato === "Europa";
      var maxAum = rows.length ? Math.max.apply(null, rows.map(function (e) { return e.aum_mld_eur; })) : 1;
      $("#etf-list").innerHTML = rows.slice(0, shown).map(function (e, i) {
        var meta = [e.emittente, e.indice].filter(Boolean).map(esc).join(" · ");
        var tags = '<span class="tag">' + esc(e.classe) + "</span>" + (e.area !== "Altro" ? '<span class="tag">' + esc(e.area) + "</span>" : "") + (e.tema && e.tema !== e.classe ? '<span class="tag soft">' + esc(e.tema) + "</span>" : "") + (e.ucits ? "" : '<span class="tag warn">Non UCITS</span>');
        return '<li class="etf"><span class="rank">' + (i + 1) + '</span><div class="name">' + esc(e.nome) + '<span class="meta">' + meta + '</span><span class="tags">' + tags + "</span></div>" +
          cell("Costo annuo", e.ter != null ? num(e.ter, 2) + "%" : "n.d.") +
          cell("Patrimonio", (e.aum_mld_eur >= 10 ? num(e.aum_mld_eur, 0) : num(e.aum_mld_eur, 1)) + " mld €", '<span class="aum-bar"><i style="width:' + Math.max(2, e.aum_mld_eur / maxAum * 100).toFixed(1) + '%"></i></span>') +
          cell("1 anno", e.rend_1a != null ? '<span class="' + cls(e.rend_1a) + '">' + signed(e.rend_1a, 1) + "%</span>" : "n.d.") +
          cell("5 anni", e.rend_5a != null ? '<span class="' + cls(e.rend_5a) + '">' + signed(e.rend_5a, 0) + "%</span>" : "n.d.") +
          '<div class="links"><span class="mono">' + esc(e.borsa + ":" + e.ticker) + "</span>" + (e.politica ? '<span class="pol">' + esc(e.politica) + "</span>" : "") + '<a href="https://it.tradingview.com/symbols/' + esc(e.borsa + "-" + e.ticker) + '/" target="_blank" rel="noopener">Scheda di borsa</a></div></li>';
      }).join("") || '<li class="empty">Nessun ETF con questi filtri. Prova ad allargare la ricerca.</li>';
      $("#etf-more").hidden = rows.length <= shown;
    }
    function cell(k, v, extra) { cellN = cellN % 4 + 1; return '<div class="c c' + cellN + '"><span class="k">' + k + '</span><span class="v">' + v + "</span>" + (extra || "") + "</div>"; }
    $("#etf-foot").textContent = d.nota_rendimenti + " Patrimonio dell'intero fondo; per gli ETF americani convertito da dollari a euro al cambio di " + num(d.cambio.EURUSD, 4) + " del " + dayLong(d.cambio.data) + ". Fonte: " + d.fonte + ".";
    draw();
  }

  // ======================================================== CALENDARIO
  var BANDIERA = { IT: "IT", EU: "EU", DE: "DE", FR: "FR", ES: "ES", US: "US" };
  var SCALA = { K: " mila", M: " mln", B: " mld" };

  function initCalendario(d) {
    var f = { paese: "", importanza: "", vista: "prossimi" };
    $("#updated").textContent = "Calendario aggiornato al " + dayLong(d.aggiornato);
    $("#snap-date").textContent = dayLong(d.aggiornato);

    liveWidget($("#live"), "events", { importanceFilter: "0,1", countryFilter: "it,eu,de,fr,es,us" }, 560);

    var pc = $("#c-paese");
    pc.innerHTML = '<button type="button" data-v="" aria-pressed="true">Tutti</button>' + Object.keys(d.paesi).map(function (k) { return '<button type="button" data-v="' + k + '" aria-pressed="false">' + esc(d.paesi[k]) + "</button>"; }).join("");
    bindChips(pc, "paese"); bindChips($("#c-imp"), "importanza"); bindChips($("#c-vista"), "vista");
    function bindChips(box, key) {
      box.addEventListener("click", function (e) {
        var b = e.target.closest("button"); if (!b) return;
        f[key] = b.getAttribute("data-v");
        $$("button", box).forEach(function (x) { x.setAttribute("aria-pressed", x === b); });
        draw();
      });
    }

    var dayFmt = new Intl.DateTimeFormat("it-IT", { timeZone: TZ, weekday: "long", day: "numeric", month: "long" });
    var keyFmt = new Intl.DateTimeFormat("sv-SE", { timeZone: TZ, year: "numeric", month: "2-digit", day: "2-digit" });
    var timeFmt = new Intl.DateTimeFormat("it-IT", { timeZone: TZ, hour: "2-digit", minute: "2-digit" });
    var today = keyFmt.format(new Date());
    // in anteprima il file è una fotografia: se oggi è fuori dal suo periodo usiamo la data del file
    var span = [keyFmt.format(new Date(d.eventi[0].data)), keyFmt.format(new Date(d.eventi[d.eventi.length - 1].data))];
    if (today < span[0] || today > span[1]) today = d.aggiornato;

    function decs(v) { return v == null ? 0 : Math.min(2, (String(v).split(".")[1] || "").length); }
    function fmtVal(v, e) {
      if (v == null) return "—";
      // stesse cifre decimali per dato, previsto e precedente, così si confrontano a colpo d'occhio
      var dd = Math.max(decs(e.effettivo), decs(e.previsto), decs(e.precedente));
      if (Math.abs(v) >= 100) dd = Math.min(dd, 1);
      var s = signed(v, dd).replace(/^\+/, "") + (SCALA[e.scala] || "");
      if (e.unita === "%") s += "%";
      else if (e.unita === "$" || e.unita === "€") s += " " + e.unita;
      return s;
    }
    function surprise(e) {
      if (e.effettivo == null || e.previsto == null) return "";
      var diff = e.effettivo - e.previsto, tol = Math.max(Math.abs(e.previsto) * 0.005, 1e-9);
      if (Math.abs(diff) <= tol) return '<span class="surp eq">in linea con le attese</span>';
      return '<span class="surp ' + (diff > 0 ? "hi" : "lo") + '">' + (diff > 0 ? "sopra le attese" : "sotto le attese") + "</span>";
    }

    function draw() {
      var ev = d.eventi.filter(function (e) {
        if (f.paese && e.paese !== f.paese) return false;
        if (f.importanza && e.importanza !== "alta") return false;
        var done = e.effettivo != null || (keyFmt.format(new Date(e.data)) < today);
        return f.vista === "prossimi" ? !done : done;
      });
      if (f.vista === "pubblicati") ev.reverse();
      var groups = [], last = null;
      ev.forEach(function (e) {
        var k = keyFmt.format(new Date(e.data));
        if (k !== last) { groups.push({ k: k, items: [] }); last = k; }
        groups[groups.length - 1].items.push(e);
      });
      $("#cal").innerHTML = groups.map(function (g) {
        var dt = new Date(g.items[0].data);
        var dl = dayFmt.format(dt);
        return '<section class="cal-day"><h3>' + esc(dl.charAt(0).toUpperCase() + dl.slice(1)) + (g.k === today ? ' <span class="tag">oggi</span>' : "") + '</h3><ul class="cal-list">' + g.items.map(row).join("") + "</ul></section>";
      }).join("") || '<p class="empty">Nessun appuntamento con questi filtri.</p>';
      $("#cal-count").textContent = ev.length === 1 ? "1 appuntamento" : ev.length + " appuntamenti";
    }
    function row(e) {
      var fam = e.famiglia && d.famiglie[e.famiglia];
      var sub = [e.periodo ? "riferito a " + e.periodo : null, e.fase].filter(Boolean).join(" · ");
      var noNums = e.effettivo == null && e.previsto == null && e.precedente == null;
      return '<li class="ev' + (e.importanza === "alta" ? " hot" : "") + '"><span class="t mono">' + timeFmt.format(new Date(e.data)) + '</span><span class="flag">' + BANDIERA[e.paese] + "</span>" +
        '<div class="what"><span class="nm">' + esc(e.nome) + (e.importanza === "alta" ? ' <span class="imp" title="Dato molto seguito">molto seguito</span>' : "") + "</span>" + (sub ? '<span class="sub">' + esc(sub) + "</span>" : "") + "</div>" +
        (noNums ? '<div class="vals none">Senza numeri: conta quello che viene detto</div>'
          : '<div class="vals"><span><small>Dato</small><b>' + fmtVal(e.effettivo, e) + "</b></span><span><small>Previsto</small>" + fmtVal(e.previsto, e) + "</span><span><small>Precedente</small>" + fmtVal(e.precedente, e) + "</span>" + surprise(e) + "</div>") +
        (fam ? '<details><summary>Cosa significa</summary><p><b>' + esc(fam.nome) + ".</b> " + esc(fam.cosa) + "</p><p><b>Come lo legge di solito il mercato.</b> " + esc(fam.lettura) + "</p>" + (e.fonte ? '<p class="src">Fonte del dato: ' + esc(e.fonte) + "</p>" : "") + "</details>" : "") +
        "</li>";
    }
    draw();
  }

  if (PAGE === "titoli") load("titoli.json", initTitoli);
  if (PAGE === "etf") load("etf.json", initEtf);
  if (PAGE === "calendario") load("calendario.json", initCalendario);
})();
