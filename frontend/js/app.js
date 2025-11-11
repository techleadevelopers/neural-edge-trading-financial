// =========================================================
// Neural Edge Frontend – Premium JS (com Ícones)
// =========================================================

// --- API base detection (localhost / 127.0.0.1 / Live Server 5500)
const _host = location.hostname || 'localhost';
const _isLocal = ['localhost', '127.0.0.1'].includes(_host) || location.port === '5500';
const API = _isLocal ? `http://${_host}:8000` : '/api';

// --- Config
const WATCHLIST = ['BTCUSDT', 'NEARUSDT', 'ICPUSDT', 'FILUSDT', 'TRUMPUSDT'];
let currentSymbol = WATCHLIST[0];
let chart, series;

// =========================================================
// Utils
// =========================================================
function textSignal(sig) {
  if (sig === 'SHORT_STRONG') return 'Short Forte';
  if (sig === 'SHORT_WEAK') return 'Short Fraco';
  return 'Neutro';
}
function regimePT(r) {
  const v = (r || '').toUpperCase();
  if (v === 'ALT_ROTATION') return 'Rotação de Alts';
  if (v === 'BTC_TREND') return 'Tendência do BTC';
  if (v === 'RISK_OFF') return 'Aversão ao Risco';
  return 'Neutro';
}
function num(x, d = 2) {
  const n = Number(x);
  return isFinite(n) ? n.toFixed(d) : '-';
}
function dt(s) {
  try {
    const t = new Date(s);
    if (!isNaN(t)) return t.toLocaleString();
  } catch {}
  return String(s || '-');
}

// =========================================================
// Candles & Chart
// =========================================================
async function fetchCandles(symbol, limit = 300) {
  const r = await fetch(`${API}/data/candles?symbol=${symbol}&interval=1m&limit=${limit}`);
  return await r.json();
}

async function drawChart(symbol = currentSymbol) {
  try {
    const data = await fetchCandles(symbol);
    const container = document.getElementById('chart');
    container.innerHTML = '';
    chart = LightweightCharts.createChart(container, {
      layout: { background: { color: '#0b1220' }, textColor: '#e2e8f0' },
      grid: { vertLines: { color: '#1f2937' }, horzLines: { color: '#1f2937' } },
      timeScale: { timeVisible: true, secondsVisible: false },
    });

    series = chart.addCandlestickSeries({
      upColor: '#16a34a',
      downColor: '#ef4444',
      borderUpColor: '#16a34a',
      borderDownColor: '#ef4444',
      wickUpColor: '#10b981',
      wickDownColor: '#f87171',
    });

    const mapped = (data || []).map((d) => ({
      time: Math.floor(new Date(d.open_time).getTime() / 1000),
      open: +d.open,
      high: +d.high,
      low: +d.low,
      close: +d.close,
    }));
    series.setData(mapped);

    // EMA20 overlay
    const closes = mapped.map((d) => d.close),
      times = mapped.map((d) => d.time);
    if (closes.length >= 20) {
      const alpha = 2 / (20 + 1);
      let ema = closes.slice(0, 20).reduce((a, b) => a + b, 0) / 20;
      const pts = [];
      for (let i = 20; i < closes.length; i++) {
        ema = alpha * closes[i] + (1 - alpha) * ema;
        pts.push({ time: times[i], value: ema });
      }
      chart.addLineSeries({ color: '#a78bfa', lineWidth: 2 }).setData(pts);
    }

    document.getElementById('status').innerText = `Gráfico: ${symbol}`;
  } catch (e) {
    document.getElementById('status').innerText = 'Erro ao desenhar gráfico';
  }
}

// =========================================================
// Model ops
// =========================================================
async function train() {
  try {
    const r = await fetch(
      `${API}/model/train?symbol=${currentSymbol}&interval=1m&limit=500`,
      { method: 'POST' }
    );
    const j = await r.json();
    document.getElementById('status').innerText = j.ok
      ? 'Modelo recalibrado'
      : 'Falha no treino';
    if (j && j.ok) {
      // atualiza bloco compacto de meta
      renderModelMeta(j.meta || {}, j.threshold);
    }
  } catch {
    document.getElementById('status').innerText = 'Erro ao treinar';
  }
}

