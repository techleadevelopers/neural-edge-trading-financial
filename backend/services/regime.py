import os
import time
import httpx
import pandas as pd
import numpy as np
import joblib
import psycopg2

from .collector import get_klines
from .utils import REGIME_SNAPSHOT_TTL_SEC

CG = os.getenv("COINGECKO_BASE", "https://api.coingecko.com/api/v3")
FAPI = os.getenv("BINANCE_FAPI_BASE", "https://fapi.binance.com")
CACHE_TTL_SEC = int(os.getenv("REGIME_CACHE_TTL_SEC", "300"))
FUNDING_CACHE_TTL_SEC = int(os.getenv("REGIME_FUNDING_CACHE_TTL_SEC", "180"))

# cache em memória (processo) para agregações pesadas do CoinGecko
_MK_CACHE = {"ts": 0.0, "data": None}
_FUND_CACHE = {"ts": 0.0, "data": None}
_REGIME_CACHE = {"ts": 0.0, "snap": None}


def _cg_global() -> dict:
    r = httpx.get(f"{CG}/global", timeout=20)
    r.raise_for_status()
    j = r.json()["data"]
    return {
        "btc_dom": float(j["market_cap_percentage"]["btc"]),
        "eth_dom": float(j["market_cap_percentage"].get("eth", 0.0)),
        "total_mcap": float(j["total_market_cap"]["usd"]),
        "vol_mcap": float(j["total_volume"]["usd"]),
    }


def _alts_breadth() -> float:
    basket = os.getenv(
        "REGIME_ALT_BASKET", "NEARUSDT,SOLUSDT,AVAXUSDT,RNDRUSDT,FETUSDT"
    ).split(",")
    if not basket:
        return 0.0
    above = 0
    for s in basket:
        try:
            df = get_klines(s.strip(), "1d", 60)
            c = df["close"].astype(float)
            ema = c.ewm(span=20).mean()
            if len(c) and c.iloc[-1] > float(ema.iloc[-1]):
                above += 1
        except Exception:
            # Se falhar um símbolo, ignora para não derrubar o snapshot
            pass
    return above / max(1, len(basket))


def _cg_coins_markets_pages(pages: int = 2, per_page: int = 250) -> list:
    out = []
    for page in range(1, pages + 1):
        params = {
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": per_page,
            "page": page,
            "sparkline": "false",
            "price_change_percentage": "7d,30d",
        }
        r = httpx.get(f"{CG}/coins/markets", params=params, timeout=30)
        r.raise_for_status()
        out.extend(r.json())
        time.sleep(0.2)
    return out


def _compute_total3_and_dominance_deltas() -> dict:
    """
    Usa /coins/markets para aproximar TOTAL e TOTAL3 (ex-BTC/ETH),
    e reconstrói MCAP de 7/30 dias atrás via retornos percentuais.
    """
    markets = _cg_coins_markets_pages()
    if not markets:
        raise RuntimeError("CoinGecko markets vazio")

    df = pd.DataFrame(markets)
    # Campos esperados
    for col in [
        "id",
        "symbol",
        "market_cap",
        "price_change_percentage_7d_in_currency",
        "price_change_percentage_30d_in_currency",
    ]:
        if col not in df.columns:
            df[col] = np.nan

    df = df[df["market_cap"].notna()].copy()
    df["mc"] = df["market_cap"].astype(float)
    df["ret7"] = (
        pd.to_numeric(df["price_change_percentage_7d_in_currency"], errors="coerce").fillna(0.0)
        / 100.0
    )
    df["ret30"] = (
        pd.to_numeric(df["price_change_percentage_30d_in_currency"], errors="coerce").fillna(0.0)
        / 100.0
    )
    # Evitar divisão por ~0 quando -100%
    df["ret7"] = df["ret7"].clip(lower=-0.95)
    df["ret30"] = df["ret30"].clip(lower=-0.95)
    df["mc_prev7"] = df["mc"] / (1.0 + df["ret7"])
    df["mc_prev30"] = df["mc"] / (1.0 + df["ret30"])

    total_cur = float(df["mc"].sum())
    total_prev7 = float(df["mc_prev7"].sum())
    total_prev30 = float(df["mc_prev30"].sum())

    def _row_by_id(cid: str):
        sub = df[df["id"] == cid]
        return sub.iloc[0] if len(sub) else None

    btc = _row_by_id("bitcoin")
    eth = _row_by_id("ethereum")
    btc_cur = float(btc["mc"]) if btc is not None else 0.0
    eth_cur = float(eth["mc"]) if eth is not None else 0.0
    btc_prev7 = float(btc["mc_prev7"]) if btc is not None else 0.0
    eth_prev7 = float(eth["mc_prev7"]) if eth is not None else 0.0
    btc_prev30 = float(btc["mc_prev30"]) if btc is not None else 0.0
    eth_prev30 = float(eth["mc_prev30"]) if eth is not None else 0.0

    total3_cur = max(1e-9, total_cur - btc_cur - eth_cur)
    total3_prev7 = max(1e-9, total_prev7 - btc_prev7 - eth_prev7)
    total3_prev30 = max(1e-9, total_prev30 - btc_prev30 - eth_prev30)

    total3_delta7 = (total3_cur / total3_prev7 - 1.0) * 100.0
    total3_delta30 = (total3_cur / total3_prev30 - 1.0) * 100.0
    btc_delta7 = (btc_cur / max(1e-9, btc_prev7) - 1.0) * 100.0
    btc_delta30 = (btc_cur / max(1e-9, btc_prev30) - 1.0) * 100.0
    divergence7 = total3_delta7 - btc_delta7

    btc_dom_cur = (btc_cur / max(1e-9, total_cur)) * 100.0
    btc_dom_prev30 = (btc_prev30 / max(1e-9, total_prev30)) * 100.0
    btc_dom_delta30 = btc_dom_cur - btc_dom_prev30

    return {
        "btc_dom": btc_dom_cur,
        "btc_dom_delta30": btc_dom_delta30,
        "total3_delta7": total3_delta7,
        "total3_delta30": total3_delta30,
        "btc_delta7": btc_delta7,
        "btc_delta30": btc_delta30,
        "divergence7": divergence7,
    }


