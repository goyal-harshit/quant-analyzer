"""
Screener.in scraper — fetches fundamental data for Indian stocks.
Free, no API key required. Scrapes public company pages.
"""
import asyncio
import logging
import re
from typing import Optional

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def _clean_number(text: str) -> Optional[float]:
    """Clean and convert a number string to float."""
    if not text or text.strip() in ("", "-", "N/A", "NA"):
        return None
    cleaned = text.strip().replace(",", "").replace("%", "").replace("₹", "").replace("Cr", "").replace("L", "")
    cleaned = cleaned.replace("\u20b9", "").strip()
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def _extract_table_data(soup: BeautifulSoup, section_id: str) -> dict:
    """Extract data from a Screener.in table section."""
    result = {}
    section = soup.find("section", {"id": section_id})
    if not section:
        return result

    table = section.find("table")
    if not table:
        return result

    # Get headers
    thead = table.find("thead")
    if thead:
        headers = [th.get_text(strip=True) for th in thead.find_all("th")]
    else:
        headers = []

    # Get rows
    tbody = table.find("tbody")
    if tbody:
        rows = tbody.find_all("tr")
        for row in rows:
            cells = row.find_all(["td", "th"])
            if cells:
                label = cells[0].get_text(strip=True)
                values = [c.get_text(strip=True) for c in cells[1:]]
                result[label] = values

    return result


