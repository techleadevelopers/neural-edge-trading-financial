# Neural Edge Trading – Short Sniper

> "eu ganho mais no short meu mano"
>
> "eu ganho mais na queda man, às vezes pego uns long mais lá de baixo. Sou conservador nas estratégias. Quando vai pra topo, aquela euforia lá em cima é o short estratégico"
>
> "mano peguei um crash doido… entrei short nos 125k do BTC, stop no 132k; bateu 126k e desceu pros 99k"
>
> "cripto é perigoso, mas vantajoso — grandes escalas, lucros nucleares"

Projeto pronto para operar sua visão: arquitetado simples e robusto, com FastAPI no backend, HTML puro no frontend e estratégia “Short Sniper” fundindo regras de euforia + modelo estatístico. Suba com um `docker-compose up --build` e comece a treinar e sinalizar.

---

## Visão Geral
- Foco: capturar assimetrias na euforia (“short inteligente no topo”).
- Estratégia: regra determinística de euforia + probabilidade estatística de queda (Logistic Regression).
- Infra: `docker-compose` com Backend FastAPI, Frontend Nginx (HTML puro), Postgres (futuro), Redis (futuro).
- Fluxo:
  1) Coleta candles (BingX; fallback Binance).
  2) Calcula indicadores e regra Short Sniper.
  3) Treina modelo baseline e gera probabilidade de queda.
  4) Fusão conservadora → `SHORT_STRONG | SHORT_WEAK | NEUTRAL`.

---

## Arquitetura
- Serviços (compose):
  - `backend` (FastAPI + Uvicorn): API de dados, treino e predição.
  - `frontend` (Nginx): HTML estático com Lightweight-Charts via CDN.
  - `db` (Postgres 15): Persistência (reservado p/ evolução).
  - `redis` (Redis 7): Cache/filas (reservado p/ evolução).
- Pastas principais:
  - `backend/app.py` – montagem da API e rotas.
  - `backend/routers/*` – endpoints `health`, `data`, `model`, `backtest`.
  - `backend/services/*` – `collector`, `features`, `models`, `rules`, `utils`.
  - `backend/data/{raw,processed,models}` – insumos e artefatos de modelo.
  - `frontend/*` – `index.html`, `signals.html`, `settings.html`, CSS/JS.

---

## Estratégia: Short Sniper (assinatura de euforia)
Regras por candle (acende `short_signal = 1` quando TODAS se cumprem):
- RSI(14) ≥ 72
- Pico de volume (z-score) ≥ 1.5
- Sombra superior relevante (upper wick) ≥ 0.35
- Estiramento de +12% em 15 barras (`ret_15 ≥ 0.12`)

Racional:
- Não adivinha topo — espera estiramento + exaustão (pavio) em contexto de euforia (RSI alto + volume).
- Conservador: confirma fraqueza, reduz falso positivo de rompimentos saudáveis.

A fusão com o modelo estatístico aplica pesos conservadores:
- `SHORT_STRONG`: regra = 1 E `prob_down ≥ 0.55`
- `SHORT_WEAK`: regra = 1 OU `prob_down ≥ 0.60`
- `NEUTRAL`: caso contrário

Ajustes finos (opcional):
- Subir limiar RSI para mercados muito tendenciais (ex.: 75–80).
- Aumentar `vol_z` para filtrar altcoins com “barulho”.
- Multi‑timeframe: pedir confirmação de fraqueza no timeframe acima (e.g., 5m confirma 1m).

---

## Modelagem Estatística
- Features: `rsi14`, `ret_1`, `ret_5`, `ret_15`, `vol_z`, `upper_wick`.
- Target: `y_down = (fwd_ret_5 < 0)` com `fwd_ret_5 = pct_change(5).shift(-5)`.
- Modelo: `LogisticRegression(max_iter=200)`.
- Persistência do artefato: `backend/data/models/baseline_logreg.pkl` (via `joblib`).
- Comportamento seguro: se não houver modelo treinado, `POST /model/predict` retorna aviso e segue reportando a regra.

---

## Coleta de Dados
- Exchange padrão: `BINGX` (swap v3). Fallback automático para `BINANCE` ao falhar.
- Endpoints utilizados:
  - BingX: `openApi/swap/v3/quote/klines`
  - Binance: `/api/v3/klines`
- Colunas padronizadas: `open_time, open, high, low, close, volume`.

---

## Endpoints Principais
- `GET /health/` → `{ ok: true }`
- `GET /data/candles?symbol=NEARUSDT&interval=1m&limit=300`
- `GET /data/signals?symbol=NEARUSDT&interval=1m&limit=300` → últimas 10 com indicadores e `short_signal`.
- `POST /model/train?symbol=NEARUSDT&interval=1m&limit=500` → treina baseline, salva em `data/models`.
- `POST /model/predict?symbol=NEARUSDT&interval=1m&limit=500` → calcula regra + prob e retorna a decisão fundida.