def _get_market_metrics_cached() -> dict:
    now = time.time()
    data = _MK_CACHE.get("data")
    ts = _MK_CACHE.get("ts", 0.0)
    if data is not None and (now - ts) < CACHE_TTL_SEC:
        return data
    mk = _compute_total3_and_dominance_deltas()
    _MK_CACHE["data"] = mk
    _MK_CACHE["ts"] = now
    return mk


def _persist_regime_snapshot_pg(snap: dict) -> None:
    try:
        # toggle via env
        if str(os.getenv("REGIME_PERSIST", "1")).lower() not in ("1", "true", "yes"):
            return
        host = os.getenv("PG_HOST")
        if not host:
            return
        conn = psycopg2.connect(
            host=host,
            port=int(os.getenv("PG_PORT", "5432")),
            dbname=os.getenv("PG_DB", "signals"),
            user=os.getenv("PG_USER", "signals"),
            password=os.getenv("PG_PASSWORD", "signals"),
        )
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS regime_snapshots (
              id BIGSERIAL PRIMARY KEY,
              ts TIMESTAMPTZ NOT NULL DEFAULT NOW(),
              btc_dom REAL,
              btc_dom_delta30 REAL,
              total3_delta7 REAL,
              total3_delta30 REAL,
              btc_delta7 REAL,
              btc_delta30 REAL,
              divergence7 REAL,
              breadth REAL,
              altseason_score INT,
              regime TEXT
            );
            """
        )
        cur.execute(
            """
            INSERT INTO regime_snapshots
            (btc_dom, btc_dom_delta30, total3_delta7, total3_delta30, btc_delta7, btc_delta30, divergence7, breadth, altseason_score, regime)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s);
            """,
            (
                float(snap.get("btc_dom", 0.0)),
                float(snap.get("btc_dom_delta30", 0.0)),
                float(snap.get("total3_delta7", 0.0)),
                float(snap.get("total3_delta30", 0.0)),
                float(snap.get("btc_delta7", 0.0)),
                float(snap.get("btc_delta30", 0.0)),
                float(snap.get("divergence7", 0.0)),
                float(snap.get("breadth", 0.0)),
                int(snap.get("altseason_score", 0)),
                str(snap.get("regime", "NEUTRAL")),
            ),
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception:
        # não quebra o endpoint se o banco estiver fora
        pass


def compute_regime_snapshot(symbol_btc: str = "BTCUSDT") -> dict:
    breadth = _alts_breadth()
    try:
        mk = _get_market_metrics_cached()
        basket_metrics = _basket_funding_and_oi()
        score = 0
        if mk["btc_dom_delta30"] < -2.0:
            score += 25
        if mk["total3_delta30"] > 12.0:
            score += 25
        if breadth > 0.6:
            score += 20
        if (mk["total3_delta7"] - mk["btc_delta7"]) > 5.0:
            score += 15
        # funding_mean (em %) e OI_Δ7 (%):
        fmp = basket_metrics.get("funding_mean_pct", 0.0)
        oi7 = basket_metrics.get("oi_delta7_mean", 0.0)
        if 0.02 <= fmp <= 0.06:
            score += 10
        if oi7 > 10.0:
            score += 5

        score = int(max(0, min(100, score)))

        if score >= 70:
            regime = "ALT_ROTATION"
        elif score >= 40:
            regime = "NEUTRAL"
        else:
            if mk["btc_delta30"] > 0:
                regime = "BTC_TREND"
            elif mk["btc_delta30"] <= 0 and mk["total3_delta30"] <= 0:
                regime = "RISK_OFF"
            else:
                regime = "BTC_TREND"

        snap = {
            "btc_dom": round(float(mk["btc_dom"]), 3),
            "btc_dom_delta30": round(float(mk["btc_dom_delta30"]), 3),
            "total3_delta7": round(float(mk["total3_delta7"]), 3),
            "total3_delta30": round(float(mk["total3_delta30"]), 3),
            "btc_delta7": round(float(mk["btc_delta7"]), 3),
            "btc_delta30": round(float(mk["btc_delta30"]), 3),
            "divergence7": round(float(mk["divergence7"]), 3),
            "breadth": round(float(breadth), 3),
            "funding_mean_pct": round(float(fmp), 4),
            "oi_delta7_mean": round(float(oi7), 3),
            "altseason_score": score,
            "regime": regime,
        }
    except Exception:
        # Fallback para MVP simples se a agregação falhar (rate limit, etc.)
        g0 = _cg_global()
        time.sleep(0.2)
        g1 = _cg_global()
        btc_dom_delta = g1["btc_dom"] - g0["btc_dom"]
        score = 25 if btc_dom_delta < -0.3 else 0
        if breadth > 0.6:
            score += 25
        regime = "ALT_ROTATION" if score >= 70 else ("NEUTRAL" if score >= 40 else "BTC_TREND")
        snap = {
            "btc_dom": g1["btc_dom"],
            "btc_dom_delta30": btc_dom_delta,
            "total3_delta7": 0.0,
            "total3_delta30": 0.0,
            "btc_delta7": 0.0,
            "btc_delta30": 0.0,
            "divergence7": 0.0,
            "breadth": round(float(breadth), 3),
            "funding_mean_pct": 0.0,
            "oi_delta7_mean": 0.0,
            "altseason_score": int(score),
            "regime": regime,
        }

    # Persistência opcional no Postgres
    _persist_regime_snapshot_pg(snap)
    return snap


def get_regime_snapshot_cached(symbol_btc: str = "BTCUSDT") -> dict:
    now = time.time()
    cached = _REGIME_CACHE.get("snap")
    ts = _REGIME_CACHE.get("ts", 0.0)
    if cached is not None and (now - ts) < REGIME_SNAPSHOT_TTL_SEC:
        return cached
    snap = compute_regime_snapshot(symbol_btc)
    _REGIME_CACHE["snap"] = snap
    _REGIME_CACHE["ts"] = now
    return snap


# ------- Funding & OI (Binance Futures) -------

def _binance_latest_funding(symbol: str) -> float:
    try:
        r = httpx.get(f"{FAPI}/fapi/v1/fundingRate", params={"symbol": symbol, "limit": 1}, timeout=20)
        r.raise_for_status()
        arr = r.json()
        if isinstance(arr, list) and arr:
            fr = float(arr[0].get("fundingRate", 0.0))
            return fr
    except Exception:
        pass
    return 0.0


def _binance_oi_delta_days(symbol: str, days: int = 7) -> float:
    try:
        params = {"symbol": symbol, "period": "1d", "limit": max(2, days + 1)}
        r = httpx.get(f"{FAPI}/futures/data/openInterestHist", params=params, timeout=20)
        r.raise_for_status()
        arr = r.json()
        if isinstance(arr, list) and len(arr) >= 2:
            last = float(arr[-1].get("sumOpenInterest", 0.0))
            prev = float(arr[-(days + 1)].get("sumOpenInterest", arr[0].get("sumOpenInterest", 0.0)))
            if prev > 0:
                return (last / prev - 1.0) * 100.0
    except Exception:
        pass
    return 0.0


def _basket_funding_and_oi() -> dict:
    now = time.time()
    data = _FUND_CACHE.get("data")
    ts = _FUND_CACHE.get("ts", 0.0)
    if data is not None and (now - ts) < FUNDING_CACHE_TTL_SEC:
        return data

    basket = os.getenv(
        "REGIME_ALT_BASKET", "NEARUSDT,SOLUSDT,AVAXUSDT,RNDRUSDT,FETUSDT"
    ).split(",")
    fundings = []
    oi_deltas = []
    for s in basket:
        s = s.strip().upper()
        if not s:
            continue
        fr = _binance_latest_funding(s)
        oi7 = _binance_oi_delta_days(s, days=7)
        fundings.append(fr)
        oi_deltas.append(oi7)
        time.sleep(0.15)
    if not fundings:
        f_mean_pct = 0.0
    else:
        f_mean_pct = float(np.mean(fundings)) * 100.0  # funding em %/8h
    oi_mean = float(np.mean(oi_deltas)) if oi_deltas else 0.0
    out = {"funding_mean_pct": round(f_mean_pct, 4), "oi_delta7_mean": round(oi_mean, 3)}
    _FUND_CACHE["data"] = out
    _FUND_CACHE["ts"] = now
    return out

def _ensure_regime_objects(conn, create_mv: bool = False):
    cur = conn.cursor()
    # table is created on insert path too, but ensure here for history endpoints
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS regime_snapshots (
          id BIGSERIAL PRIMARY KEY,
          ts TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          btc_dom REAL,
          btc_dom_delta30 REAL,
          total3_delta7 REAL,
          total3_delta30 REAL,
          btc_delta7 REAL,
          btc_delta30 REAL,
          divergence7 REAL,
          breadth REAL,
          funding_mean_pct REAL,
          oi_delta7_mean REAL,
          altseason_score INT,
          regime TEXT
        );
        CREATE INDEX IF NOT EXISTS regime_snapshots_ts_idx ON regime_snapshots(ts);
        """
    )
    if create_mv:
        cur.execute("SELECT 1 FROM pg_matviews WHERE matviewname='regime_snapshots_daily'")
        exists = cur.fetchone() is not None
        if not exists:
            cur.execute(
                """
                CREATE MATERIALIZED VIEW regime_snapshots_daily AS
                WITH agg AS (
                  SELECT date_trunc('day', ts) AS day,
                         AVG(btc_dom) AS btc_dom,
                         AVG(btc_dom_delta30) AS btc_dom_delta30,
                         AVG(total3_delta7) AS total3_delta7,
                         AVG(total3_delta30) AS total3_delta30,
                         AVG(btc_delta7) AS btc_delta7,
                         AVG(btc_delta30) AS btc_delta30,
                         AVG(divergence7) AS divergence7,
                         AVG(breadth) AS breadth,
                         AVG(funding_mean_pct) AS funding_mean_pct,
                         AVG(oi_delta7_mean) AS oi_delta7_mean,
                         AVG(altseason_score) AS altseason_score
                  FROM regime_snapshots
                  GROUP BY 1
                ),
                last_regime AS (
                  SELECT DISTINCT ON (date_trunc('day', ts))
                         date_trunc('day', ts) AS day,
                         regime
                  FROM regime_snapshots
                  ORDER BY date_trunc('day', ts), ts DESC
                )
                SELECT a.*, lr.regime
                FROM agg a
                LEFT JOIN last_regime lr USING (day);
                """
            )
            cur.execute("CREATE INDEX IF NOT EXISTS regime_snapshots_daily_day_idx ON regime_snapshots_daily(day)")
    conn.commit()
    cur.close()


