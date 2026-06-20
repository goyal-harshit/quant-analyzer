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
async def get_watchlist(watchlist_id: int, refresh: bool = False, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get a specific watchlist with live quote data."""
    res = await db.execute(select(Watchlist).where(Watchlist.id == watchlist_id, Watchlist.user_id == current_user.id))
    watchlist = res.scalar_one_or_none()
    if not watchlist:
        raise HTTPException(status_code=404, detail="Watchlist not found")

    tickers = watchlist.tickers or []
    quotes = {}
    if tickers:
        quote_results = await _gather_limited(
            [data_service.get_quote(t, refresh=refresh) for t in tickers], limit=10
        )
        quote_results_cleaned = [None if isinstance(q, Exception) else q for q in quote_results]
        quotes = dict(zip(tickers, [q for q in quote_results_cleaned if q]))

    return {
        "id": watchlist.id,
        "name": watchlist.name,
        "tickers": watchlist.tickers,
        "quotes": quotes,
    }


@router.put("/{watchlist_id}/tickers")
async def update_watchlist_tickers(watchlist_id: int, tickers: list[str], db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Update the tickers in a watchlist."""
    res = await db.execute(select(Watchlist).where(Watchlist.id == watchlist_id, Watchlist.user_id == current_user.id))
    watchlist = res.scalar_one_or_none()
    if not watchlist:
        raise HTTPException(status_code=404, detail="Watchlist not found")

    watchlist.tickers = tickers
    await db.commit()
    return {"updated": True, "tickers": watchlist.tickers}


@router.delete("/{watchlist_id}")
async def delete_watchlist(watchlist_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Delete a watchlist."""
    res = await db.execute(select(Watchlist).where(Watchlist.id == watchlist_id, Watchlist.user_id == current_user.id))
    watchlist = res.scalar_one_or_none()
    if not watchlist:
        raise HTTPException(status_code=404, detail="Watchlist not found")

    await db.delete(watchlist)
    await db.commit()
    return {"deleted": True}


@router.get("/{watchlist_id}/performance")
async def get_watchlist_performance(
    watchlist_id: int,
    benchmark: str = "NIFTY50",
    period: str = "1y",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get watchlist performance vs benchmark, equal weighted index of tickers.
    """
    res = await db.execute(select(Watchlist).where(Watchlist.id == watchlist_id, Watchlist.user_id == current_user.id))
    watchlist = res.scalar_one_or_none()
    if not watchlist:
        raise HTTPException(status_code=404, detail="Watchlist not found")

    tickers = watchlist.tickers or []
    if not tickers:
        return {"performance": [], "benchmark": benchmark}

    import pandas as pd
    history_dfs = {}
    for t in tickers:
        df = await data_service.get_price_history(t, period=period)
        if df is not None and not isinstance(df, Exception) and not df.empty:
            df_copy = df.copy()
            df_copy.columns = [c.lower() for c in df_copy.columns]
            if "close" in df_copy.columns:
                history_dfs[t] = df_copy["close"]

    if not history_dfs:
        return {"performance": [], "benchmark": benchmark}

    combined_df = pd.DataFrame(history_dfs).ffill().bfill()
    watchlist_growth = combined_df.mean(axis=1)
    if not watchlist_growth.empty:
        watchlist_growth = (watchlist_growth / watchlist_growth.iloc[0]) * 100

    bench_ticker = "^NSEI" if benchmark.upper() == "NIFTY50" else benchmark
    bench_df = await data_service.get_price_history(bench_ticker, period=period)
    if bench_df.empty:
        bench_df = await data_service.get_price_history("^NSEI", period=period)

    if not bench_df.empty:
        bench_df_copy = bench_df.copy()
        bench_df_copy.columns = [c.lower() for c in bench_df_copy.columns]
        if "close" in bench_df_copy.columns:
            bench_growth = bench_df_copy["close"]
            bench_growth = (bench_growth / bench_growth.iloc[0]) * 100
        else:
            bench_growth = pd.Series(100.0, index=watchlist_growth.index)
    else:
        bench_growth = pd.Series(100.0, index=watchlist_growth.index)

    performance_data = []
    for idx in watchlist_growth.index:
        date_str = idx.strftime("%Y-%m-%d")
        wl_val = float(watchlist_growth.loc[idx])
        bench_val = float(bench_growth.loc[idx]) if idx in bench_growth.index else 100.0
        performance_data.append({
            "date": date_str,
            "watchlist": round(wl_val, 2),
            "benchmark": round(bench_val, 2),
        })

    return {
        "performance": performance_data,
        "benchmark": benchmark,
    }