class ScreenerService:
    """Scrapes Screener.in for Indian stock fundamental data."""

    def __init__(self):
        self.base_url = "https://www.screener.in/company/{ticker}"
        self._cache: dict = {}
        self._cache_ttl = 300  # 5 min cache

    async def get_fundamentals(self, ticker: str) -> dict:
        """
        Fetch fundamental data from Screener.in for an Indian stock.
        Returns dict with PE, ROE, ROCE, margins, debt ratios, etc.
        """
        import time
        now = time.time()

        # Check cache
        if ticker in self._cache:
            cached_time, cached_data = self._cache[ticker]
            if now - cached_time < self._cache_ttl:
                logger.info(f"Screener.in cache hit for {ticker}")
                return cached_data

        url = self.base_url.format(ticker=ticker)
        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                resp = await client.get(url, headers=HEADERS)
                if resp.status_code != 200:
                    logger.warning(f"Screener.in returned {resp.status_code} for {ticker}")
                    return {}
                html = resp.text

            soup = BeautifulSoup(html, "lxml")
            data = self._parse_screener_page(soup, ticker)

            # Cache result
            self._cache[ticker] = (now, data)
            return data

        except Exception as e:
            logger.error(f"Screener.in scrape failed for {ticker}: {e}")
            return {}

    def _parse_screener_page(self, soup: BeautifulSoup, ticker: str) -> dict:
        """Parse a Screener.in company page and extract all fundamentals."""
        result = {"ticker": ticker, "source": "screener.in"}

        # Get full page text for regex extraction
        full_text = soup.get_text(separator=" ")

        # ── Top ratios (from the header card) ────────────────────
        # Screener.in shows key metrics in the top area of the page
        ratio_patterns = {
            "pe_ratio": r"Stock P/E\s*([\d,.]+)",
            "pb_ratio": r"Price to Book\s*([\d,.]+)",
            "market_cap": r"Market Cap\s*₹?\s*([\d,.]+)\s*Cr",
            "dividend_yield": r"Dividend Yield\s*([\d,.]+)\s*%",
            "fifty_two_week_high": r"High\s*₹?\s*([\d,.]+)",
            "fifty_two_week_low": r"Low\s*₹?\s*([\d,.]+)",
            "roce": r"ROCE\s*([\d,.]+)\s*%?",
            "roe": r"ROE\s*([\d,.]+)\s*%?",
            "book_value": r"Book Value\s*₹?\s*([\d,.]+)",
            "eps": r"EPS\s*₹?\s*([\d,.]+)",
        }

        for key, pattern in ratio_patterns.items():
            match = re.search(pattern, full_text)
            if match:
                val = _clean_number(match.group(1))
                if val is not None:
                    # Convert market cap from Cr to INR
                    if key == "market_cap":
                        val = val * 1e7
                    result[key] = val

        # ── Key Ratios table ────────────────────────────────────
        ratios_section = soup.find("section", {"id": "ratios"})
        if ratios_section:
            table = ratios_section.find("table")
            if table:
                for row in table.find_all("tr"):
                    cells = row.find_all(["td", "th"])
                    if cells:
                        label = cells[0].get_text(strip=True).lower()
                        values = [c.get_text(strip=True) for c in cells[1:]]
                        latest = values[-1] if values else None
                        if not latest:
                            continue
                        val = _clean_number(latest)
                        if val is None:
                            continue
                        if "roe" in label and "roe" not in result:
                            result["roe"] = val
                        elif "roce" in label and "roce" not in result:
                            result["roce"] = val
                        elif "debt" in label and "equity" in label:
                            result["debt_equity"] = val
                        elif "current" in label and "ratio" in label:
                            result["current_ratio"] = val
                        elif "quick" in label and "ratio" in label:
                            result["quick_ratio"] = val
                        elif "interest" in label and "coverage" in label:
                            result["interest_coverage"] = val

        # ── Profit & Loss (latest year) ─────────────────────────
        pl_section = soup.find("section", {"id": "profit-loss"})
        if pl_section:
            table = pl_section.find("table")
            if table:
                for row in table.find_all("tr"):
                    cells = row.find_all(["td", "th"])
                    if cells:
                        label = cells[0].get_text(strip=True).lower()
                        values = [c.get_text(strip=True) for c in cells[1:]]
                        latest = values[-1] if values else None
                        if not latest:
                            continue
                        val = _clean_number(latest)
                        if val is None:
                            continue
                        if "sales" in label or "revenue" in label:
                            result["revenue_cr"] = val
                        elif "net profit" in label:
                            result["net_profit_cr"] = val
                        elif label.strip() == "eps" or "eps" in label:
                            if "eps" not in result:
                                result["eps"] = val
                        elif "depreciation" in label:
                            result["depreciation_cr"] = val
                        elif "interest" in label:
                            result["interest_expense_cr"] = val

                # Compute net margin
                if "revenue_cr" in result and "net_profit_cr" in result and result["revenue_cr"]:
                    result["net_margin"] = (result["net_profit_cr"] / result["revenue_cr"]) * 100

        # ── Quarterly Results (latest quarter) ──────────────────
        q_section = soup.find("section", {"id": "quarters"})
        if q_section:
            table = q_section.find("table")
            if table:
                for row in table.find_all("tr"):
                    cells = row.find_all(["td", "th"])
                    if cells:
                        label = cells[0].get_text(strip=True).lower()
                        values = [c.get_text(strip=True) for c in cells[1:]]
                        latest = values[-1] if values else None
                        if not latest:
                            continue
                        val = _clean_number(latest)
                        if val is None:
                            continue
                        if "sales" in label or "revenue" in label:
                            result["quarterly_revenue_cr"] = val
                        elif "net profit" in label:
                            result["quarterly_net_profit_cr"] = val
                        elif "eps" in label:
                            result["quarterly_eps"] = val

        # ── Balance Sheet ───────────────────────────────────────
        bs_section = soup.find("section", {"id": "balance-sheet"})
        if bs_section:
            table = bs_section.find("table")
            if table:
                for row in table.find_all("tr"):
                    cells = row.find_all(["td", "th"])
                    if cells:
                        label = cells[0].get_text(strip=True).lower()
                        values = [c.get_text(strip=True) for c in cells[1:]]
                        latest = values[-1] if values else None
                        if not latest:
                            continue
                        val = _clean_number(latest)
                        if val is None:
                            continue
                        if "borrowing" in label or "loan" in label:
                            result["total_debt_cr"] = val
                        elif "equity" in label and "share" in label:
                            result["share_capital_cr"] = val
                        elif "reserves" in label:
                            result["reserves_cr"] = val

        # ── Cash Flow ───────────────────────────────────────────
        cf_section = soup.find("section", {"id": "cash-flow"})
        if cf_section:
            table = cf_section.find("table")
            if table:
                for row in table.find_all("tr"):
                    cells = row.find_all(["td", "th"])
                    if cells:
                        label = cells[0].get_text(strip=True).lower()
                        values = [c.get_text(strip=True) for c in cells[1:]]
                        latest = values[-1] if values else None
                        if not latest:
                            continue
                        val = _clean_number(latest)
                        if val is None:
                            continue
                        if "cash from operating" in label or "operating activity" in label:
                            result["operating_cf_cr"] = val
                        elif "investing" in label:
                            result["investing_cf_cr"] = val
                        elif "financing" in label or "funding" in label:
                            result["financing_cf_cr"] = val

                # Compute free cash flow
                if "operating_cf_cr" in result and "investing_cf_cr" in result:
                    result["free_cashflow_cr"] = result["operating_cf_cr"] + result["investing_cf_cr"]

        # ── Pros and Cons ───────────────────────────────────────
        pros_cons = soup.find("section", {"id": "analysis"})
        if pros_cons:
            pros_ul = pros_cons.find("ul", class_="pros")
            cons_ul = pros_cons.find("ul", class_="cons")
            if pros_ul:
                result["pros"] = [li.get_text(strip=True) for li in pros_ul.find_all("li")]
            if cons_ul:
                result["cons"] = [li.get_text(strip=True) for li in cons_ul.find_all("li")]

        # ── Company About ───────────────────────────────────────
        about = soup.find("section", {"id": "about"})
        if about:
            desc_p = about.find("p")
            if desc_p:
                result["description"] = desc_p.get_text(strip=True)[:500]

        # ── Peer comparison ─────────────────────────────────────
        peers_section = soup.find("section", {"id": "peers"})
        if peers_section:
            peer_table = peers_section.find("table")
            if peer_table:
                rows = peer_table.find_all("tr")[1:]  # skip header
                peers = []
                for row in rows[:5]:
                    cells = row.find_all("td")
                    if cells:
                        peer_name = cells[0].get_text(strip=True)
                        peers.append(peer_name)
                if peers:
                    result["peers"] = peers

        # ── Sector / Industry ───────────────────────────────────
        industry_tag = soup.find("a", href=lambda h: h and "/sector/" in str(h))
        if industry_tag:
            result["sector"] = industry_tag.get_text(strip=True)

        return result


# Singleton
screener_service = ScreenerService()
