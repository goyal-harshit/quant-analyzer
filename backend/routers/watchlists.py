"""Watchlists Router — User watchlist management"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from models.database import get_db, User, Watchlist
from models.schemas import WatchlistCreate, WatchlistOut
from services.data_service import data_service, _gather_limited
from services.auth_service import get_current_user

router = APIRouter()


@router.post("", response_model=dict)
async def create_watchlist(payload: WatchlistCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Create a new watchlist."""
    user_id = current_user.id
    watchlist = Watchlist(user_id=user_id, name=payload.name, tickers=payload.tickers or [])
    db.add(watchlist)
    await db.commit()
    await db.refresh(watchlist)
    return {"id": watchlist.id, "name": watchlist.name, "tickers": watchlist.tickers}


@router.get("", response_model=list[WatchlistOut])
async def list_watchlists(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """List all watchlists for the demo user."""
    user_id = current_user.id
    res = await db.execute(select(Watchlist).where(Watchlist.user_id == user_id))
    watchlists = res.scalars().all()
    return [
        WatchlistOut(id=w.id, name=w.name, tickers=w.tickers, created_at=w.created_at)
        for w in watchlists
    ]


@router.get("/{watchlist_id}")
async def get_watchlist(watchlist_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific watchlist with live quote data."""
    res = await db.execute(select(Watchlist).where(Watchlist.id == watchlist_id))
    watchlist = res.scalar_one_or_none()
    if not watchlist:
        raise HTTPException(status_code=404, detail="Watchlist not found")

    tickers = watchlist.tickers or []
    quotes = {}
    if tickers:
        quote_results = await _gather_limited(
            [data_service.get_quote(t) for t in tickers], limit=10
        )
        quotes = dict(zip(tickers, [q for q in quote_results if q]))

    return {
        "id": watchlist.id,
        "name": watchlist.name,
        "tickers": watchlist.tickers,
        "quotes": quotes,
    }


@router.put("/{watchlist_id}/tickers")
async def update_watchlist_tickers(watchlist_id: int, tickers: list[str], db: AsyncSession = Depends(get_db)):
    """Update the tickers in a watchlist."""
    res = await db.execute(select(Watchlist).where(Watchlist.id == watchlist_id))
    watchlist = res.scalar_one_or_none()
    if not watchlist:
        raise HTTPException(status_code=404, detail="Watchlist not found")

    watchlist.tickers = tickers
    await db.commit()
    return {"updated": True, "tickers": watchlist.tickers}


@router.delete("/{watchlist_id}")
async def delete_watchlist(watchlist_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a watchlist."""
    res = await db.execute(select(Watchlist).where(Watchlist.id == watchlist_id))
    watchlist = res.scalar_one_or_none()
    if not watchlist:
        raise HTTPException(status_code=404, detail="Watchlist not found")

    await db.delete(watchlist)
    await db.commit()
    return {"deleted": True}