async function predict(symbol = currentSymbol) {
  try {
    const r = await fetch(
      `${API}/model/predict?symbol=${symbol}&interval=1m&limit=500`,
      { method: 'POST' }
    );
    const j = await r.json();
    renderSignalPremium(j);
    if (j && j.threshold != null) {
      renderModelMeta(undefined, j.threshold);
    }
  } catch (e) {
    document.getElementById('signalPre').innerHTML = `<div class="muted">Erro na predição: ${String(
      e
    )}</div>`;
  }
}

document.getElementById('btnTrain').onclick = train;
document.getElementById('btnPredict').onclick = () => predict();

// =========================================================
// Symbol bar
// =========================================================
function buildSymbolsBar() {
  const bar = document.getElementById('symbolsBar');
  if (!bar) return;
  bar.innerHTML = '';
  WATCHLIST.forEach((sym) => {
    const b = document.createElement('button');
    b.innerHTML = `${sym}`;
    if (sym === currentSymbol) b.classList.add('active');
    b.onclick = async () => {
      currentSymbol = sym;
      Array.from(bar.children).forEach((x) => x.classList.remove('active'));
      b.classList.add('active');
      await drawChart(sym);
      await predict(sym);
    };
    bar.appendChild(b);
  });
}

// =========================================================
// Watchlist
// =========================================================
function pillClass(signal) {
  if (!signal) return 'neutral';
  if (signal === 'SHORT_STRONG') return 'strong';
  if (signal === 'SHORT_WEAK') return 'weak';
  return 'neutral';
}

async function updateWatchlist_legacy() {
  const grid = document.getElementById('watchlistGrid');
  if (!grid) return;
  grid.innerHTML = '';

  for (const sym of WATCHLIST) {
    const tile = document.createElement('div');
    tile.className = 'tile';
    tile.innerHTML = `<h4>${sym}</h4><div class="row"><span class="muted">carregando...</span></div>`;
    grid.appendChild(tile);

    try {
      const [pred, cand] = await Promise.all([
        fetch(`${API}/model/predict?symbol=${sym}&interval=1m&limit=500`, {
          method: 'POST',
        }).then((x) => x.json()),
        fetchCandles(sym, 80),
      ]);

      const s = pred.fused_final?.signal || pred.fused?.signal || 'NEUTRAL';
      const c = pred.fused_final?.confidence ?? pred.fused?.confidence ?? 0;
      const regime = pred.regime?.regime || 'NEUTRAL';

      // sparkline
      let spark = '';
      let trend = 0;
      if (Array.isArray(cand) && cand.length > 1) {
        const closes = cand.map((d) => +d.close);
        const min = Math.min(...closes),
          max = Math.max(...closes),
          w = 200,
          h = 40,
          range = max - min || 1e-9;
        const pts = closes
          .map((v, i) => {
            const x = (i / (closes.length - 1)) * w;
            const y = h - ((v - min) / range) * h;
            return `${x.toFixed(2)},${y.toFixed(2)}`;
          })
          .join(' ');
        trend = (closes[closes.length - 1] / closes[0] - 1) * 100;
        const stroke =
          trend > 0.2 ? '#16a34a' : trend < -0.2 ? '#ef4444' : '#22d3ee';
        spark = `<div class="sparkline"><svg viewBox="0 0 ${w} ${h}" preserveAspectRatio="none"><polyline fill="none" stroke="${stroke}" stroke-width="1.5" points="${pts}"/></svg></div>`;
      }

      const arrow = trend > 0.2 ? 'UP' : trend < -0.2 ? 'DN' : 'FLAT';
      const tclass =
        trend > 0.2 ? 'trend-up' : trend < -0.2 ? 'trend-down' : 'trend-flat';

      tile.innerHTML = `
        <h4>${sym}</h4>
        ${spark}
        <div class="row"><span class="muted">Tendência 80m</span><span class="${tclass}">${arrow} ${trend.toFixed(2)}%</span></div>
        <div class="row"><span class="muted">Regime</span><span class="muted">${regimePT(regime)}</span></div>
        <div class="row"><span class="muted">Sinal</span><span class="pill ${pillClass(
          s
        )}">${textSignal(s)}</span></div>
        <div class="row"><span class="muted">Confiança</span><span>${(c * 100).toFixed(
          1
        )}%</span></div>`;
    } catch {
      tile.innerHTML = `<h4>${sym}</h4><div class="muted">erro</div>`;
    }
  }
}

