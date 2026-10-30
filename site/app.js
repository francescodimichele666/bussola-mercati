/* Bussola dei Mercati: legge data/data.json (prodotto dal motore) e disegna la pagina.
   Tutti i numeri mostrati vengono dal file dati; qui si fanno solo calcoli su quei numeri. */
(function () {
  "use strict";

  var SHORT = {
    az_italia: "Italia", az_germania: "Germania", az_francia: "Francia", az_spagna: "Spagna", az_eurozona: "Area euro",
    az_europa: "Europa", az_mondo: "Mondo", az_usa: "USA", az_emergenti: "Emergenti", ob_monetario: "Monetario",
    ob_stato_ea: "Stato area euro", ob_btp: "BTP", ob_corporate: "Societarie", ob_highyield: "High yield",
    mp_oro: "Oro", im_europa: "Immobiliare", cr_bitcoin: "Bitcoin"
  };
  var PAESI = [["IT", "Italia"], ["DE", "Germania"], ["FR", "Francia"], ["ES", "Spagna"], ["EA", "Area euro"]];
  var BORSA = { IT: "az_italia", DE: "az_germania", FR: "az_francia", ES: "az_spagna", EA: "az_eurozona" };
  var RIDGES = [["az_italia", "#6fd3bd"], ["az_spagna", "#ff9f86"], ["az_francia", "#8fb6ff"], ["az_germania", "#e9c46a"], ["az_eurozona", "#c6b3f0"], ["az_mondo", "#9fb0bf"]];
  var MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"];
  var data = null, fundSel = "az_italia", redraw = [];

  function $(s, el) { return (el || document).querySelector(s); }
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function num(x, d) { return x.toLocaleString("it-IT", { minimumFractionDigits: d, maximumFractionDigits: d }); }
  function signed(x, d) { return (x > 0 ? "+" : x < 0 ? "−" : "") + num(Math.abs(x), d); }
  function pct(x, d) { if (x == null || isNaN(x)) return "n.d."; return signed(x * 100, d == null ? 1 : d) + "%"; }
  function cls(x) { return x == null ? "" : x >= 0 ? "pos" : "neg"; }
  function fmtDate(s) {
    if (!s) return "";
    var q = /^(\d{4})-T(\d)$/.exec(s);
    if (q) return q[2] + "° trimestre " + q[1];
    var m = /^(\d{4})-(\d{2})(?:-(\d{2}))?/.exec(s);
    if (!m) return s;
    return (m[3] ? +m[3] + " " : "") + MESI[+m[2] - 1] + " " + m[1];
  }
  function shortDate(s) {
    var q = /^(\d{4})-T(\d)$/.exec(s || ""); if (q) return q[2] + "° trim. " + q[1];
    var m = /^(\d{4})-(\d{2})/.exec(s || ""); return m ? MESI[+m[2] - 1].slice(0, 3) + " " + m[1] : s;
  }
  function tinyDate(s) {
    var q = /^(\d{4})-T(\d)$/.exec(s || ""); if (q) return "T" + q[2] + " " + q[1].slice(2);
    var m = /^(\d{4})-(\d{2})/.exec(s || ""); return m ? MESI[+m[2] - 1].slice(0, 3) + " " + m[1].slice(2) : s;
  }
  function macro(id) { return data.macro.find(function (m) { return m.id === id; }); }
  function cat(id) { return data.categorie.find(function (c) { return c.id === id; }); }
  function srcLink(m) { return m.url ? '<a href="' + esc(m.url) + '" target="_blank" rel="noopener">' + esc(m.fonte) + "</a>" : esc(m.fonte); }
  function srcLine(m) { return fmtDate(m.data) + " · " + srcLink(m); }

  // ---------- Avvio ----------
  fetch("data/data.json", { cache: "no-cache" })
    .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(function (d) { data = d; renderAll(); })
    .catch(function () {
      $("#updated").textContent = "I dati non si sono caricati. Ricarica la pagina tra qualche minuto.";
      $("#scene-loading").classList.add("done");
    });

  function renderAll() {
    var g = new Date(data.generato_il);
    $("#updated").textContent = "Aggiornato il " + g.toLocaleDateString("it-IT", { day: "numeric", month: "long", year: "numeric" });
    $("#foot-meta").textContent = "Ultimo aggiornamento automatico: " + g.toLocaleString("it-IT") + ". Categorie: " + data.categorie.length + ". Indicatori: " + data.macro.length + ".";
    if (data.note && data.note.length) {
      var band = $("#preview-band");
      band.innerHTML = data.note.map(function (n) { return "<p>" + esc(n) + "</p>"; }).join("");
      band.hidden = false;
    }
    renderPulse();
    renderItaly();
    renderEurope();
    renderTable();
    renderFunds();
    renderWorld();
    renderProxies();
    if (window.ResizeObserver) {
      var t = null, lastW = 0;
      new ResizeObserver(function (e) {
        var w = Math.round(e[0].contentRect.width); if (w === lastW) return; lastW = w;
        clearTimeout(t); t = setTimeout(function () { redraw.forEach(function (f) { f(); }); }, 120);
      }).observe($("#it-grid"));
    }
    initLandscape();
  }

  function spreadSeries() {
    var it = macro("y10_IT"), de = macro("y10_DE"); if (!it || !de) return null;
    var dm = {}; de.storico.forEach(function (p) { dm[p[0].slice(0, 7)] = p[1]; });
    return it.storico.filter(function (p) { return dm[p[0].slice(0, 7)] != null; })
      .map(function (p) { return [p[0], (p[1] - dm[p[0].slice(0, 7)]) * 100]; });
  }

  // ---------- Numeri in apertura ----------
  function renderPulse() {
    var out = [], it = cat("az_italia"), inf = macro("infl_IT"), ecb = macro("rate_ecb"), sp = spreadSeries();
    if (it) out.push(["Borsa di Milano, 12 mesi", pct(it.statistiche.rend_1a), "FTSE MIB con dividendi", cls(it.statistiche.rend_1a)]);
    if (sp && sp.length) out.push(["Spread BTP–Bund", num(sp[sp.length - 1][1], 0) + " pb", "differenza tra i rendimenti a 10 anni", ""]);
    if (inf) out.push(["Inflazione Italia", num(inf.valore, 1) + "%", shortDate(inf.data) + ", su un anno prima", ""]);
    if (ecb) out.push(["Tasso BCE", num(ecb.valore, 2) + "%", "rifinanziamento principale", ""]);
    $("#pulse").innerHTML = out.map(function (o) {
      return '<li><span class="lbl">' + esc(o[0]) + '</span><span class="val ' + o[3] + '">' + o[1] + '</span><span class="sub">' + esc(o[2]) + "</span></li>";
    }).join("");
  }

  // ---------- Piccoli grafici ----------
  function niceTicks(lo, hi, n) {
    var span = hi - lo || 1, step = Math.pow(10, Math.floor(Math.log10(span / n))), err = span / n / step;
    step *= err >= 7.5 ? 10 : err >= 3.5 ? 5 : err >= 1.5 ? 2 : 1;
    var t = [], v = Math.ceil(lo / step) * step;
    for (; v <= hi + 1e-9; v += step) t.push(+v.toFixed(6));
    return t;
  }
  function lineChart(el, series, o) {
    var W = Math.max(260, el.clientWidth), H = o.h || 160, padL = 34, padR = o.labelW || 78, padT = 10, padB = 24;
    var all = []; series.forEach(function (s) { s.pts.forEach(function (p) { all.push(p[1]); }); });
    if (o.zero) all.push(0);
    var lo = Math.min.apply(null, all), hi = Math.max.apply(null, all), pad = (hi - lo) * 0.12 || 0.5;
    lo -= pad; hi += pad;
    var labels = series[0].pts.map(function (p) { return p[0]; });
    series.forEach(function (s) { s.pts.forEach(function (p) { if (labels.indexOf(p[0]) < 0) labels.push(p[0]); }); });
    labels.sort();
    function X(lab) { return padL + labels.indexOf(lab) / Math.max(1, labels.length - 1) * (W - padL - padR); }
    function Y(v) { return padT + (hi - v) / (hi - lo) * (H - padT - padB); }
    var s = '<svg viewBox="0 0 ' + W + " " + H + '" width="' + W + '" height="' + H + '" role="img" aria-label="' + esc(o.aria) + '">';
    var ticks = niceTicks(lo, hi, 3), td = ticks.length > 1 && ticks[1] - ticks[0] < 1 ? 1 : 0;
    ticks.forEach(function (t) {
      var y = Y(t).toFixed(1);
      s += '<line x1="' + padL + '" x2="' + (W - padR + 6) + '" y1="' + y + '" y2="' + y + '" stroke="var(--line-soft)"/><text x="' + (padL - 6) + '" y="' + (+y + 4) + '" text-anchor="end">' + num(t, td) + "</text>";
    });
    if (o.ref != null && o.ref > lo && o.ref < hi) {
      var yr = Y(o.ref).toFixed(1);
      s += '<line x1="' + padL + '" x2="' + (W - padR + 6) + '" y1="' + yr + '" y2="' + yr + '" stroke="var(--muted)" stroke-dasharray="3 4"/><text x="' + (W - padR + 10) + '" y="' + (+yr + 4) + '">' + esc(o.refLabel) + "</text>";
    }
    s += '<text x="' + padL + '" y="' + (H - 6) + '">' + esc(tinyDate(labels[0])) + '</text><text x="' + (W - padR) + '" y="' + (H - 6) + '" text-anchor="end">' + esc(tinyDate(labels[labels.length - 1])) + "</text>";
    var ends = [];
    series.forEach(function (sr) {
      var d = sr.pts.map(function (p, i) { return (i ? "L" : "M") + X(p[0]).toFixed(1) + "," + Y(p[1]).toFixed(1); }).join("");
      s += '<path d="' + d + '" fill="none" stroke="' + sr.color + '" stroke-width="' + (sr.w || 2) + '" stroke-linejoin="round" stroke-linecap="round"/>';
      var last = sr.pts[sr.pts.length - 1];
      s += '<circle cx="' + X(last[0]).toFixed(1) + '" cy="' + Y(last[1]).toFixed(1) + '" r="3.2" fill="' + sr.color + '"/>';
      ends.push({ y: Y(last[1]), x: X(last[0]), name: sr.name, v: last[1], color: sr.color });
    });
    ends.sort(function (a, b) { return a.y - b.y; });
    for (var i = 1; i < ends.length; i++) if (ends[i].y - ends[i - 1].y < 15) ends[i].y = ends[i - 1].y + 15;
    ends.forEach(function (e) {
      s += '<text class="lbl-series" x="' + (e.x + 8).toFixed(1) + '" y="' + (e.y + 4).toFixed(1) + '" fill="' + e.color + '">' + esc(e.name) + " " + num(e.v, o.valD == null ? 1 : o.valD) + "</text>";
    });
    el.innerHTML = s + "</svg>";
  }
  function barChart(el, pts, o) {
    var W = Math.max(220, el.clientWidth), H = o.h || 110, padT = 18, padB = 22, n = pts.length;
    var vals = pts.map(function (p) { return p[1]; }), hi = Math.max(0, Math.max.apply(null, vals)), lo = Math.min(0, Math.min.apply(null, vals));
    var rng = hi - lo || 1, bw = Math.min(34, (W - 8) / n * 0.62), step = (W - 8) / n;
    function Y(v) { return padT + (hi - v) / rng * (H - padT - padB); }
    var s = '<svg viewBox="0 0 ' + W + " " + H + '" width="' + W + '" height="' + H + '" role="img" aria-label="' + esc(o.aria) + '">';
    s += '<line x1="0" x2="' + W + '" y1="' + Y(0).toFixed(1) + '" y2="' + Y(0).toFixed(1) + '" stroke="var(--line)"/>';
    pts.forEach(function (p, i) {
      var x = 4 + i * step + (step - bw) / 2, y0 = Y(0), y1 = Y(p[1]), last = i === n - 1;
      s += '<rect x="' + x.toFixed(1) + '" y="' + Math.min(y0, y1).toFixed(1) + '" width="' + bw.toFixed(1) + '" height="' + Math.max(1, Math.abs(y1 - y0)).toFixed(1) + '" rx="2" fill="' + (last ? "var(--accent)" : "var(--line)") + '"/>';
      if (last || i === 0) s += '<text x="' + (x + bw / 2).toFixed(1) + '" y="' + (H - 6) + '" text-anchor="middle">' + esc(tinyDate(p[0])) + "</text>";
      if (last) s += '<text x="' + (x + bw / 2).toFixed(1) + '" y="' + (Math.min(y0, y1) - 5).toFixed(1) + '" text-anchor="middle" fill="var(--ink)">' + signed(p[1], 1) + "</text>";
    });
    el.innerHTML = s + "</svg>";
  }
  function spark(vals, w, h) {
    w = w || 120; h = h || 30;
    var min = Math.min.apply(null, vals), max = Math.max.apply(null, vals), rng = max - min || 1;
    var col = vals[vals.length - 1] >= vals[0] ? "var(--up)" : "var(--down)";
    var pts = vals.map(function (v, i) { return [i / (vals.length - 1) * (w - 4), h - 3 - (v - min) / rng * (h - 6)]; });
    var line = pts.map(function (p) { return p[0].toFixed(1) + "," + p[1].toFixed(1); }).join(" ");
    var last = pts[pts.length - 1];
    return '<svg class="spark" viewBox="0 0 ' + w + " " + h + '" aria-hidden="true"><polygon points="0,' + h + " " + line + " " + last[0].toFixed(1) + "," + h + '" fill="' + col + '" opacity=".13"/><polyline points="' + line + '" fill="none" stroke="' + col + '" stroke-width="1.6" stroke-linejoin="round"/><circle cx="' + last[0].toFixed(1) + '" cy="' + last[1].toFixed(1) + '" r="2.6" fill="' + col + '"/></svg>';
  }

  // ---------- L'Italia oggi ----------
  function card(o) {
    return '<article class="card ' + o.size + (o.stale ? " stale" : "") + '"><h3>' + o.title + '</h3><div class="big">' + o.big + '</div><p class="read">' + o.read + '</p><div class="chart" id="' + o.chart + '"></div><p class="src">' + o.src + "</p></article>";
  }
  function trendWord(a, b, up, down, flat) { return a > b ? up : a < b ? down : flat; }

  function renderItaly() {
    var html = [], draws = [];
    var sp = spreadSeries(), yit = macro("y10_IT"), yde = macro("y10_DE");
    if (sp && sp.length > 1) {
      var now = sp[sp.length - 1][1], first = sp[0][1];
      html.push(card({ size: "wide", title: "Spread BTP–Bund a 10 anni", stale: yit.non_aggiornato,
        big: num(now, 0) + "<small>punti base</small>",
        read: "Lo Stato italiano paga il " + num(yit.valore, 2) + "% sui titoli a 10 anni, la Germania il " + num(yde.valore, 2) + "%. A " + shortDate(sp[0][0]) + " la differenza era di " + num(first, 0) + " punti: oggi è " + trendWord(now, first + 5, "più alta", "più bassa", "simile") + ". Più è alta, più il mercato chiede all'Italia per prestarle denaro.",
        chart: "ch-spread", src: srcLine(yit) }));
      draws.push(function () { lineChart($("#ch-spread"), [{ name: "Spread", color: "var(--accent)", pts: sp, w: 2.4 }], { aria: "Spread BTP-Bund negli ultimi mesi", valD: 0 }); });
    }
    var iit = macro("infl_IT"), iea = macro("infl_EA");
    if (iit) {
      var rd = "Prezzi in aumento del " + num(iit.valore, 1) + "% rispetto a un anno prima";
      if (iea) rd += ", contro il " + num(iea.valore, 1) + "% della media dell'area euro";
      rd += ". L'obiettivo della BCE è il 2%: " + (iit.valore > 2.05 ? "l'Italia è sopra." : iit.valore < 1.95 ? "l'Italia è sotto." : "l'Italia è in linea.");
      html.push(card({ size: "wide", title: "Inflazione in Italia", stale: iit.non_aggiornato, big: num(iit.valore, 1) + "<small>%</small>", read: rd, chart: "ch-infl", src: srcLine(iit) }));
      draws.push(function () {
        var s = [{ name: "Italia", color: "var(--accent)", pts: iit.storico.slice(-13), w: 2.4 }];
        if (iea) s.push({ name: "Area euro", color: "var(--muted)", pts: iea.storico.slice(-13), w: 1.6 });
        lineChart($("#ch-infl"), s, { aria: "Inflazione Italia e area euro", ref: 2, refLabel: "obiettivo 2%", tickD: 0, labelW: 104 });
      });
    }
    var uit = macro("disocc_IT"), uea = macro("disocc_EA");
    if (uit) {
      html.push(card({ size: "third", title: "Disoccupazione", stale: uit.non_aggiornato, big: num(uit.valore, 1) + "<small>%</small>",
        read: (uit.precedente != null ? trendWord(uit.valore, uit.precedente, "In salita", "In calo", "Stabile") + " rispetto al mese prima (" + num(uit.precedente, 1) + "%)" : "Ultimo dato") + (uea ? ". Media area euro: " + num(uea.valore, 1) + "%." : "."),
        chart: "ch-unemp", src: srcLine(uit) }));
      draws.push(function () { lineChart($("#ch-unemp"), [{ name: "", color: "var(--accent)", pts: uit.storico.slice(-13) }], { aria: "Disoccupazione in Italia", h: 110, labelW: 40 }); });
    }
    var git = macro("pil_IT"), gea = macro("pil_EA");
    if (git) {
      html.push(card({ size: "third", title: "Crescita dell'economia", stale: git.non_aggiornato, big: signed(git.valore, 1) + "<small>%</small>",
        read: "PIL del " + fmtDate(git.data) + " rispetto allo stesso trimestre dell'anno prima" + (gea ? ". Area euro: " + signed(gea.valore, 1) + "% (" + shortDate(gea.data) + ")." : "."),
        chart: "ch-gdp", src: srcLine(git) }));
      draws.push(function () { barChart($("#ch-gdp"), git.storico.slice(-8), { aria: "Crescita del PIL italiano per trimestre" }); });
    }
    var bi = cat("az_italia");
    if (bi) {
      var st = bi.statistiche, t = bi.tecnica;
      html.push(card({ size: "third", title: "Borsa di Milano (FTSE MIB)", big: pct(st.rend_1a) ,
        read: "Negli ultimi 12 mesi, dividendi compresi. Su 5 anni " + pct(st.rend_5a) + " all'anno. " + (t.dal_massimo > -0.005 ? "Oggi è sui massimi del periodo." : "Oggi è a " + pct(t.dal_massimo, 0) + " dal massimo del periodo."),
        chart: "ch-mib", src: "Prezzi di fine mese · " + esc(bi.proxy) }));
      draws.push(function () { lineChart($("#ch-mib"), [{ name: "", color: "var(--accent)", pts: bi.date.slice(-61).map(function (d, i) { return [d, bi.eur.slice(-61)[i]]; }) }], { aria: "Borsa di Milano negli ultimi 5 anni", h: 110, labelW: 12, valD: 0 }); });
    }
    $("#it-grid").innerHTML = html.join("");
    draws.forEach(function (f) { f(); });
    redraw = redraw.concat(draws);
  }

  // ---------- Europa a confronto ----------
  function renderEurope() {
    var de10 = macro("y10_DE");
    var cols = [
      { h: "Inflazione", sub: "su un anno prima", get: function (c) { var m = macro("infl_" + c); return m && { v: m.valore, d: m.data, t: num(m.valore, 1) + "%" }; } },
      { h: "Disoccupazione", sub: "", get: function (c) { var m = macro("disocc_" + c); return m && { v: m.valore, d: m.data, t: num(m.valore, 1) + "%" }; } },
      { h: "Crescita PIL", sub: "su un anno prima", get: function (c) { var m = macro("pil_" + c); return m && { v: m.valore, d: m.data, t: signed(m.valore, 1) + "%" }; } },
      { h: "Titoli di Stato", sub: "rendimento 10 anni", get: function (c) { var m = macro("y10_" + c); return m && { v: m.valore, d: m.data, t: num(m.valore, 2) + "%" }; } },
      { h: "Spread", sub: "sulla Germania", get: function (c) { var m = macro("y10_" + c); if (!m || !de10) return null; if (c === "DE") return { v: 0, t: "riferimento", ref: true }; var v = (m.valore - de10.valore) * 100; return { v: v, t: num(v, 0) + " pb" }; } },
      { h: "Borsa", sub: "ultimi 12 mesi", get: function (c) { var k = cat(BORSA[c]); return k && { v: k.statistiche.rend_1a, t: pct(k.statistiche.rend_1a), c: cls(k.statistiche.rend_1a) }; } },
      { h: "Borsa", sub: "5 anni, all'anno", get: function (c) { var k = cat(BORSA[c]); return k && k.statistiche.rend_5a != null && { v: k.statistiche.rend_5a, t: pct(k.statistiche.rend_5a), c: cls(k.statistiche.rend_5a) }; } }
    ];
    var grid = PAESI.map(function (p) { return cols.map(function (col) { return col.get(p[0]) || null; }); });
    var ranges = cols.map(function (_, j) {
      var vs = grid.map(function (r) { return r[j] && !r[j].ref ? r[j].v : null; }).filter(function (v) { return v != null; });
      return [Math.min.apply(null, vs), Math.max.apply(null, vs)];
    });
    $("#cmp-table thead").innerHTML = "<tr><th scope=\"col\">Paese</th>" + cols.map(function (c) { return '<th scope="col" class="num">' + esc(c.h) + (c.sub ? "<br><small>" + esc(c.sub) + "</small>" : "") + "</th>"; }).join("") + "</tr>";
    $("#cmp-table tbody").innerHTML = PAESI.map(function (p, i) {
      return '<tr class="' + (p[0] === "IT" ? "me" : "") + '"><td class="country"><span class="flag">' + p[0] + "</span>" + esc(p[1]) + "</td>" +
        grid[i].map(function (x, j) {
          if (!x) return '<td class="num"><span class="cell"><span class="v" style="color:var(--muted)">n.d.</span></span></td>';
          var r = ranges[j], pos = r[1] > r[0] ? (x.v - r[0]) / (r[1] - r[0]) : 0.5;
          return '<td class="num"><span class="cell"><span class="v ' + (x.c || "") + '">' + x.t + "</span>" +
            (x.ref ? "" : '<span class="meter" aria-hidden="true"><i style="left:' + (pos * 100).toFixed(0) + '%"></i></span>') +
            (x.d ? '<span class="d">' + esc(tinyDate(x.d)) + "</span>" : "") + "</span></td>";
        }).join("") + "</tr>";
    }).join("");
    var f = macro("infl_IT");
    $("#cmp-foot").textContent = "Ogni Paese pubblica i dati in giorni diversi: sotto ogni cifra c'è il mese o trimestre a cui si riferisce. Borse misurate con FTSE MIB, DAX, CAC 40, IBEX 35 ed Euro Stoxx 50. Fonti: " + (f ? f.fonte : "BCE ed Eurostat") + ".";

    var out = [], ecb = macro("rate_ecb"), iea = macro("infl_EA"), hy = macro("hy_spread_eu");
    if (ecb) {
      var t = "Tasso ufficiale della <b>Banca Centrale Europea</b>.";
      if (iea) { var real = ecb.valore - iea.valore; t += " Tolta l'inflazione dell'area euro resta " + signed(real, 1) + " punti: " + (real < 0 ? "il denaro costa meno di quanto salgono i prezzi, una politica che sostiene l'economia." : "il denaro costa più dell'inflazione, una politica che frena l'economia."); }
      out.push(fact({ stale: ecb.non_aggiornato, val: num(ecb.valore, 2), unit: "%", text: t, src: srcLine(ecb) }));
    }
    if (hy) out.push(fact({ stale: hy.non_aggiornato, val: num(hy.valore, 2), unit: "%", text: "Interesse in più chiesto alle aziende europee <b>meno solide</b> rispetto allo Stato. Sale quando il mercato teme fallimenti.", src: srcLine(hy) }));
    else out.push(fact({ pending: true, val: "In arrivo", text: "<b>Spread delle obbligazioni high yield in euro</b>: compare con il primo aggiornamento automatico.", src: "ICE BofA, via Federal Reserve di St. Louis" }));
    var eu = data.categorie.filter(function (c) { return c.gruppo === "Azioni" && (c.paese || c.id === "az_europa"); });
    var above = eu.filter(function (c) { return c.tecnica.sopra_media; }).length;
    out.push(fact({ val: above + "/" + eu.length, unit: "", text: "Borse europee con il prezzo <b>sopra la media degli ultimi 10 mesi</b>, il segnale di tendenza più usato nell'analisi tecnica.", src: "Calcolato dal sito sui prezzi in euro" }));
    $("#eu-facts").innerHTML = out.join("");
  }

  function fact(o) {
    return '<div class="fact' + (o.stale ? " stale" : "") + (o.pending ? " pending" : "") + '"><div class="fact-val">' + o.val + (o.unit ? "<small>" + o.unit + "</small>" : "") +
      '</div><p class="fact-text">' + o.text + '</p><div class="fact-src">' + o.src + "</div></div>";
  }

  // ---------- Categorie ----------
  function riskBars(c) {
    var s = '<span class="risk" title="Rischio ' + c + ' su 7" aria-label="Rischio ' + c + ' su 7">';
    for (var i = 1; i <= 7; i++) s += '<i class="' + (i <= c ? "on" : "") + '" style="height:' + (4 + i * 2) + 'px"></i>';
    return s + "<b>" + c + "</b></span>";
  }
  function trend(t) {
    if (t.sopra_media == null) return "";
    return t.sopra_media ? '<span class="trend up">Sopra la media</span>' : '<span class="trend down">Sotto la media</span>';
  }
  function renderTable() {
    var rows = [], group = null;
    data.categorie.forEach(function (c) {
      var s = c.statistiche;
      if (c.gruppo !== group) { group = c.gruppo; rows.push('<tr class="group-row"><td colspan="9">' + esc(group) + "</td></tr>"); }
      var short = s.anni_storia < 5;
      rows.push('<tr><td><span class="cat-name">' + esc(c.nome) + '</span><span class="cat-sub">' + (short ? '<span class="short-hist">Solo ' + num(s.anni_storia, 0) + " anni di dati</span>" : "Dati da " + esc(fmtDate(c.date[0]))) + "</span></td>" +
        '<td class="num ' + cls(s.rend_1a) + '">' + pct(s.rend_1a) + "</td>" +
        '<td class="num ' + cls(s.rend_5a) + '">' + pct(s.rend_5a) + "</td>" +
        '<td class="num">' + num(s.vol_5a * 100, 1) + "%</td>" +
        '<td class="num ' + (s.max_ribasso < 0 ? "neg" : "") + '">' + (s.max_ribasso < -0.0005 ? pct(s.max_ribasso, 0) : "0%") + "</td>" +
        '<td class="num">' + (s.anni_in_perdita == null ? "n.d." : num(s.anni_in_perdita * 100, 0) + "%") + "</td>" +
        "<td>" + riskBars(c.classe_rischio) + "</td>" +
        "<td>" + trend(c.tecnica) + "</td>" +
        "<td>" + spark(c.eur.slice(-61)) + "</td></tr>");
    });
    $("#cats-table tbody").innerHTML = rows.join("");
  }

  // ---------- Fondi più grandi ----------
  function renderFunds() {
    var cats = data.categorie.filter(function (c) { return c.prodotti && c.prodotti.length; });
    if (!cats.some(function (c) { return c.id === fundSel; })) fundSel = cats[0].id;
    var tabs = $("#fund-tabs");
    tabs.innerHTML = cats.map(function (c) {
      return '<button type="button" role="tab" id="tab-' + c.id + '" data-id="' + c.id + '" aria-selected="' + (c.id === fundSel) + '" tabindex="' + (c.id === fundSel ? 0 : -1) + '">' + esc(SHORT[c.id] || c.nome) + "</button>";
    }).join("");
    function show(id, focus) {
      fundSel = id;
      Array.prototype.forEach.call(tabs.children, function (b) { var on = b.getAttribute("data-id") === id; b.setAttribute("aria-selected", on); b.tabIndex = on ? 0 : -1; if (on && focus) b.focus(); });
      drawFunds(cat(id));
    }
    tabs.addEventListener("click", function (e) { var b = e.target.closest("button"); if (b) show(b.getAttribute("data-id")); });
    tabs.addEventListener("keydown", function (e) {
      if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
      var ids = cats.map(function (c) { return c.id; }), i = ids.indexOf(fundSel) + (e.key === "ArrowRight" ? 1 : -1);
      show(ids[(i + ids.length) % ids.length], true); e.preventDefault();
    });
    drawFunds(cat(fundSel));
    $("#fund-foot").textContent = "Patrimonio e costi al " + fmtDate(data.prodotti_aggiornati_al) + ". " + (data.prodotti_fonte || "") + " L'ordine segue solo il patrimonio gestito. Il costo annuo (TER) è già tolto dal valore del fondo; non comprende commissioni della banca e tasse.";
  }
  function drawFunds(c) {
    $("#fund-panel").setAttribute("aria-labelledby", "tab-" + c.id);
    var ps = c.prodotti, max = Math.max.apply(null, ps.map(function (p) { return p.aum || 0; }));
    var tot = ps.reduce(function (a, p) { return a + (p.aum || 0); }, 0);
    var intro = '<div class="fund-intro"><span><b>' + esc(c.nome) + "</b></span><span>" + ps.length + (ps.length === 1 ? " fondo" : " fondi") + " · " + aum(tot) + " gestiti in tutto</span><span>Categoria: 12 mesi " + pct(c.statistiche.rend_1a) + ", rischio " + c.classe_rischio + " su 7</span></div>";
    $("#fund-panel").innerHTML = intro + '<ol class="fund-list">' + ps.map(function (p, i) {
      var tipo = p.tipo || "ETF";
      return '<li class="fund"><span class="rank">' + (i + 1) + '</span>' +
        '<div class="name">' + esc(p.nome) + '<span class="meta">' + esc(p.emittente) + " · " + esc(tipo) + (p.indice ? " · " + esc(p.indice) : "") + "</span></div>" +
        '<div><span class="k">Patrimonio</span><span class="v">' + aum(p.aum) + '</span><span class="aum-bar" aria-hidden="true"><i style="width:' + ((p.aum || 0) / max * 100).toFixed(0) + '%"></i></span></div>' +
        '<div><span class="k">Costo annuo</span><span class="v">' + num(p.ter, 2) + "%</span></div>" +
        '<div><span class="k">Proventi</span><span class="v" style="font-family:var(--text);font-size:14px">' + esc(p.politica) + "</span></div>" +
        '<div class="isin-box"><span class="k">ISIN · borsa</span><span class="isin">' + esc(p.isin) + '</span> <span class="k" style="display:inline">' + esc(p.borsa) + '</span><span class="links"><br><a href="https://www.justetf.com/it/etf-profile.html?isin=' + encodeURIComponent(p.isin) + '" target="_blank" rel="noopener">Scheda e KID su justETF</a></span></div></li>';
    }).join("") + "</ol>";
  }
  function aum(x) {
    if (x == null) return "n.d.";
    return x >= 1 ? num(x, x >= 100 ? 0 : 1) + " mld €" : num(x * 1000, 0) + " mln €";
  }

  // ---------- Dal mondo ----------
  function renderWorld() {
    var out = [];
    var fed = macro("rate_fed"), ius = macro("infl_us"), u10 = macro("y10_us"), u2 = macro("y2_us"), vix = macro("vix"), gpr = macro("gpr");
    if (fed) out.push(fact({ stale: fed.non_aggiornato, val: num(fed.valore, 2), unit: "%", text: "Tasso ufficiale della <b>Federal Reserve</b> americana. Quando sale, il dollaro tende a rafforzarsi.", src: srcLine(fed) }));
    if (ius) out.push(fact({ stale: ius.non_aggiornato, val: num(ius.valore, 1), unit: "%", text: "Inflazione negli <b>Stati Uniti</b>.", src: srcLine(ius) }));
    if (u10 && u2) {
      var cu = u10.valore - u2.valore;
      out.push(fact({ val: signed(cu, 2), unit: "", text: "Treasury a 10 anni (" + num(u10.valore, 2) + "%) meno quello a 2 anni. " + (cu >= 0 ? "Positivo, come di norma." : "Negativo, cioè <b>curva invertita</b>: in passato ha spesso preceduto un rallentamento, ma non sempre."), src: srcLine(u10) }));
    }
    if (vix) out.push(fact({ stale: vix.non_aggiornato, val: num(vix.valore, 1), unit: "", text: "Indice <b>VIX</b>, la paura misurata sulle opzioni di Wall Street. " + (vix.valore < 20 ? "Sotto 20, livello tipico delle fasi calme." : "Sopra 20, livello tipico delle fasi di tensione."), src: srcLine(vix) }));
    if (gpr) out.push(fact({ stale: gpr.non_aggiornato, val: num(gpr.valore, 0), unit: "", text: "<b>Rischio geopolitico</b> (100 = media storica)." + (gpr.percentile != null ? " Più alto del " + gpr.percentile + "% dei mesi dal 1985." : ""), src: srcLine(gpr) }));
    else out.push(fact({ pending: true, val: "In arrivo", text: "<b>Rischio geopolitico</b>: compare con il primo aggiornamento automatico.", src: "Caldara e Iacoviello, Federal Reserve Board" }));
    ["gdp_us", "gdp_cn"].forEach(function (id) {
      var g = macro(id); if (!g) return;
      out.push(fact({ stale: g.non_aggiornato, val: signed(g.valore, 1), unit: "%", text: esc(g.nome) + ".", src: srcLine(g) }));
    });
    $("#facts-world").innerHTML = out.join("");
  }

  function renderProxies() {
    $("#proxies tbody").innerHTML = data.categorie.map(function (c) {
      return "<tr><td>" + esc(c.nome) + "</td><td>" + esc(c.proxy) + " (" + esc(c.ticker) + ")</td><td>" + esc(shortDate(c.date[0])) + " – " + esc(shortDate(c.date[c.date.length - 1])) + "</td></tr>";
    }).join("");
  }

  // ---------- Grafico 3D in apertura ----------
  function initLandscape() {
    var box = $("#scene-box"), canvas = $("#scene"), labelsEl = $("#scene-labels"), loading = $("#scene-loading");
    var MONTHS = 60;
    var rows = RIDGES.map(function (r) { return { c: cat(r[0]), tone: r[1] }; }).filter(function (r) { return r.c && r.c.eur.length > MONTHS; });
    function fallback() {
      loading.classList.add("done"); canvas.style.display = "none";
      var ch = rows.map(function (r) { var p = r.c.eur.slice(-MONTHS - 1); return { n: SHORT[r.c.id], v: p[p.length - 1] / p[0] - 1, t: r.tone }; });
      var mx = Math.max.apply(null, ch.map(function (x) { return Math.abs(x.v); })) || 1;
      box.insertAdjacentHTML("beforeend", '<div class="scene-fallback">' + ch.map(function (x) {
        return '<div class="fb-row"><span>' + esc(x.n) + '</span><span class="fb-bar"><i style="width:' + (Math.abs(x.v) / mx * 100).toFixed(0) + "%;background:" + x.t + '"></i></span><b>' + pct(x.v, 0) + "</b></div>";
      }).join("") + "</div>");
    }
    if (!rows.length) return fallback();
    var startLabel = shortDate(rows[0].c.date[rows[0].c.date.length - 1 - MONTHS]);
    $("#scene-caption").textContent = "Borse europee e mondo da " + startLabel + " a oggi, in euro con dividendi. Davanti l'Italia.";
    if (!window.THREE) return fallback();
    var T = window.THREE, renderer, small = box.clientWidth < 600;
    try { renderer = new T.WebGLRenderer({ canvas: canvas, antialias: !small, powerPreference: "low-power" }); } catch (e) { return fallback(); }
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, small ? 1.5 : 2));
    var BG = new T.Color(getComputedStyle(box).backgroundColor || "#13202c");
    renderer.setClearColor(BG, 1);

    var scene = new T.Scene();
    scene.fog = new T.Fog(BG, 20, 36);
    var camera = new T.PerspectiveCamera(36, 1, 0.1, 100);
    var world = new T.Group(); scene.add(world);
    var Wx = 10, gap = 1.5, n = MONTHS + 1, depth = (rows.length - 1) * gap;
    var allY = [];
    rows.forEach(function (r) { var p = r.c.eur.slice(-n); p.forEach(function (v) { allY.push(Math.abs(Math.log(v / p[0]))); }); });
    var k = 2.6 / Math.max(0.2, Math.max.apply(null, allY));
    var grid = new T.GridHelper(Math.max(Wx, depth) + 4, 22, 0x2f4253, 0x1d2b38);
    grid.position.set(0, 0, -depth / 2); world.add(grid);

    var walls = [], labels = [], tips = [], white = new T.Color("#ffffff");
    rows.forEach(function (r, j) {
      var p = r.c.eur.slice(-n), z = -j * gap, tone = new T.Color(r.tone), low = tone.clone().lerp(BG, 0.86);
      var pos = [], col = [], line = [];
      for (var i = 0; i < n - 1; i++) {
        var xa = -Wx / 2 + i / (n - 1) * Wx, xb = -Wx / 2 + (i + 1) / (n - 1) * Wx;
        var ya = Math.log(p[i] / p[0]) * k, yb = Math.log(p[i + 1] / p[0]) * k;
        pos.push(xa, 0, z, xa, ya, z, xb, 0, z, xa, ya, z, xb, yb, z, xb, 0, z);
        [low, tone, low, tone, tone, low].forEach(function (cc) { col.push(cc.r, cc.g, cc.b); });
      }
      for (var q = 0; q < n; q++) line.push(-Wx / 2 + q / (n - 1) * Wx, Math.log(p[q] / p[0]) * k + 0.01, z);
      var g = new T.BufferGeometry();
      g.setAttribute("position", new T.Float32BufferAttribute(pos, 3));
      g.setAttribute("color", new T.Float32BufferAttribute(col, 3));
      var mesh = new T.Mesh(g, new T.MeshBasicMaterial({ vertexColors: true, side: T.DoubleSide, transparent: true, opacity: j === 0 ? 0.95 : 0.85 }));
      world.add(mesh);
      var lg = new T.BufferGeometry(); lg.setAttribute("position", new T.Float32BufferAttribute(line, 3));
      var ln = new T.Line(lg, new T.LineBasicMaterial({ color: tone.clone().lerp(white, 0.3) }));
      world.add(ln);
      walls.push({ mesh: mesh, line: ln });
      var change = p[n - 1] / p[0] - 1;
      tips.push(new T.Vector3(Wx / 2, Math.log(p[n - 1] / p[0]) * k, z));
      var lab = document.createElement("span");
      lab.className = (change >= 0 ? "up" : "down") + (j === 0 ? " it" : "");
      lab.style.color = r.tone;
      lab.innerHTML = esc(SHORT[r.c.id]) + "<b>" + pct(change, 0) + "</b>";
      labelsEl.appendChild(lab); labels.push(lab);
    });

    var narrow = false;
    function resize() {
      var w = box.clientWidth, h = box.clientHeight;
      narrow = w < 560;
      renderer.setSize(w, h, false);
      camera.aspect = w / h;
      camera.fov = narrow ? 44 : 36;
      camera.updateProjectionMatrix();
      world.position.x = narrow ? -2.8 : -1.5;
    }
    resize();
    if (window.ResizeObserver) new ResizeObserver(resize).observe(box); else window.addEventListener("resize", resize);

    var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    var dragX = 0, dragging = false, lastX = 0, visible = true;
    box.addEventListener("pointerdown", function (e) { dragging = true; lastX = e.clientX; });
    window.addEventListener("pointermove", function (e) { if (!dragging) return; dragX += (e.clientX - lastX) * 0.005; dragX = Math.max(-0.8, Math.min(0.8, dragX)); lastX = e.clientX; if (reduce) frame(0); });
    window.addEventListener("pointerup", function () { dragging = false; });
    if (window.IntersectionObserver) new IntersectionObserver(function (e) { visible = e[0].isIntersecting; }).observe(box);

    var v = new T.Vector3(), t0 = performance.now(), GROW = 2400, first = true;
    function frame(now) {
      var t = reduce ? GROW : now - t0;
      var e = Math.min(1, t / GROW), ease = 1 - Math.pow(1 - e, 3);
      var segs = Math.max(1, Math.round(ease * (n - 1)));
      walls.forEach(function (w) { w.mesh.geometry.setDrawRange(0, segs * 6); w.line.geometry.setDrawRange(0, segs + 1); });
      world.rotation.y = -0.28 + (reduce ? 0 : Math.sin(t / 7000) * 0.07) + dragX;
      camera.position.set(-0.4, 7.4, 11.5);
      camera.lookAt(0.4, 0.3, -depth / 2);
      renderer.render(scene, camera);
      if (first) { first = false; loading.classList.add("done"); }
      var W = box.clientWidth, H = box.clientHeight;
      var pts = tips.map(function (tp, i) {
        v.copy(tp); world.localToWorld(v); v.project(camera);
        return { i: i, x: Math.min(W - (narrow ? 118 : 136), (v.x + 1) / 2 * W), y: (1 - v.y) / 2 * H };
      }).sort(function (a, b) { return a.y - b.y; });
      var minGap = narrow ? 17 : 20;
      for (var p = 1; p < pts.length; p++) if (pts[p].y - pts[p - 1].y < minGap) pts[p].y = pts[p - 1].y + minGap;
      pts.forEach(function (pt) {
        var el = labels[pt.i];
        el.style.left = pt.x.toFixed(1) + "px";
        el.style.top = Math.min(H - 44, pt.y).toFixed(1) + "px";
        el.style.opacity = e < 0.97 ? 0 : 1;
      });
    }
    function loop(now) { if (visible || first) frame(now); if (!reduce) requestAnimationFrame(loop); }
    requestAnimationFrame(loop);
  }
})();
