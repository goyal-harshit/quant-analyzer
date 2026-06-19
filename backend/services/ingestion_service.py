"""
ingestion_service.py — Background data ingestion pipeline
Seeds StockMaster, ingests price data, fundamentals, and precomputes factor scores.
"""

import logging
from datetime import datetime, timezone
import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.database import StockMaster, PriceData, Fundamentals, FactorScore
from services.data_service import data_service
from services.seed_data import ALL_STOCKS
from services.fast_data import compute_quant_factors

logger = logging.getLogger(__name__)


class IngestionService:
    async def seed_stock_master(self, db: AsyncSession):
        """Seed stock_master table from seed_data.py on startup."""
        logger.info("Starting stock_master seeding...")
        result = await db.execute(select(StockMaster.ticker))
        existing_tickers = set(result.scalars().all())

        added_count = 0
        for s in ALL_STOCKS:
            ticker = s[0].upper()
            if ticker not in existing_tickers:
                # Resolve base attributes from seed dict
                from services.seed_data import _stock_dict
                sd = _stock_dict(ticker)
                
                stock = StockMaster(
                    ticker=ticker,
                    name=sd["name"],
                    sector=sd["sector"],
                    industry=sd.get("industry") or "Unknown",
                    exchange="NSE",
                    market_cap=sd.get("marketCap", 0),
                    is_active=True,
                )
                db.add(stock)
                existing_tickers.add(ticker)
                added_count += 1

        if added_count > 0:
            await db.commit()
            logger.info(f"Seeded {added_count} new stocks into stock_master.")
        else:
            logger.info("stock_master already seeded.")

    async def ingest_prices(self, db: AsyncSession, ticker: str, period: str = "2y") -> int:
        """Fetch price history and insert new data points."""
        ticker = ticker.upper()
        df = await data_service.get_price_history(ticker, period=period)
        if df.empty:
            logger.warning(f"No price history found for {ticker} during ingestion.")
            return 0

        # Check existing dates for this ticker
        stmt = select(PriceData.date).where(PriceData.ticker == ticker)
        res = await db.execute(stmt)
        existing_dates = set(d.date() for d in res.scalars().all())

        new_records = []
        for dt, row in df.iterrows():
            date_only = dt.date()
            if date_only not in existing_dates:
                # Ensure date is datetime object
                dt_obj = datetime(dt.year, dt.month, dt.day)
                new_records.append(
                    PriceData(
                        ticker=ticker,
                        date=dt_obj,
                        open=float(row["open"]),
                        high=float(row["high"]),
                        low=float(row["low"]),
                        close=float(row["close"]),
                        adj_close=float(row.get("adj_close", row["close"])),
                        volume=int(row["volume"]),
                    )
                )

        if new_records:
            db.add_all(new_records)
            await db.commit()
            logger.info(f"Ingested {len(new_records)} price bars for {ticker}.")
            return len(new_records)
        return 0

    async def ingest_fundamentals(self, db: AsyncSession, ticker: str) -> bool:
        """Fetch fundamental data and update/insert latest."""
        ticker = ticker.upper()
        fund = await data_service.get_fundamentals(ticker)
        if not fund:
            logger.warning(f"No fundamental data found for {ticker} during ingestion.")
            return False

        # Check if latest fundamentals exist for the period
        period = fund.get("period", "FY24")
        stmt = select(Fundamentals).where(
            Fundamentals.ticker == ticker,
            Fundamentals.period == period
        )
        res = await db.execute(stmt)
        record = res.scalar_one_or_none()

        if not record:
            record = Fundamentals(
                ticker=ticker,
                period=period,
                period_end=datetime.now(timezone.utc),
            )
            db.add(record)

        # Map fields
        record.pe_ratio = fund.get("pe_ratio")
        record.pb_ratio = fund.get("pb_ratio")
        record.ev_ebitda = fund.get("ev_ebitda")
        record.ps_ratio = fund.get("ps_ratio")
        record.roe = fund.get("roe")
        record.roa = fund.get("roa")
        record.roic = fund.get("roce")  # Map ROCE to roic
        record.gross_margin = fund.get("gross_margin")
        record.ebitda_margin = fund.get("ebitda_margin")
        record.net_margin = fund.get("net_margin")
        record.revenue_growth = fund.get("revenue_growth")
        record.eps_growth = fund.get("earnings_growth")
        record.debt_equity = fund.get("debt_equity")
        record.current_ratio = fund.get("current_ratio")
        record.fcf_yield = fund.get("fcf_yield")
        record.revenue = fund.get("revenue")
        record.ebitda = fund.get("ebitda")
        record.net_profit = fund.get("net_profit")
        record.total_debt = fund.get("total_debt")

        # Update StockMaster market cap
        if fund.get("market_cap"):
            stmt_stock = select(StockMaster).where(StockMaster.ticker == ticker)
            res_stock = await db.execute(stmt_stock)
            stock = res_stock.scalar_one_or_none()
            if stock:
                stock.market_cap = fund.get("market_cap")

        await db.commit()
        logger.info(f"Ingested fundamentals for {ticker} ({period}).")
        return True

    async def compute_and_store_factors(self, db: AsyncSession, ticker: str) -> bool:
        """Compute factor scores from DB tables and store them."""
        ticker = ticker.upper()
        # Fetch price history from DB to ensure local computation is fast and consistent
        stmt_hist = select(PriceData).where(PriceData.ticker == ticker).order_by(PriceData.date)
        res_hist = await db.execute(stmt_hist)
        price_records = res_hist.scalars().all()

        if len(price_records) < 20:
            # Fallback to fetching from data_service
            df = await data_service.get_price_history(ticker, period="2y")
        else:
            df = pd.DataFrame([{
                "open": r.open, "high": r.high, "low": r.low, "close": r.close, "volume": r.volume
            } for r in price_records], index=[r.date for r in price_records])

        # Fetch fundamentals from DB
        stmt_fund = select(Fundamentals).where(Fundamentals.ticker == ticker).order_by(Fundamentals.created_at.desc())
        res_fund = await db.execute(stmt_fund)
        fund_record = res_fund.scalars().first()

        if fund_record:
            fund_dict = {
                "pe_ratio": fund_record.pe_ratio,
                "pb_ratio": fund_record.pb_ratio,
                "roe": fund_record.roe,
                "revenue_growth": fund_record.revenue_growth,
                "earnings_growth": fund_record.eps_growth,
                "debt_equity": fund_record.debt_equity,
                "current_ratio": fund_record.current_ratio,
            }
        else:
            # Fallback
            fund_dict = await data_service.get_fundamentals(ticker) or {}

        if df.empty:
            logger.warning(f"Cannot compute factors for {ticker}: insufficient price history.")
            return False

        try:
            scores = compute_quant_factors(df, fund_dict)
            date_today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

            # Check if factor scores already exist for today
            stmt_fact = select(FactorScore).where(FactorScore.ticker == ticker, FactorScore.date == date_today)
            res_fact = await db.execute(stmt_fact)
            fact_record = res_fact.scalar_one_or_none()

            if not fact_record:
                fact_record = FactorScore(ticker=ticker, date=date_today)
                db.add(fact_record)

            fact_record.momentum_score = scores.get("momentum_score")
            fact_record.quality_score = scores.get("quality_score")
            fact_record.value_score = scores.get("value_score")
            fact_record.growth_score = scores.get("growth_score")
            fact_record.size_score = scores.get("size_score")
            fact_record.low_vol_score = scores.get("low_vol_score")
            fact_record.composite_score = scores.get("composite_score")
            fact_record.momentum_12_1 = scores.get("momentum_12_1")
            fact_record.momentum_3_1 = scores.get("momentum_3_1")
            fact_record.momentum_6_1 = scores.get("momentum_6_1")
            fact_record.volatility_60d = scores.get("volatility_60d")

            await db.commit()
            logger.info(f"Computed and stored factors for {ticker}.")
            return True
        except Exception as e:
            logger.error(f"Error computing factors for {ticker}: {e}")
            return False


ingestion_service = IngestionService()