// New Watchlist updater (UI fixa, sem flicker)
const WATCH_CACHE = new Map();

function ensureWatchTile(grid, sym) {
  let tile = WATCH_CACHE.get(sym);
  if (tile) return tile;
  tile = document.createElement('div');
  tile.className = 'tile';
  tile.dataset.sym = sym;
  tile.innerHTML = `
    <h4>${sym}</h4>
    <div class="sparkline"><svg viewBox="0 0 200 40" preserveAspectRatio="none"><polyline fill="none" stroke="#22d3ee" stroke-width="1.5" points=""/></svg></div>
    <div class="row"><span class="muted">TendǦncia 80m</span><span class="trend-flat" data-trend>FLAT 0.00%</span></div>
    <div class="row"><span class="muted">Regime</span><span class="muted" data-regime>-</span></div>
    <div class="row"><span class="muted">Sinal</span><span class="pill neutral" data-signal>Neutro</span></div>
    <div class="row"><span class="muted">Confian��a</span><span data-conf>0.0%</span></div>
  `;
  WATCH_CACHE.set(sym, tile);
  grid.appendChild(tile);
  return tile;
}

function updateWatchTile(tile, { points, stroke, trend, regimeText, signal, confPct }) {
  const poly = tile.querySelector('polyline');
  if (poly) {
    poly.setAttribute('points', points || '');
    if (stroke) poly.setAttribute('stroke', stroke);
  }
  const tEl = tile.querySelector('[data-trend]');
  if (tEl) {
    tEl.classList.remove('trend-up', 'trend-down', 'trend-flat');
    const tclass = trend > 0.2 ? 'trend-up' : trend < -0.2 ? 'trend-down' : 'trend-flat';
    tEl.classList.add(tclass);
    const arrow = trend > 0.2 ? 'UP' : trend < -0.2 ? 'DN' : 'FLAT';
    tEl.textContent = `${arrow} ${trend.toFixed(2)}%`;
  }
  const rEl = tile.querySelector('[data-regime]');
  if (rEl && regimeText != null) rEl.textContent = regimeText;
  const sEl = tile.querySelector('[data-signal]');
  if (sEl && signal) {
    sEl.className = 'pill ' + pillClass(signal);
    sEl.textContent = textSignal(signal);
  }
  const cEl = tile.querySelector('[data-conf]');
  if (cEl && confPct != null) cEl.textContent = `${confPct.toFixed(1)}%`;
}

async function updateWatchlist() {
  const grid = document.getElementById('watchlistGrid');
  if (!grid) return;
  for (const sym of WATCHLIST) {
    const tile = ensureWatchTile(grid, sym);
    try {
      const [pred, cand] = await Promise.all([
        fetch(`${API}/model/predict?symbol=${sym}&interval=1m&limit=500`, { method: 'POST' }).then((x) => x.json()),
        fetchCandles(sym, 80),
      ]);
      const s = pred.fused_final?.signal || pred.fused?.signal || 'NEUTRAL';
      const c = pred.fused_final?.confidence ?? pred.fused?.confidence ?? 0;
      const regime = pred.regime?.regime || 'NEUTRAL';

      let points = '', trend = 0, stroke = '#22d3ee';
      if (Array.isArray(cand) && cand.length > 1) {
        const closes = cand.map((d) => +d.close);
        const min = Math.min(...closes), max = Math.max(...closes);
        const w = 200, h = 40, range = max - min || 1e-9;
        points = closes.map((v, i) => {
          const x = (i / (closes.length - 1)) * w;
          const y = h - ((v - min) / range) * h;
          return `${x.toFixed(2)},${y.toFixed(2)}`;
        }).join(' ');
        trend = (closes[closes.length - 1] / closes[0] - 1) * 100;
        stroke = trend > 0.2 ? '#16a34a' : trend < -0.2 ? '#ef4444' : '#22d3ee';
      }

      updateWatchTile(tile, {
        points,
        stroke,
        trend,
        regimeText: regimePT(regime),
        signal: s,
        confPct: c * 100,
      });
    } catch {
      updateWatchTile(tile, { points: '', trend: 0, regimeText: '-', signal: 'NEUTRAL', confPct: 0 });
    }
  }
}