Exemplos (curl):
```bash
curl http://localhost:8000/health/
curl "http://localhost:8000/data/candles?symbol=NEARUSDT&interval=1m&limit=100"
curl -X POST "http://localhost:8000/model/train?symbol=NEARUSDT&interval=1m&limit=500"
curl -X POST "http://localhost:8000/model/predict?symbol=NEARUSDT&interval=1m&limit=500"
```

---

## Frontend (HTML puro)
- `frontend/index.html`: gráfico de candles (Lightweight‑Charts via CDN) + botões “Treinar” e “Predizer”.
- `frontend/signals.html`: lista as últimas 10 observações com indicadores.
- `frontend/settings.html`: instruções rápidas e variáveis principais.
- Chama API local (`http://localhost:8000`) quando acessado em `localhost:3000`.

---

## Quickstart
1) Variáveis de ambiente
```bash
# Linux/macOS
cp .env.example .env
# Windows (PowerShell)
Copy-Item .env.example .env
```

2) Subir a stack
```bash
docker-compose up --build
```

3) Acessos
- Backend (docs): `http://localhost:8000/docs`
- Frontend: `http://localhost:3000`

4) Fluxo sugerido
- Clique “Treinar baseline” na home → gera `backend/data/models/baseline_logreg.pkl`.
- Clique “Predizer agora” → retorna JSON com `prob_down`, `rule_short`, `fused` e `last`.

Volumes/persistência
- Modelo e dados são mantidos em `backend/data/*` e mapeados para o container (`./backend/data:/app/data`).

---

## Variáveis de Ambiente (principais)
```ini
EXCHANGE=BINGX | BINANCE
BINGX_BASE_URL=https://open-api.bingx.com
BINANCE_BASE_URL=https://api.binance.com
DEFAULT_SYMBOL=NEARUSDT
DEFAULT_INTERVAL=1m
CANDLES_LIMIT=500
PG_HOST=db
PG_PORT=5432
PG_DB=signals
PG_USER=signals
PG_PASSWORD=signals
REDIS_HOST=redis
REDIS_PORT=6379
```
Extras opcionais: `OPENAI_API_KEY`, `CRYPTOPANIC_TOKEN` (reservados p/ sentimento/notícias).

---

## Operação, Risco e Disciplina
- Direção preferencial: short em euforia (alinhado ao viés do projeto).
- Stops objetivos: sempre definir hard‑stop no momento da entrada (ex.: short 125k → stop 132k).
- Tamanho de posição: fracionado/proporcional à convicção do sinal (`SHORT_STRONG` > `SHORT_WEAK`).
- Alavancagem: conservadora — controlar o risco de liquidação em eventos bruscos.
- Regime de mercado: elevar limiares em bull markets para filtrar rompimentos genuínos.
- Gestão ativa: mover stop a favor após deslocamento significativo (lock‑in de ganhos).

---

## Roadmap
- Backtest completo: P&L, Sharpe, MaxDD, custos e slippage (rota `backtest` hoje é stub).
- Persistência de sinais/execuções no Postgres (`db`).
- Cache e filas de jobs no Redis (`redis`).
- Streaming (WebSocket) de candles e sinais.
- Parametrização de limiares por símbolo/timeframe.
- Camada de execução (paper trading primeiro; real somente após validação robusta).

---

## Troubleshooting
- Modelo não encontrado em `/model/predict`:
  - Rode `POST /model/train` ou use o botão “Treinar baseline”.
- CORS ao desenvolver fora de `localhost`:
  - Ajustar middleware CORS em `backend/app.py`.
- BingX indisponível:
  - Fallback automático para Binance — verifique conectividade ou troque `EXCHANGE` para `BINANCE`.
- Docker com volumes em Windows:
  - Verificar permissões do diretório `backend/data` se o modelo não persistir.

---

## Segurança e Observabilidade
- Chaves/API: use `.env` local, não commitar segredos.
- Produção: restringir CORS, ativar logs estruturados e métricas (a adicionar).
- Resiliência: coletores com `timeout` e fallback — ampliar com retries backoff exponencial.

---

## Aviso Legal
Este repositório é educativo e experimental. Cripto é altamente volátil. Nenhuma recomendação de investimento. Teste, valide (backtest/forward) e use gestão de risco rigorosa. Você é o único responsável por suas decisões.

---

## Estrutura (referência)
```
neural-edge-trading/
├─ docker-compose.yml
├─ .env.example
├─ backend/
│  ├─ app.py
│  ├─ routers/
│  │  ├─ health.py
│  │  ├─ data.py
│  │  ├─ model.py
│  │  ├─ backtest.py
│  ├─ services/
│  │  ├─ collector.py
│  │  ├─ features.py
│  │  ├─ models.py
│  │  ├─ rules.py
│  │  ├─ utils.py
│  ├─ data/
│  │  ├─ raw/
│  │  ├─ processed/
│  │  └─ models/
│  └─ requirements.txt
└─ frontend/
   ├─ index.html
   ├─ signals.html
   ├─ settings.html
   ├─ assets/
   │  └─ style.css
   └─ js/
      └─ app.js
```

Pronto para `docker-compose up --build`.