def refresh_regime_mv() -> dict:
    try:
        host = os.getenv("PG_HOST")
        if not host:
            return {"ok": False, "error": "PG not configured"}
        conn = psycopg2.connect(
            host=host,
            port=int(os.getenv("PG_PORT", "5432")),
            dbname=os.getenv("PG_DB", "signals"),
            user=os.getenv("PG_USER", "signals"),
            password=os.getenv("PG_PASSWORD", "signals"),
        )
        _ensure_regime_objects(conn, create_mv=True)
        cur = conn.cursor()
        cur.execute("REFRESH MATERIALIZED VIEW regime_snapshots_daily;")
        conn.commit()
        cur.close()
        conn.close()
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def get_regime_history(days: int = 30, use_mv: bool | None = None, refresh: bool = False) -> dict:
    try:
        host = os.getenv("PG_HOST")
        if not host:
            return {"rows": [], "source": "none"}
        conn = psycopg2.connect(
            host=host,
            port=int(os.getenv("PG_PORT", "5432")),
            dbname=os.getenv("PG_DB", "signals"),
            user=os.getenv("PG_USER", "signals"),
            password=os.getenv("PG_PASSWORD", "signals"),
        )
        use_mv_final = (
            use_mv if use_mv is not None else str(os.getenv("REGIME_HISTORY_USE_MV", "0")).lower() in ("1", "true", "yes")
        )
        _ensure_regime_objects(conn, create_mv=use_mv_final)
        if use_mv_final and (refresh or str(os.getenv("REGIME_REFRESH_ON_READ", "0")).lower() in ("1", "true", "yes")):
            cur = conn.cursor()
            cur.execute("REFRESH MATERIALIZED VIEW regime_snapshots_daily;")
            conn.commit()
            cur.close()

        cur = conn.cursor()
        if use_mv_final:
            cur.execute(
                """
                SELECT day,
                       btc_dom, btc_dom_delta30,
                       total3_delta7, total3_delta30,
                       btc_delta7, btc_delta30,
                       divergence7, breadth,
                       funding_mean_pct, oi_delta7_mean,
                       altseason_score, regime
                FROM regime_snapshots_daily
                WHERE day >= NOW() - INTERVAL %s
                ORDER BY day;
                """,
                (f"{int(days)} days",),
            )
        else:
            cur.execute(
                """
                WITH base AS (
                  SELECT date_trunc('day', ts) AS day,
                         AVG(btc_dom) AS btc_dom,
                         AVG(btc_dom_delta30) AS btc_dom_delta30,
                         AVG(total3_delta7) AS total3_delta7,
                         AVG(total3_delta30) AS total3_delta30,
                         AVG(btc_delta7) AS btc_delta7,
                         AVG(btc_delta30) AS btc_delta30,
                         AVG(divergence7) AS divergence7,
                         AVG(breadth) AS breadth,
                         AVG(funding_mean_pct) AS funding_mean_pct,
                         AVG(oi_delta7_mean) AS oi_delta7_mean,
                         AVG(altseason_score) AS altseason_score
                  FROM regime_snapshots
                  WHERE ts >= NOW() - INTERVAL %s
                  GROUP BY 1
                ),
                last_regime AS (
                  SELECT DISTINCT ON (date_trunc('day', ts))
                         date_trunc('day', ts) AS day,
                         regime
                  FROM regime_snapshots
                  WHERE ts >= NOW() - INTERVAL %s
                  ORDER BY date_trunc('day', ts), ts DESC
                )
                SELECT b.day,
                       b.btc_dom, b.btc_dom_delta30,
                       b.total3_delta7, b.total3_delta30,
                       b.btc_delta7, b.btc_delta30,
                       b.divergence7, b.breadth,
                       b.funding_mean_pct, b.oi_delta7_mean,
                       b.altseason_score, lr.regime
                FROM base b
                LEFT JOIN last_regime lr USING (day)
                ORDER BY b.day;
                """,
                (f"{int(days)} days", f"{int(days)} days"),
            )
        rows = cur.fetchall()
        cols = [
            "day",
            "btc_dom",
            "btc_dom_delta30",
            "total3_delta7",
            "total3_delta30",
            "btc_delta7",
            "btc_delta30",
            "divergence7",
            "breadth",
            "funding_mean_pct",
            "oi_delta7_mean",
            "altseason_score",
            "regime",
        ]
        out = []
        for r in rows:
            d = {k: (r[i].isoformat() if k == "day" else float(r[i]) if isinstance(r[i], (int, float)) else r[i]) for i, k in enumerate(cols)}
            out.append(d)
        cur.close()
        conn.close()
        return {"rows": out, "source": ("mv" if use_mv_final else "base")}
    except Exception as e:
        return {"rows": [], "source": "error", "error": str(e)}


# Opcional (placeholder): modelo supervisionado p/ regime (stack)
MODEL = "data/models/regime_clf.pkl"


def train_regime() -> str:
    # Placeholder: futuramente, gerar dataset real (BTC.D, TOTAL3, breadth, funding, OI)
    os.makedirs(os.path.dirname(MODEL), exist_ok=True)
    joblib.dump({"placeholder": True}, MODEL)
    return MODEL


def predict_regime() -> dict:
    return compute_regime_snapshot()