// =========================================================
// Regime badge
// =========================================================
async function regime() {
  try {
    const r = await fetch(`${API}/regime/snapshot`);
    const j = await r.json();
    const b2 = document.getElementById('regimeBadge2');
    const alt = document.getElementById('altbarFill');
    const desc = document.getElementById('regimeDesc');
    if (b2 && alt && desc) {
      const reg = (j.regime || '').toUpperCase();
      b2.className =
        'reg-badge ' +
        (reg === 'ALT_ROTATION'
          ? 'alt'
          : reg === 'BTC_TREND'
          ? 'btc'
          : 'off');
      b2.textContent =
        reg === 'ALT_ROTATION'
          ? 'Força nas Altcoins'
          : reg === 'BTC_TREND'
          ? 'Apetite por Risco'
          : 'Aversão ao Risco';
      alt.style.width = `${Math.max(
        0,
        Math.min(100, Number(j.altseason_score) || 0)
      )}%`;
      desc.innerHTML = 'Quando há <b>apetite por risco</b>, o mercado tende a buscar ganhos mais altos (RISK ON). Em momentos de <b>aversão ao risco</b>, prevalecem posições defensivas (RISK OFF).';
    }
  } catch {
    const el = document.getElementById('regimeBadge2');
    if (el) {
      el.textContent = 'Erro ao carregar regime';
      el.style.background = '#7f1d1d';
    }
  }
}

// =========================================================
// Premium Render – Último Sinal
// =========================================================
function renderSignalPremium(j) {
  const el = document.getElementById('signalPre');
  if (!j || j.error) {
    el.innerHTML = `<div class="muted">${j?.error || 'Sem dados'}</div>`;
    return;
  }
  const sig = j.fused_final?.signal || j.fused?.signal || 'NEUTRAL';
  const conf = j.fused_final?.confidence ?? j.fused?.confidence ?? 0;
  const regime = j.regime?.regime || 'NEUTRAL';
  const last = j.last || {};
  const hora = dt(last.open_time);

  const pillCls =
    'pill ' +
    (sig === 'SHORT_STRONG'
      ? 'strong'
      : sig === 'SHORT_WEAK'
      ? 'weak'
      : 'neutral');
  const score = j.regime?.altseason_score || 0;
  const shortPct = j.prob_down != null ? Math.round(j.prob_down * 100) : 0;
  const longPct = 100 - shortPct;
  const confPct = Math.round((+conf || 0) * 100);

  const rsi = num(last.rsi14, 1),
    volz = num(last.vol_z, 2),
    wick = num(last.upper_wick, 2),
    ret15 =
      last.ret_15 != null ? (Number(last.ret_15) * 100).toFixed(1) + '%' : '-';

  const subtitle = `<div class="subtitle">Atualizado em ${hora} — Fonte: NeuralEdge AI</div>`;
  const status = `
    <div class="statusGrid">
      <div class="statusItem"><div class="k">Mercado</div><div class="v"> Neutro / Sem euforia</div></div>
      <div class="statusItem"><div class="k">Sentimento global</div><div class="v"> ${regimePT(regime)}</div></div>
      <div class="statusItem"><div class="k">Força Altseason</div><div class="v"> ${score} / 100</div></div>
    </div>`;

  const prob = `
    <div class="prob">
      <div class="hdr"><span>Tendência Atual</span></div>
      <div class="bar">
        <span class="short" style="width:${shortPct}%"></span>
        <span class="long" style="width:${longPct}%"></span>
      </div>
      <div class="labels"><span class="s"> ${shortPct}% Short</span><span class="l"> ${longPct}% Long</span></div>
      <div class="conf">Nível de Confiança: ${confPct}%</div>
    </div>`;

  el.innerHTML = `
    <div class="title"><span class="${pillCls}">${textSignal(sig)}</span></div>
    ${subtitle}
    ${status}
    ${prob}
    <div class="miniGrid">
      <div class="mini info"><div class="label">Símbolo</div><div class="value">${
        j.symbol || '-'
      }</div></div>
      <div class="mini info"><div class="label">Intervalo</div><div class="value">${
        j.interval || '-'
      }</div></div>
      <div class="mini info"><div class="label">Hora</div><div class="value">${hora}</div></div>
      <div class="mini info"><div class="label">RSI(14)</div><div class="value">${rsi}</div></div>
      <div class="mini info"><div class="label">Vol Z</div><div class="value">${volz}</div></div>
      <div class="mini info"><div class="label">Pavio sup.</div><div class="value">${wick}</div></div>
      <div class="mini info"><div class="label">Ret. 15</div><div class="value">${ret15}</div></div>
    </div>`;
}

