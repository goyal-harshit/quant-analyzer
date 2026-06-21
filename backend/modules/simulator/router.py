"""Trading Simulator router — /api/v1/simulator

Paper-trading endpoints. All routes accept an optional bearer token: logged-in
users own their portfolios; guests create anonymous portfolios scoped by id.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from models.database import get_db, User
from services.auth_service import get_optional_user
from . import service
from .schemas import (
    CreatePortfolioRequest, TradeRequest, PortfolioState,
    TransactionOut, Performance,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _uid(user: Optional[User]) -> Optional[int]:
    return user.id if user else None


@router.post("/portfolio")
async def create_portfolio(
    req: CreatePortfolioRequest,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user),
):
    """Create a new simulator portfolio with virtual starting capital."""
    p = await service.create_portfolio(db, _uid(user), req.name, req.starting_capital)
    return {"id": p.id, "name": p.name, "starting_capital": p.starting_capital, "cash": p.cash}


@router.get("/portfolios")
async def list_portfolios(
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user),
):
    """List the logged-in user's portfolios (empty for guests — scope by id)."""
    ps = await service.list_portfolios(db, _uid(user))
    return [{"id": p.id, "name": p.name, "starting_capital": p.starting_capital, "cash": p.cash} for p in ps]


@router.get("/{portfolio_id}/portfolio", response_model=PortfolioState)
async def get_portfolio(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user),
):
    """Current holdings marked to live prices, with realized/unrealized P&L."""
    p = await service._get_portfolio(db, portfolio_id, _uid(user))
    return await service.get_portfolio_state(db, p)


@router.post("/{portfolio_id}/trade", response_model=TransactionOut)
async def place_trade(
    portfolio_id: int,
    req: TradeRequest,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user),
):
    """Place a buy/sell order. Executes at the live price unless one is given."""
    p = await service._get_portfolio(db, portfolio_id, _uid(user))
    tx = await service.place_trade(db, p, req.ticker, req.side.value, req.quantity, req.price)
    return {
        "id": tx.id, "ticker": tx.ticker, "side": tx.side, "quantity": tx.quantity,
        "price": tx.price, "fees": tx.fees, "realized_pnl": tx.realized_pnl, "timestamp": tx.timestamp,
    }


@router.get("/{portfolio_id}/trades", response_model=List[TransactionOut])
async def get_trades(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user),
):
    """Full transaction history (most recent first)."""
    await service._get_portfolio(db, portfolio_id, _uid(user))
    return await service.list_transactions(db, portfolio_id)


@router.get("/{portfolio_id}/performance", response_model=Performance)
async def get_performance(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user),
):
    """Equity curve + performance stats (returns, win rate, drawdown, Sharpe)."""
    p = await service._get_portfolio(db, portfolio_id, _uid(user))
    return await service.get_performance(db, p)


@router.delete("/{portfolio_id}")
async def delete_portfolio(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user),
):
    """Delete a portfolio and its transactions."""
    await service.delete_portfolio(db, portfolio_id, _uid(user))
    return {"deleted": portfolio_id}
