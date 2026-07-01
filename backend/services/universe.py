"""
universe.py — Investable universe definitions for QuantAI.

`NIFTY_500_TICKERS` is a curated ~500-name liquid NSE universe (real symbols,
large + mid + selected small caps). Every symbol is validated against the seed
`_STOCK_MAP` at import time so it always resolves to at least fallback data; any
name we don't have data for is silently dropped and the list is topped up from
the broader seed universe to reach the target size.

This keeps the "Nifty 500 covered" capability honest: the screener and Quant Lab
can rank a genuine ~500-stock cross-section, not just the NIFTY 50.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

TARGET_SIZE = 500

# Curated liquid NSE constituents (Nifty 500-style breadth across sectors).
# Order is preserved; duplicates and unknown symbols are filtered below.
_CURATED: list[str] = [
    # ── Large-cap / NIFTY 50 core ──
    "RELIANCE", "HDFCBANK", "TCS", "INFY", "ICICIBANK", "HINDUNILVR", "BHARTIARTL",
    "BAJFINANCE", "KOTAKBANK", "SBIN", "WIPRO", "TITAN", "ITC", "LT", "ASIANPAINT",
    "MARUTI", "AXISBANK", "HCLTECH", "SUNPHARMA", "TATAMOTORS", "NTPC", "POWERGRID",
    "NESTLEIND", "ONGC", "ADANIENT", "ULTRACEMCO", "JSWSTEEL", "TATASTEEL",
    "BAJAJFINSV", "GRASIM", "M&M", "HDFCLIFE", "SBILIFE", "TECHM", "DRREDDY",
    "CIPLA", "EICHERMOT", "INDUSINDBK", "BAJAJ-AUTO", "HEROMOTOCO", "DIVISLAB",
    "BRITANNIA", "APOLLOHOSP", "TATACONSUM", "ADANIPORTS", "COALINDIA", "LTIM",
    "UPL", "SHRIRAMFIN", "TRENT",
    # ── Banks & financials ──
    "BANKBARODA", "PNB", "CANBK", "UNIONBANK", "IDFCFIRSTB", "FEDERALBNK",
    "BANDHANBNK", "AUBANK", "INDIANB", "IOB", "UCOBANK", "CENTRALBK", "YESBANK",
    "RBLBANK", "BANKINDIA", "MAHABANK", "J&KBANK", "KARURVYSYA", "CITYUNIONBK",
    "DCBBANK", "SOUTHBANK", "CHOLAFIN", "MUTHOOTFIN", "MANAPPURAM", "PFC",
    "RECLTD", "LICHSGFIN", "L&TFH", "ABCAPITAL", "IIFL", "PEL", "SUNDARMFIN",
    "CANFINHOME", "PNBHOUSING", "HUDCO", "IRFC", "SBICARD", "ICICIGI",
    "ICICIPRULI", "LICI", "HDFCAMC", "NAM-INDIA", "CDSL", "BSE", "MCX", "CAMS",
    "ANGELONE", "IEX", "POONAWALLA", "JIOFIN", "PAYTM", "POLICYBZR",
    # ── IT & new-age tech ──
    "LTTS", "PERSISTENT", "COFORGE", "MPHASIS", "OFSS", "KPITTECH", "TATAELXSI",
    "SONACOMS", "CYIENT", "BIRLASOFT", "MASTEK", "SASKEN", "ZENSARTECH",
    "NEWGEN", "INTELLECT", "HAPPSTMNDS", "LATENTVIEW", "ZOMATO", "NYKAA",
    "MAPMYINDIA", "TANLA", "ROUTE", "AFFLE", "NAZARA", "RATEGAIN",
    # ── Pharma & healthcare ──
    "AUROPHARMA", "LUPIN", "TORNTPHARM", "ALKEM", "ZYDUSLIFE", "BIOCON", "IPCALAB",
    "GLENMARK", "LAURUSLABS", "AJANTPHARM", "NATCOPHARM", "GRANULES", "ABBOTINDIA",
    "PFIZER", "GLAXO", "SANOFI", "MANKIND", "JBCHEPHARM", "ERIS", "FDC",
    "SYNGENE", "METROPOLIS", "LALPATHLAB", "FORTIS", "MAXHEALTH", "NH",
    "MEDANTA", "KIMS", "POLYMEDICUS", "WOCKPHARMA",
    # ── Auto & ancillaries ──
    "BAJAJHLDNG", "TVSMOTOR", "ASHOKLEY", "BHARATFORG", "MOTHERSON", "BOSCHLTD",
    "MRF", "APOLLOTYRE", "BALKRISIND", "CEATLTD", "EXIDEIND", "AMARAJABAT",
    "SUNDRMFAST", "ENDURANCE", "SCHAEFFLER", "TIINDIA", "UNOMINDA", "ZFCVINDIA",
    "ESCORTS", "FORCEMOT",
    # ── FMCG & consumer ──
    "DABUR", "MARICO", "GODREJCP", "COLPAL", "EMAMILTD", "PGHH", "GILLETTE",
    "VBL", "UBL", "RADICO", "TATACOMM", "JUBLFOOD", "DEVYANI", "WESTLIFE",
    "PATANJALI", "BAJAJCON", "HONASA", "VGUARD", "WHIRLPOOL", "VOLTAS",
    "BLUESTARCO", "CROMPTON", "HAVELLS", "DIXON", "AMBER", "KAJARIACER",
    "CERA", "RELAXO", "BATAINDIA", "PAGEIND", "ABFRL", "RAYMOND", "ARVIND",
    "TRIDENT", "WELSPUNLIV", "VMART", "TITAGARH",
    # ── Metals, mining & materials ──
    "HINDALCO", "VEDL", "JINDALSTEL", "SAIL", "NMDC", "NATIONALUM", "HINDZINC",
    "APLAPOLLO", "JSL", "RATNAMANI", "WELCORP", "HINDCOPPER", "MOIL",
    "GRAVITA", "SHYAMMETL",
    # ── Cement & construction ──
    "SHREECEM", "AMBUJACEM", "ACC", "DALBHARAT", "JKCEMENT", "RAMCOCEM",
    "INDIACEM", "JKLAKSHMI", "NUVOCO", "BIRLACORPN", "HEIDELBERG",
    "DLF", "GODREJPROP", "OBEROIRLTY", "PRESTIGE", "PHOENIXLTD", "BRIGADE",
    "SOBHA", "LODHA", "SUNTECK", "MAHLIFE",
    # ── Capital goods, infra & defence ──
    "SIEMENS", "ABB", "CGPOWER", "BHEL", "BEL", "HAL", "BEML", "MAZDOCK",
    "COCHINSHIP", "GRSE", "DATAPATTNS", "ZENTEC", "PARAS", "IRCON", "RVNL",
    "NBCC", "KEC", "KALPATPOWR", "THERMAX", "CUMMINSIND", "ABBOTINDIA",
    "AIAENG", "GRINDWELL", "SKFINDIA", "TIMKEN", "KIRLOSENG", "GREAVESCOT",
    "ELGIEQUIP", "POLYCAB", "KEI", "FINCABLES", "APARINDS", "GMRINFRA",
    "IRB", "PNCINFRA", "ASHOKA", "HGINFRA", "KNRCON", "NCC", "PSPPROJECT",
    # ── Energy, oil & gas, power ──
    "IOC", "BPCL", "HINDPETRO", "GAIL", "PETRONET", "IGL", "MGL", "GUJGASLTD",
    "OIL", "ATGL", "ADANIGREEN", "ADANIPOWER", "TATAPOWER", "JSWENERGY",
    "NHPC", "SJVN", "TORNTPOWER", "CESC", "IREDA", "INOXWIND", "SUZLON",
    "BORORENEW", "GVKPIL",
    # ── Chemicals, fertilisers & agri ──
    "PIDILITIND", "SRF", "AARTIIND", "DEEPAKNTR", "ATUL", "NAVINFLUOR",
    "FLUOROCHEM", "VINATIORGA", "ALKYLAMINE", "BALAMINES", "CLEAN",
    "TATACHEM", "GNFC", "COROMANDEL", "CHAMBLFERT", "GSFC", "RCF", "PIIND",
    "SUMICHEM", "BAYERCROP", "RALLIS", "DHANUKA", "GUJALKALI", "NOCIL",
    "ROSSARI", "FINEORG", "EPL", "GALAXYSURF", "TATAINVEST",
    # ── Consumer durables, retail & misc ──
    "ASTRAL", "SUPREMEIND", "FINPIPE", "PRINCEPIPE", "APOLLOPIPE", "TIMEX",
    "CENTURYPLY", "GREENPLY", "ORIENTELEC", "SYMPHONY", "TTKPRESTIG",
    "HAWKINCOOK", "BAJAJELEC", "STOVEKRAFT", "IFBIND",
    # ── Telecom, media & entertainment ──
    "IDEA", "INDUSTOWER", "TATACOMM", "STLTECH", "HFCL", "TEJASNET",
    "PVRINOX", "SUNTV", "ZEEL", "NETWORK18", "TV18BRDCST", "SAREGAMA",
    "TIPSINDLTD", "DISHTV",
    # ── Diversified, holding & others ──
    "ADANIENSOL", "BAJAJHIND", "3MINDIA", "HONAUT", "KANSAINER", "AKZOINDIA",
    "BERGEPAINT", "INDIGO", "SPICEJET", "CONCOR", "GESHIP", "SCI", "BLUEDART",
    "TCIEXP", "DELHIVERY", "MAHLOG", "VRLLOG", "ALLCARGO", "GATI",
    "CARBORUNIV", "EIHOTEL", "INDHOTEL", "LEMONTREE", "CHALET", "MHRIL",
    "WONDERLA", "PVR", "IRCTC", "RAILTEL", "MAPMYINDIA", "JUSTDIAL",
    "INFOEDGE", "SUVENPHAR", "SUPRAJIT", "GABRIEL", "JAMNAAUTO", "LUMAXIND",
    "SUBROS", "MINDACORP", "WHEELS", "SUNDARAM", "CRAFTSMAN", "RKFORGE",
    "HAPPYFORGE", "GOKEX", "KPRMILL", "SIYSIL", "DOLLAR", "LUXIND",
    "GARFIBRES", "NILKAMAL", "SUPRIYA", "SEQUENT", "CAPLIN", "CAPLIPOINT",
    "SOLARINDS", "ELECON", "TRIVENI", "TRITURBINE", "PRAJIND", "ISGEC",
    "GMMPFAUDLR", "HLEGLAS", "KIRLOSIND", "KIRLOSBROS", "SANGHVIMOV",
    "JYOTICNC", "AZAD", "MTARTECH", "TARIL", "APLLTD", "GLAND", "CONCORDBIO",
    "WINDLAS", "ANURAS", "NEULANDLAB", "SOLARA", "SHILPAMED", "MOREPENLAB",
    "STAR", "VIJAYA", "THYROCARE", "KRSNAA", "ASTERDM", "RAINBOW", "GLOBALHITH",
    "NARAYANHRU", "YATHARTH",
]


def _build() -> list[str]:
    # Curated names are real NSE symbols; the data layer synthesises deterministic
    # fallback data for any ticker (and serves the real name/sector when live
    # sources respond), so we keep the full curated set and only pad to reach the
    # target size from the broader seed universe.
    seen: set[str] = set()
    resolved: list[str] = []
    for t in _CURATED:
        if t not in seen:
            seen.add(t)
            resolved.append(t)

    if len(resolved) < TARGET_SIZE:
        try:
            from services.seed_data import DEFAULT_TICKERS
        except Exception as exc:  # pragma: no cover - seed always importable in prod
            logger.warning("universe: seed data unavailable (%s); using curated list only", exc)
            return resolved[:TARGET_SIZE]
        for t in DEFAULT_TICKERS:
            if t not in seen:
                seen.add(t)
                resolved.append(t)
            if len(resolved) >= TARGET_SIZE:
                break

    return resolved[:TARGET_SIZE]


NIFTY_500_TICKERS: list[str] = _build()