// =========================================================
// Targets (Ativos-Alvo) – Versão Otimizada com Cache
// =========================================================
const TARGETS = ['BTCUSDT','SOLUSDT','ETHUSDT','NEARUSDT','TRUMPUSDT','ICPUSDT','FILUSDT'];
const targetsCache = new Map();

function coinIcon(sym) {
  try {
    const base = (sym || '').replace('USDT','').toLowerCase();
    if (base === 'trump') {
      return 'assets/icons/trump.svg';
    }
    // corrige ICP com asset local para evitar troca incorreta
    if (base === 'icp') {
      return 'assets/icons/icp.svg';
    }
    const known = { btc:'btc', eth:'eth', sol:'sol', near:'near', fil:'fil' };
    if (known[base]) {
      return `https://cdn.jsdelivr.net/gh/spothq/cryptocurrency-icons@master/svg/color/${known[base]}.svg`;
    }
    return `https://cryptoicons.org/api/icon/${base}/24`;
  } catch { return ''; }
}

async function renderTargets() {
  const box = document.getElementById('targetsList');
  if (!box) return;
  // Cria/atualiza sem limpar a UI (evita flicker)
  for (const sym of TARGETS) {
    // Garante row fixa para o símbolo
    let row = targetsCache.get(sym);
    if (!row) {
      row = document.createElement('div');
      row.className = 'row';
      row.dataset.sym = sym;
      row.innerHTML = `
        <div class="sparkWrap"><svg class="miniSpark" viewBox="0 0 100 28" preserveAspectRatio="none"><polyline fill="none" stroke="#22d3ee" stroke-width="1.2" points=""/></svg></div>
        <div style="text-align:right">
          <div class="trend"></div>
          <div class="muted" data-conf="1"><i class="fas fa-check-circle" style="margin-right: 4px; color: #22c55e; font-size: 10px;"></i>Confiança 0%</div>
        </div>`;
      row.insertAdjacentHTML('afterbegin', `<div class="sym"><img src="${coinIcon(sym)}" alt="" width="16" height="16" style="vertical-align:middle;margin-right:6px;border-radius:50%;" onerror="this.style.display='none'"/>${sym.replace('USDT', '')}</div>`);
      targetsCache.set(sym, row);
      box.appendChild(row);
    }
    try {
      const [pred, cand] = await Promise.all([
        fetch(`${API}/model/predict?symbol=${sym}&interval=1m&limit=200`, { method: 'POST' }).then(x => x.json()),
        fetchCandles(sym, 80)
      ]);
      const closes = (cand || []).map(d => +d.close);
      let trend = 0, points = '';
      if (closes.length > 1) {
        const min = Math.min(...closes), max = Math.max(...closes), w = 100, h = 28, range = max - min || 1e-9;
        points = closes.map((v, i) => { const x = (i / (closes.length - 1)) * w; const y = h - ((v - min) / range) * h; return `${x.toFixed(2)},${y.toFixed(2)}`; }).join(' ');
        trend = (closes[closes.length - 1] / closes[0] - 1) * 100;
      }
      const c = pred.fused_final?.confidence ?? pred.fused?.confidence ?? 0;
      const rsi = num(pred.last?.rsi14, 1);
      const volz = num(pred.last?.vol_z, 2);
      // Aplica atualizações pontuais
      const poly = row.querySelector('polyline'); if (poly) { poly.setAttribute('points', points); poly.setAttribute('stroke', trend >= 0 ? '#16a34a' : '#ef4444'); }
      const trendDiv = row.querySelector('.trend'); if (trendDiv) { 
        trendDiv.classList.toggle('up', trend >= 0); 
        trendDiv.classList.toggle('down', trend < 0); 
        const trendIcon = trend >= 0 ? '<i class="fas fa-trending-up" style="margin-right: 4px; color: #16a34a;"></i>' : '<i class="fas fa-trending-down" style="margin-right: 4px; color: #ef4444;"></i>';
        trendDiv.innerHTML = `${trendIcon}${trend >= 0 ? '+ ' : '- '}${trend.toFixed(2)}%`; 
      }
      const confDiv = row.querySelector('[data-conf]'); if (confDiv) { 
        confDiv.innerHTML = `<i class="fas fa-check-circle" style="margin-right: 4px; color: #22c55e; font-size: 10px;"></i>Confiança ${Math.round((c || 0) * 100)}%`; 
        confDiv.title = `RSI ${rsi} • Vol Z ${volz}`; 
      }
    } catch {
      const trendDiv = row.querySelector('.trend'); if (trendDiv) trendDiv.innerHTML = '<i class="fas fa-exclamation-triangle" style="color: #ef4444;"></i>';
      const confDiv = row.querySelector('[data-conf]'); if (confDiv) confDiv.innerHTML = '<i class="fas fa-exclamation-triangle" style="color: #ef4444; margin-right: 4px;"></i>erro';
    }
  }
}

