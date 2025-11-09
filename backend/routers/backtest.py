from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def backtest_stub():
    return {"todo": "Implementar: P&L, sharpe, maxDD, custos, slippage."}

