const API = location.hostname.includes("localhost") ? "http://localhost:8000" : "/api"; // ajuste conforme deploy

async function fetchCandles() {
  const res = await fetch(`${API}/data/candles?symbol=NEARUSDT&interval=1m&limit=300`);
  return await res.json();
}

async function drawChart() {
  try {
    const data = await fetchCandles();
    const container = document.getElementById('chart');
    const chart = LightweightCharts.createChart(container, {
      layout: { background: { color: "#ffffff" }, textColor: "#333" },
      timeScale:{ timeVisible:true, secondsVisible:false }
    });
    const series = chart.addCandlestickSeries();
    const mapped = data.map(d => ({
      time: Math.floor(new Date(d.open_time).getTime()/1000),
      open: Number(d.open),
      high: Number(d.high),
      low: Number(d.low),
      close: Number(d.close)
    }));
    series.setData(mapped);
  } catch (e) {
    document.getElementById('status').innerText = 'Erro ao desenhar gráfico';
    console.error(e);
  }
}

async function train() {
  try {
    const r = await fetch(`${API}/model/train`, {method: "POST"});
    const j = await r.json();
    document.getElementById('status').innerText = j.ok ? "Modelo treinado ✅" : "Falha no treino";
  } catch (e) {
    document.getElementById('status').innerText = 'Erro ao treinar';
  }
}

async function predict() {
  try {
    const r = await fetch(`${API}/model/predict`, {method: "POST"});
    const j = await r.json();
    document.getElementById('signalPre').textContent = JSON.stringify(j, null, 2);
  } catch (e) {
    document.getElementById('signalPre').textContent = 'Erro na predição: ' + e;
  }
}

document.getElementById('btnTrain').onclick = train;
document.getElementById('btnPredict').onclick = predict;

drawChart();
predict();

