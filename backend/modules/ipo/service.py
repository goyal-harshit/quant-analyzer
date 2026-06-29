"""
IPO service — live NSE data (free, no API key).

Sources (NSE public APIs, accessed via the cookie-warmed services.nse_live):
  /api/all-upcoming-issues?category=ipo  -> open + forthcoming issues
  /api/public-past-issues?category=eq    -> recently listed issues (1300+)

Status (UPCOMING / OPEN / CLOSED / LISTED) is derived from the live dates so
buckets stay correct. Recently-listed issues are enriched with a live current
price (Yahoo) to show return-vs-issue. A small curated seed list is kept only
as a last-resort fallback if NSE is unreachable.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import date, datetime, timezone, timedelta


from services.cache_service import cache

logger = logging.getLogger(__name__)

TTL_IPO = 2 * 3600
IST = timezone(timedelta(hours=5, minutes=30))


def _today() -> date:
    return datetime.now(IST).date()


# ── Last-resort fallback if NSE is unreachable (e.g. transient 403/throttle) ──
# Only shown when the live NSE feed can't be reached; real data replaces it as
# soon as NSE responds. Kept small and labelled as a fallback.
SEED_IPOS = [
    {"id": "seed-physicswallah", "company_name": "PhysicsWallah", "symbol": "PWALLAH",
     "ipo_type": "MAINBOARD", "issue_size_cr": 4200, "price_band_low": 103, "price_band_high": 109,
     "lot_size": 137, "open_date": "2026-06-18", "close_date": "2026-06-22", "listing_date": "2026-06-27",
     "gmp": 18, "subscription_times": 12.4},
    {"id": "seed-hdb", "company_name": "HDB Financial Services", "symbol": "HDBFS",
     "ipo_type": "MAINBOARD", "issue_size_cr": 12500, "price_band_low": 700, "price_band_high": 740,
     "lot_size": 20, "open_date": "2026-06-25", "close_date": "2026-06-27", "listing_date": "2026-07-02",
     "gmp": 55, "subscription_times": None},
    {"id": "seed-ather", "company_name": "Ather Energy", "symbol": "ATHER",
     "ipo_type": "MAINBOARD", "issue_size_cr": 3000, "price_band_low": 304, "price_band_high": 321,
     "lot_size": 46, "open_date": "2026-06-30", "close_date": "2026-07-02", "listing_date": "2026-07-07",
     "gmp": 12, "subscription_times": None},
    {"id": "seed-ntpcgreen", "company_name": "NTPC Green Energy", "symbol": "NTPCGREEN",
     "ipo_type": "MAINBOARD", "issue_size_cr": 10000, "price_band_low": 102, "price_band_high": 108,
     "issue_price": 108, "lot_size": 138, "open_date": "2026-05-28", "close_date": "2026-05-30",
     "listing_date": "2026-06-05", "listing_price": 118.5},
    {"id": "seed-swiggy", "company_name": "Swiggy", "symbol": "SWIGGY",
     "ipo_type": "MAINBOARD", "issue_size_cr": 11300, "price_band_low": 371, "price_band_high": 390,
     "issue_price": 390, "lot_size": 38, "open_date": "2026-05-20", "close_date": "2026-05-22",
     "listing_date": "2026-05-27", "listing_price": 412.0},
    {"id": "seed-emcure", "company_name": "Emcure Pharmaceuticals", "symbol": "EMCURE",
     "ipo_type": "MAINBOARD", "issue_size_cr": 1952, "price_band_low": 960, "price_band_high": 1008,
     "issue_price": 1008, "lot_size": 14, "open_date": "2026-05-12", "close_date": "2026-05-14",
     "listing_date": "2026-05-20", "listing_price": 1325.0},
]


def _parse(s):
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except (ValueError, TypeError):
        return None


def _nse_date(s):
    if not s:
        return None
    s = str(s).strip()
    for cand in (s, s.title()):
        for fmt in ("%d-%b-%Y", "%d-%m-%Y", "%Y-%m-%d", "%d-%B-%Y"):
            try:
                return datetime.strptime(cand, fmt).date().isoformat()
            except (ValueError, TypeError):
                continue
    return None


def _num(s):
    try:
        return float(str(s).replace(",", "").replace("Rs.", "").strip())
    except (ValueError, TypeError, AttributeError):
        return None


def _parse_band(s):
    """'Rs.144 to Rs.152' -> (144.0, 152.0); '66' -> (66, 66)."""
    if not s:
        return None, None
    import re
    # \d+(?:\.\d+)? avoids capturing the '.' in the 'Rs.' prefix as a leading decimal
    vals = [float(n) for n in re.findall(r"\d+(?:\.\d+)?", str(s).replace(",", ""))]
    vals = [v for v in vals if v > 0]
    if not vals:
        return None, None
    return min(vals), max(vals)


def _enrich(raw: dict, today: date) -> dict:
    item = dict(raw)
    item.setdefault("exchange", "NSE")
    item.setdefault("status", "UPCOMING")
    open_d, close_d, list_d = _parse(item.get("open_date")), _parse(item.get("close_date")), _parse(item.get("listing_date"))

    if list_d and today >= list_d:
        status = "LISTED"
    elif close_d and today > close_d:
        status = "CLOSED"
    elif open_d and close_d and open_d <= today <= close_d:
        status = "OPEN"
    elif open_d and today < open_d:
        status = "UPCOMING"
    else:
        status = item.get("status", "UPCOMING")
    item["status"] = status

    issue_price = item.get("issue_price") or item.get("price_band_high")
    lp, cp = item.get("listing_price"), item.get("current_price")
    if lp and issue_price:
        item["listing_gain_pct"] = round((lp / issue_price - 1) * 100, 2)
    elif cp and issue_price:
        item["listing_gain_pct"] = round((cp / issue_price - 1) * 100, 2)

    gmp, ref = item.get("gmp"), item.get("price_band_high")
    if gmp and ref:
        item["gmp_pct"] = round((gmp / ref) * 100, 2)
    return item


async def _fetch_live() -> list[dict]:
    """Fetch real open/upcoming + recently-listed IPOs from NSE. [] on failure."""
    try:
        from services.nse_live import get_json
    except Exception:
        return []

    out: list[dict] = []
    ref = "https://www.nseindia.com/market-data/all-upcoming-issues-ipo"

    # Fetch both feeds concurrently with a per-call bound, so a slow/blocked
    # past-issues call can't starve the (working) upcoming feed or blow the
    # overall budget and lose everything we already fetched.
    async def _safe(path):
        try:
            return await asyncio.wait_for(get_json(path, referer=ref), timeout=9)
        except Exception:
            return None

    up, past = await asyncio.gather(
        _safe("/api/all-upcoming-issues?category=ipo"),
        _safe("/api/public-past-issues?category=eq"),
    )

    # ── Open + upcoming ──
    for r in up or []:
        try:
            low, high = _parse_band(r.get("issuePrice"))
            shares = _num(r.get("issueSize"))
            series = (r.get("series") or "").upper()
            is_sme = "SME" in series or "SME" in (r.get("status") or "").upper()
            out.append({
                "id": f"nse-{r.get('symbol')}",
                "company_name": (r.get("companyName") or "").replace(" Limited", "").strip(),
                "symbol": r.get("symbol"),
                "ipo_type": "SME" if is_sme else "MAINBOARD",
                "price_band_low": low, "price_band_high": high,
                "issue_price": high,
                "issue_size_cr": round(shares * high / 1e7, 1) if (shares and high) else None,
                "open_date": _nse_date(r.get("issueStartDate")),
                "close_date": _nse_date(r.get("issueEndDate")),
            })
        except Exception:
            continue

    # ── Recently listed (filter to real equity/SME IPOs, most recent ~30) ──
    rows = []
    for r in past or []:
        ld = _nse_date(r.get("listingDate"))
        company = (r.get("companyName") or "").strip()
        series = (r.get("securityType") or "").upper()
        # Exclude debt/bond listings (blank company, non-equity series, penny prices)
        if not ld or not company or series not in ("EQ", "SME"):
            continue
        low, high = _parse_band(r.get("priceRange") or r.get("issuePrice"))
        issue_p = _num(r.get("issuePrice")) or high
        # Equity IPOs price ₹5–5000/share; outside that range = bonds/NCDs/debt
        if not issue_p or not (5 <= issue_p <= 5000):
            continue
        rows.append((ld, r, low, high, issue_p, series))
    rows.sort(key=lambda x: x[0], reverse=True)
    for ld, r, low, high, issue_p, series in rows[:30]:
        out.append({
            "id": f"nse-past-{r.get('symbol')}",
            "company_name": (r.get("companyName") or "").replace(" Limited", "").strip(),
            "symbol": r.get("symbol"),
            "ipo_type": "SME" if "SME" in series else "MAINBOARD",
            "price_band_low": low, "price_band_high": high,
            "issue_price": issue_p,
            "open_date": _nse_date(r.get("ipoStartDate")),
            "close_date": _nse_date(r.get("ipoEndDate")),
            "listing_date": ld,
        })
    return out


async def _enrich_listed_prices(items: list[dict]) -> None:
    """Add a live current price (Yahoo) to recently-listed items, in place."""
    listed = [i for i in items if i.get("status") == "LISTED" and i.get("symbol") and not i.get("current_price")]
    listed = listed[:18]  # bound the live calls
    if not listed:
        return
    try:
        from services.fast_data import fast_data_service
        import asyncio
        async def _one(it):
            try:
                q = await fast_data_service.get_quote(it["symbol"])
                if q and q.get("price"):
                    it["current_price"] = round(q["price"], 2)
            except Exception:
                pass
        sem = asyncio.Semaphore(6)
        async def _wrap(it):
            async with sem:
                await _one(it)
        await asyncio.gather(*[_wrap(it) for it in listed])
    except Exception:
        pass


async def get_all(refresh: bool = False) -> list[dict]:
    today = _today()
    cached = None if refresh else await cache.get("ipo:all")
    if cached:
        rows = json.loads(cached)
    else:
        # Bound the NSE fetch: when NSE blocks this host (HTTP 403), the cookie-warm
        # + retry path can stall ~90s per call, hanging the whole endpoint. Cap it
        # and fall back to seed so the page always responds quickly.
        try:
            rows = await asyncio.wait_for(_fetch_live(), timeout=16)
        except (asyncio.TimeoutError, Exception):
            logger.info("NSE IPO fetch timed out/failed — using seed fallback")
            rows = []
        if not rows:
            logger.info("NSE IPO live unavailable — using seed fallback")
            rows = SEED_IPOS
        rows = [_enrich(r, today) for r in rows]      # set status before price-enrich
        await _enrich_listed_prices(rows)
        await cache.set("ipo:all", json.dumps(rows), TTL_IPO)
    # Always (re)enrich on return — idempotent, guarantees status regardless of cache vintage.
    return [_enrich(r, today) for r in rows]


async def upcoming(refresh: bool = False):
    return [i for i in await get_all(refresh) if i.get("status") == "UPCOMING"]


async def open_ipos(refresh: bool = False):
    return [i for i in await get_all(refresh) if i.get("status") == "OPEN"]


async def listed(days: int = 90, refresh: bool = False):
    today = _today()
    cutoff = today - timedelta(days=days)
    out = [i for i in await get_all(refresh)
           if i.get("status") == "LISTED" and (_parse(i.get("listing_date")) or today) >= cutoff]
    out.sort(key=lambda x: x.get("listing_date", ""), reverse=True)
    return out


async def sme(refresh: bool = False):
    return [i for i in await get_all(refresh) if i.get("ipo_type") == "SME"]


async def calendar(month: str | None = None):
    today = _today()
    ym = month or today.strftime("%Y-%m")
    events: list[dict] = []
    for i in await get_all():
        for kind, field in (("OPEN", "open_date"), ("CLOSE", "close_date"), ("LISTING", "listing_date")):
            d = i.get(field)
            if d and d.startswith(ym):
                events.append({"date": d, "type": kind, "company_name": i["company_name"],
                               "symbol": i.get("symbol"), "ipo_type": i["ipo_type"]})
    events.sort(key=lambda e: e["date"])
    return {"month": ym, "events": events}