// =========================================================
// Model Meta helpers (AUC / F1 / Thr / Treino)
// =========================================================
function renderModelMeta(meta, thr) {
  const host = document.getElementById('signalPre');
  if (!host) return;
  let box = document.getElementById('modelMeta');
  if (!box) {
    box = document.createElement('div');
    box.id = 'modelMeta';
    box.className = 'miniGrid';
    host.appendChild(box);
  }
  const m = meta || {};
  const auc = m.val_auc != null ? m.val_auc : m.cv_auc;
  const f1 = m.f1_short;
  const ts = m.timestamp ? new Date(m.timestamp).toLocaleString() : '-';
  const t = typeof thr === 'number' ? thr : undefined;
  const thrStr = t != null ? t.toFixed(2) : (m.threshold != null ? Number(m.threshold).toFixed(2) : '-');
  const val = (x, d=2) => (x == null || isNaN(Number(x)) ? '-' : Number(x).toFixed(d));
  box.innerHTML = `
    <div class="mini info"><div class="label">AUC</div><div class="value">${val(auc,2)}</div></div>
    <div class="mini info"><div class="label">F1_short</div><div class="value">${val(f1,2)}</div></div>
    <div class="mini info"><div class="label">Thr</div><div class="value">${thrStr}</div></div>
    <div class="mini info"><div class="label">Treino</div><div class="value">${ts}</div></div>
  `;
}

async function fetchModelMeta() {
  try {
    const r = await fetch(`${API}/model/meta`);
    const j = await r.json();
    if (j && j.ok) renderModelMeta(j.meta || {}, j.threshold);
  } catch {}
}
// =========================================================
// Kickoff (inicialização)
// =========================================================
buildSymbolsBar();
drawChart(currentSymbol);
predict(currentSymbol);
fetchModelMeta();
updateWatchlist();
setInterval(() => updateWatchlist(), 60000);
renderTargets();  // Chama a nova funcao otimizada
setInterval(renderTargets, 60000);
regime();
setInterval(regime, 60000);



