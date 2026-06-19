"""
seed_data.py — Deterministic seed data for 100 Indian stocks.
Provides reliable offline fallback when live data sources fail.
"""
import hashlib
import math
import random
from datetime import datetime, timedelta

STOCK_MASTER = [
    # ticker, name, sector, basePrice, pe, pb, roe, revGrowth, momentum, quality, value, growth, marketCapCr
    ("RELIANCE", "Reliance Industries", "Energy", 2847.5, 24.5, 2.1, 15.2, 12.3, 67, 78, 71, 63, 192400),
    ("HDFCBANK", "HDFC Bank", "Banking", 1742.3, 19.2, 2.8, 17.1, 18.5, 72, 85, 76, 74, 132300),
    ("TCS", "Tata Consultancy Services", "IT", 3912.5, 28.7, 12.4, 47.2, 8.7, 61, 92, 52, 58, 142100),
    ("INFY", "Infosys Ltd", "IT", 1478.9, 25.3, 8.9, 33.8, 9.1, 58, 88, 60, 56, 61400),
    ("ICICIBANK", "ICICI Bank", "Banking", 1089.8, 17.8, 2.9, 17.9, 22.1, 81, 82, 79, 79, 76800),
    ("HINDUNILVR", "Hindustan Unilever", "FMCG", 2534.6, 58.3, 11.2, 19.5, 3.2, 45, 87, 35, 42, 59400),
    ("BHARTIARTL", "Bharti Airtel", "Telecom", 1621.3, 65.2, 5.8, 9.2, 24.5, 89, 72, 38, 82, 96100),
    ("BAJFINANCE", "Bajaj Finance", "NBFC", 6834.2, 32.4, 6.1, 19.8, 28.7, 76, 79, 55, 84, 42300),
    ("KOTAKBANK", "Kotak Mahindra Bank", "Banking", 1823.4, 21.5, 3.2, 15.8, 15.3, 55, 83, 72, 65, 36200),
    ("SBIN", "State Bank of India", "Banking", 795.6, 11.2, 1.5, 14.2, 18.9, 73, 71, 88, 71, 70900),
    ("WIPRO", "Wipro Ltd", "IT", 462.3, 22.7, 4.2, 18.5, 3.1, 42, 78, 67, 38, 24100),
    ("TITAN", "Titan Company", "Consumer", 3287.5, 82.4, 17.3, 21.2, 19.8, 71, 84, 28, 76, 29100),
    ("ITC", "ITC Ltd", "FMCG", 482.5, 27.8, 6.8, 25.1, 7.5, 48, 86, 69, 52, 60300),
    ("LT", "Larsen & Toubro", "Capital Goods", 3567.8, 35.2, 5.4, 16.3, 17.2, 77, 75, 54, 73, 49000),
    ("ASIANPAINT", "Asian Paints", "Consumer", 2891.3, 65.8, 16.2, 25.4, 5.3, 38, 89, 32, 44, 27700),
    ("MARUTI", "Maruti Suzuki", "Auto", 12543.5, 29.7, 4.8, 16.8, 13.4, 62, 76, 61, 67, 39000),
    ("AXISBANK", "Axis Bank", "Banking", 1156.8, 15.8, 2.3, 16.2, 20.4, 68, 74, 81, 75, 35700),
    ("HCLTECH", "HCL Technologies", "IT", 1623.5, 24.1, 6.7, 28.3, 7.9, 56, 83, 63, 57, 44000),
    ("SUNPHARMA", "Sun Pharmaceutical", "Pharma", 1687.2, 38.4, 6.2, 16.8, 11.2, 74, 79, 49, 63, 40500),
    ("TATAMOTORS", "Tata Motors", "Auto", 967.4, 12.4, 3.2, 26.4, 22.7, 85, 68, 77, 82, 35500),
    ("NTPC", "NTPC Ltd", "Energy", 387.3, 15.2, 2.1, 14.1, 9.7, 71, 72, 84, 58, 37600),
    ("POWERGRID", "Power Grid Corp", "Energy", 342.6, 18.7, 3.1, 17.2, 8.4, 63, 78, 77, 54, 31800),
    ("NESTLEIND", "Nestle India", "FMCG", 2401.8, 74.2, 94.3, 127.5, 6.8, 35, 91, 22, 46, 23100),
    ("ONGC", "ONGC Ltd", "Energy", 281.4, 7.8, 0.9, 12.4, 14.2, 55, 65, 93, 59, 35400),
    ("ADANIENT", "Adani Enterprises", "Conglomerate", 2847.6, 78.3, 4.8, 6.2, 35.4, 82, 52, 31, 88, 32400),
    ("YESBANK", "Yes Bank", "Banking", 24.5, 35.2, 1.8, 4.2, 15.7, 44, 35, 62, 58, 12500),
    ("IDFCFIRSTB", "IDFC First Bank", "Banking", 82.3, 28.5, 2.1, 8.9, 19.2, 52, 48, 58, 64, 9800),
    ("BANDHANBNK", "Bandhan Bank", "Banking", 215.6, 22.4, 3.2, 12.5, 16.8, 48, 52, 65, 61, 8700),
    ("FEDERALBNK", "Federal Bank", "Banking", 162.8, 14.5, 1.9, 13.8, 17.4, 56, 58, 72, 63, 7200),
    ("RBLBANK", "RBL Bank", "Banking", 252.4, 18.7, 2.5, 10.2, 15.1, 41, 42, 68, 52, 5400),
    ("TECHM", "Tech Mahindra", "IT", 1285.6, 20.3, 5.8, 22.4, 6.2, 38, 71, 55, 42, 32400),
    ("LTI", "LTI Mindtree", "IT", 5487.3, 32.5, 9.2, 28.7, 14.3, 64, 82, 48, 61, 28100),
    ("MINDTREE", "Mindtree", "IT", 3845.2, 29.8, 7.6, 31.5, 11.8, 59, 84, 52, 58, 18200),
    ("PERSISTENT", "Persistent Systems", "IT", 4521.6, 35.4, 10.2, 26.8, 17.5, 72, 79, 44, 67, 16700),
    ("CYIENT", "Cyient", "IT", 1876.4, 22.5, 4.8, 19.2, 12.4, 54, 68, 58, 52, 8300),
    ("MPHASIS", "Mphasis", "IT", 2487.5, 26.7, 5.9, 23.5, 9.8, 47, 76, 54, 48, 12100),
    ("M&M", "Mahindra & Mahindra", "Auto", 1987.5, 24.8, 3.9, 18.5, 16.2, 68, 74, 62, 71, 35700),
    ("BAJAJ-AUTO", "Bajaj Auto", "Auto", 7654.3, 28.5, 6.8, 22.1, 11.5, 58, 78, 56, 62, 22500),
    ("EICHERMOT", "Eicher Motors", "Auto", 4256.8, 32.4, 7.2, 24.8, 13.7, 65, 81, 51, 67, 11800),
    ("HEROMOTOCO", "Hero MotoCorp", "Auto", 4852.6, 21.5, 5.4, 26.2, 8.9, 46, 75, 64, 54, 24800),
    ("TVSMOTOR", "TVS Motor", "Auto", 2156.4, 35.8, 8.5, 28.4, 19.5, 74, 77, 48, 72, 16200),
    ("ASHOKLEY", "Ashok Leyland", "Auto", 184.5, 18.2, 3.5, 15.8, 14.2, 57, 62, 68, 61, 10400),
    ("ESCORTS", "Escorts Kubota", "Auto", 3245.7, 30.6, 5.2, 17.4, 12.8, 52, 69, 58, 55, 9200),
    ("BOSCHLTD", "Bosch Ltd", "Auto", 25874.5, 42.8, 9.8, 20.5, 7.2, 44, 82, 42, 48, 7800),
    ("DRREDDY", "Dr Reddy's Labs", "Pharma", 5784.5, 20.5, 4.8, 24.2, 12.8, 62, 78, 58, 63, 19500),
    ("CIPLA", "Cipla", "Pharma", 1425.7, 28.4, 5.2, 16.8, 9.5, 48, 68, 54, 51, 22800),
    ("DIVISLAB", "Divis Laboratories", "Pharma", 4187.2, 45.6, 12.4, 28.5, 8.2, 53, 84, 38, 56, 11200),
    ("AUROPHARMA", "Aurobindo Pharma", "Pharma", 1158.4, 18.5, 3.2, 21.8, 14.5, 58, 65, 65, 59, 14200),
    ("LUPIN", "Lupin", "Pharma", 1624.8, 25.6, 4.5, 15.2, 11.8, 46, 62, 56, 53, 15600),
    ("BIOCON", "Biocon", "Pharma", 324.5, 35.8, 5.8, 12.4, 16.8, 52, 58, 48, 61, 8200),
    ("TORNETPHARMA", "Torrent Pharma", "Pharma", 2785.6, 32.4, 7.2, 22.8, 13.5, 61, 74, 52, 64, 9500),
    ("CADILAHC", "Cadila Healthcare", "Pharma", 624.8, 22.5, 4.2, 18.6, 10.2, 44, 63, 59, 52, 12800),
    ("GLENMARK", "Glenmark Pharma", "Pharma", 896.4, 26.8, 3.8, 14.5, 8.9, 38, 55, 62, 47, 7200),
    ("BRITANNIA", "Britannia Industries", "FMCG", 5248.6, 52.4, 14.8, 28.5, 7.8, 47, 82, 38, 52, 12500),
    ("DABUR", "Dabur India", "FMCG", 587.4, 45.6, 9.8, 22.4, 6.5, 42, 78, 42, 48, 10200),
    ("MARICO", "Marico", "FMCG", 568.2, 38.5, 8.5, 24.8, 7.2, 44, 76, 46, 50, 7500),
    ("GODREJCP", "Godrej Consumer", "FMCG", 1285.6, 42.8, 10.2, 20.5, 8.4, 48, 74, 40, 52, 9500),
    ("COLPAL", "Colgate Palmolive", "FMCG", 2684.5, 48.6, 15.8, 32.5, 5.8, 36, 84, 32, 42, 7200),
    ("JUBLFOOD", "Jubilant FoodWorks", "FMCG", 524.8, 62.5, 18.4, 28.2, 14.5, 55, 72, 28, 65, 5400),
    ("GAIL", "GAIL India", "Energy", 205.6, 12.5, 1.8, 15.2, 11.8, 52, 62, 78, 58, 25800),
    ("IOC", "Indian Oil Corp", "Energy", 165.4, 8.5, 1.2, 14.8, 16.5, 48, 54, 85, 62, 42100),
    ("BPCL", "Bharat Petroleum", "Energy", 624.8, 9.8, 1.5, 16.2, 13.8, 51, 58, 82, 57, 28700),
    ("TATAPOWER", "Tata Power", "Energy", 385.6, 22.5, 3.2, 12.8, 15.2, 58, 62, 62, 63, 18200),
    ("ADANIGREEN", "Adani Green Energy", "Energy", 1856.4, 85.6, 12.5, 4.8, 42.5, 88, 38, 22, 92, 24500),
    ("TRENT", "Trent Ltd", "Consumer", 3456.8, 72.5, 22.8, 32.5, 35.8, 82, 86, 28, 88, 15200),
    ("DMART", "Avenue Supermarts", "Consumer", 4125.6, 85.4, 18.5, 24.8, 18.5, 68, 84, 24, 72, 26800),
    ("ZOMATO", "Zomato Ltd", "Consumer", 198.5, -45.2, 8.5, -2.5, 52.8, 92, 28, 18, 95, 18500),
    ("PAYTM", "One 97 Communications", "Consumer", 524.8, -28.5, 4.2, -8.5, 38.5, 54, 22, 32, 78, 4200),
    ("NYKAA", "FSN E-Commerce", "Consumer", 185.6, -52.4, 6.8, -4.2, 45.2, 62, 32, 28, 88, 5800),
    ("AVENUE", "Avenue Supermarts", "Consumer", 4125.6, 85.4, 18.5, 24.8, 18.5, 68, 84, 24, 72, 26800),
    ("IDEA", "Vodafone Idea", "Telecom", 14.8, -8.5, 0.5, -12.5, 8.5, 28, 15, 42, 32, 6800),
    ("INDUSTOWER", "Indus Towers", "Telecom", 345.8, 28.5, 4.8, 18.5, 12.8, 55, 62, 58, 56, 11300),
    ("SIEMENS", "Siemens India", "Capital Goods", 6254.8, 48.5, 8.5, 18.2, 14.5, 62, 76, 42, 62, 22500),
    ("BHEL", "BHEL", "Capital Goods", 285.6, 32.5, 2.8, 8.5, 22.5, 58, 42, 54, 68, 9500),
    ("HAVELS", "Havells India", "Capital Goods", 1785.6, 52.8, 9.8, 22.5, 16.8, 64, 78, 42, 66, 11200),
    ("ABB", "ABB India", "Capital Goods", 5678.4, 58.6, 12.5, 24.8, 18.5, 68, 80, 38, 68, 10800),
    ("CUMMINS", "Cummins India", "Capital Goods", 3245.8, 42.5, 7.8, 26.4, 15.2, 58, 76, 48, 62, 9200),
    ("ULTRACEMCO", "UltraTech Cement", "Others", 10568.5, 38.5, 4.8, 14.2, 11.5, 55, 68, 58, 58, 36200),
    ("GRASIM", "Grasim Industries", "Others", 2485.6, 28.5, 2.8, 12.5, 14.8, 52, 62, 65, 61, 21800),
    ("JSWSTEEL", "JSW Steel", "Others", 875.6, 15.8, 2.5, 18.5, 22.4, 72, 62, 72, 74, 28400),
    ("TATASTEEL", "Tata Steel", "Others", 165.8, 12.5, 1.8, 16.8, 18.5, 62, 58, 78, 68, 25200),
    ("HINDALCO", "Hindalco Industries", "Others", 625.8, 14.8, 2.2, 17.5, 20.5, 65, 60, 74, 70, 18600),
    ("VEDANTA", "Vedanta Ltd", "Others", 428.6, 10.5, 1.5, 22.4, 25.8, 74, 55, 82, 76, 12200),
    ("INDUSINDBK", "IndusInd Bank", "Others", 1456.8, 18.5, 2.5, 15.8, 19.5, 62, 68, 72, 68, 15200),
    ("SRTRANSFIN", "Shriram Finance", "Others", 3245.8, 22.5, 3.2, 16.8, 18.5, 58, 65, 65, 64, 9800),
    ("DLF", "DLF Ltd", "Others", 865.4, 35.8, 4.5, 12.5, 22.8, 72, 52, 52, 74, 24500),
    ("GODREJPROP", "Godrej Properties", "Others", 2584.6, 42.5, 5.2, 14.8, 28.5, 76, 56, 48, 78, 6800),
    ("ADANIPORTS", "Adani Ports", "Others", 1425.8, 32.5, 4.8, 16.5, 18.5, 68, 64, 58, 65, 32100),
    ("PNB", "Punjab National Bank", "Others", 125.6, 8.5, 0.8, 12.5, 16.8, 52, 45, 82, 58, 18900),
    ("CANBK", "Canara Bank", "Others", 425.8, 7.8, 1.2, 16.5, 19.2, 58, 52, 85, 62, 15200),
    ("UNIONBANK", "Union Bank of India", "Others", 145.6, 9.5, 1.1, 14.8, 17.5, 54, 48, 80, 60, 10800),
    ("HDFCLIFE", "HDFC Life Insurance", "Others", 685.8, 65.8, 12.5, 18.5, 14.8, 56, 72, 32, 58, 14200),
    ("SBILIFE", "SBI Life Insurance", "Others", 1568.4, 72.5, 14.8, 20.5, 16.8, 62, 74, 28, 62, 12400),
    ("ICICIPRULI", "ICICI Prudential Life", "Others", 625.8, 58.6, 10.5, 16.8, 12.5, 48, 68, 36, 54, 10200),
    ("APOLLOHOSP", "Apollo Hospitals", "Others", 6234.8, 68.5, 12.8, 18.5, 15.8, 62, 76, 32, 64, 28400),
    ("TATACONSUM", "Tata Consumer Products", "Others", 1125.6, 52.8, 8.5, 16.2, 14.5, 54, 72, 42, 58, 10800),
    ("COFORGE", "Coforge", "IT", 6245.8, 32.5, 8.5, 26.8, 16.5, 62, 78, 48, 64, 7200),
    ("HEXAWARE", "Hexaware Technologies", "IT", 856.4, 24.5, 5.2, 22.4, 11.8, 52, 72, 56, 54, 4800),
    ("ZENSAR", "Zensar Technologies", "IT", 624.8, 20.5, 4.2, 18.5, 9.8, 44, 68, 58, 48, 3500),
    ("HALDYNAT", "Haldyn Glass", "FMCG", 452.6, 18.5, 2.8, 12.5, 15.8, 48, 48, 62, 56, 1200),
    ("TATACOMM", "Tata Communications", "Telecom", 1845.6, 28.5, 3.8, 14.5, 12.8, 52, 62, 58, 56, 5400),
    ("THERMAX", "Thermax Ltd", "Capital Goods", 4258.6, 52.8, 8.5, 18.5, 16.8, 62, 74, 42, 62, 4800),
    ("BANKBARODA", "Bank of Baroda", "Others", 265.8, 8.5, 1.4, 17.5, 18.5, 58, 54, 84, 63, 16800),
    ("INDIANB", "Indian Bank", "Others", 485.6, 9.5, 1.5, 15.8, 16.5, 52, 50, 80, 58, 7200),
]


# ── EXTENDED UNIVERSE (~430 additional NSE stocks, 3-field entries) ──
# Financials are generated dynamically by _stock_dict()
EXTRA_STOCKS = [
    ('ADANIGREEN','Adani Green Energy','Energy'),('ADANIPOWER','Adani Power','Energy'),
    ('ATGL','Adani Total Gas','Energy'),('AMBUJACEM','Ambuja Cements','Infrastructure'),
    ('BANKBARODA','Bank of Baroda','Banking'),('BANDHANBNK','Bandhan Bank','Banking'),
    ('BERGEPAINT','Berger Paints','Consumer'),('BIOCON','Biocon','Pharma'),
    ('BOSCHLTD','Bosch Ltd','Auto'),('CDSL','CDSL','Financial Services'),
    ('CONCOR','Container Corp','Logistics'),('DABUR','Dabur India','FMCG'),
    ('DELHIVERY','Delhivery','Logistics'),('DLF','DLF Ltd','Real Estate'),
    ('EICHERMOT','Eicher Motors','Auto'),('ESCORTS','Escorts Kubota','Auto'),
    ('FEDERALBNK','Federal Bank','Banking'),('GAIL','GAIL India','Energy'),
    ('GODREJCP','Godrej Consumer','FMCG'),('GODREJPROP','Godrej Properties','Real Estate'),
    ('GODREJIND','Godrej Industries','Consumer'),('GUJGASLTD','Gujarat Gas','Energy'),
    ('HAL','HAL','Defence'),('HAVELLS','Havells India','Consumer'),
    ('HINDALCO','Hindalco','Metals'),('HINDZINC','Hindustan Zinc','Metals'),
    ('IDEA','Vodafone Idea','Telecom'),('IDFCFIRSTB','IDFC First Bank','Banking'),
    ('INDIAMART','IndiaMart','IT'),('INDIGO','InterGlobe Aviation','Aviation'),
    ('INDUSINDBK','IndusInd Bank','Banking'),('IOC','Indian Oil','Energy'),
    ('IPCALAB','Ipca Labs','Pharma'),('JINDALSTEL','Jindal Steel','Metals'),
    ('JSWENERGY','JSW Energy','Energy'),('JUBLFOOD','Jubilant FoodWorks','FMCG'),
    ('LALPATHLAB','Dr Lal PathLabs','Healthcare'),('LICHSGFIN','LIC Housing Finance','NBFC'),
    ('LUPIN','Lupin','Pharma'),('M&MFIN','M&M Financial','NBFC'),
    ('MCDOWELL-N','United Spirits','FMCG'),('MFSL','Max Financial','Insurance'),
    ('MOTHERSUMI','Motherson Sumi','Auto'),('MRF','MRF Tyres','Auto'),
    ('MUTHOOTFIN','Muthoot Finance','NBFC'),('NAUKRI','Info Edge India','IT'),
    ('NHPC','NHPC','Power'),('NMDC','NMDC','Metals'),
    ('NTPC','NTPC','Power'),('PAGEIND','Page Industries','Textiles'),
    ('PEL','Piramal Enterprises','Pharma'),('PETRONET','Petronet LNG','Energy'),
    ('PFC','Power Finance Corp','NBFC'),('PIDILITIND','Pidilite Industries','Chemicals'),
    ('PIIND','PI Industries','Chemicals'),('POLYCAB','Polycab India','Consumer'),
    ('POWERGRID','Power Grid Corp','Power'),('PVRINOX','PVR INOX','Media'),
    ('RAILTEL','RailTel Corp','Telecom'),('RAMCOCEM','Ramco Cements','Infrastructure'),
    ('RBLBANK','RBL Bank','Banking'),('RECLTD','REC Ltd','NBFC'),
    ('SAIL','Steel Authority of India','Metals'),('SIEMENS','Siemens India','Capital Goods'),
    ('SRTRANSFIN','Shriram Transport','NBFC'),('SUNTV','Sun TV Network','Media'),
    ('SYNGENE','Syngene International','Pharma'),('TATACOMM','Tata Communications','Telecom'),
    ('TATAELXSI','Tata Elxsi','IT'),('TATAPOWER','Tata Power','Power'),
    ('TORNTPHARM','Torrent Pharma','Pharma'),('TRENT','Trent','Retail'),
    ('TVSMOTOR','TVS Motor','Auto'),('UBL','United Breweries','FMCG'),
    ('VEDL','Vedanta','Metals'),('VOLTAS','Voltas','Consumer'),
    ('WHIRLPOOL','Whirlpool India','Consumer'),('ZEEL','Zee Entertainment','Media'),
    ('ZOMATO','Zomato','IT'),('PAYTM','One97 Communications','IT'),
    ('NYTAA','FSN E-Commerce','Retail'),('AARTIIND','Aarti Industries','Chemicals'),
    ('ABFRL','Aditya Birla Fashion','Retail'),('ALOKINDS','Alok Industries','Textiles'),
    ('ANGELONE','Angel One','Financial Services'),('APLLTD','Alembic Pharma','Pharma'),
    ('ASTERDM','Aster DM Healthcare','Healthcare'),('ASTRAL','Astral Ltd','Infrastructure'),
    ('AUBANK','AU Small Finance Bank','Banking'),('AURIONPRO','Aurionpro Solutions','IT'),
    ('AVANTIFEED','Avanti Feeds','FMCG'),('BALKRISIND','Balkrishna Industries','Auto'),
    ('BALRAMCHIN','Balrampur Chini','FMCG'),('BASF','BASF India','Chemicals'),
    ('BATAINDIA','Bata India','Retail'),('BCG','Brightcom Group','IT'),
    ('BEML','BEML Ltd','Capital Goods'),('BHARATFORG','Bharat Forge','Auto'),
    ('BHEL','BHEL','Capital Goods'),('BLUESTARCO','Blue Star','Consumer'),
    ('BSE','BSE Ltd','Financial Services'),('CAMS','CAMS','Financial Services'),
    ('CANFINHOME','Can Fin Homes','NBFC'),('CARBORUNIV','Carborundum Universal','Infrastructure'),
    ('CEATLTD','CEAT Tyres','Auto'),('CENTURYTEX','Century Textiles','Textiles'),
    ('CESC','CESC','Power'),('CGPOWER','CG Power','Capital Goods'),
    ('CHAMBLFERT','Chambal Fertilizers','Chemicals'),('CHOLA','Cholamandalam Finance','NBFC'),
    ('COCHINSHIP','Cochin Shipyard','Capital Goods'),('COLPAL','Colgate Palmolive','FMCG'),
    ('CRISIL','CRISIL','Financial Services'),('CROMPTON','Crompton Greaves','Consumer'),
    ('CUMMINSIND','Cummins India','Capital Goods'),('DALBHARAT','Dalmia Bharat','Infrastructure'),
    ('DEEPAKNTR','Deepak Nitrite','Chemicals'),('DIVISLAB','Divis Labs','Pharma'),
    ('DRREDDY','Dr Reddys Labs','Pharma'),('EIDPARRY','EID Parry','FMCG'),
    ('ELGIEQUIP','Elgi Equipments','Capital Goods'),('EMAMILTD','Emami Ltd','FMCG'),
    ('ENDURANCE','Endurance Tech','Auto'),('ERIS','Eris Lifesciences','Pharma'),
    ('EXIDEIND','Exide Industries','Auto'),('FACT','Fertilizers & Chem','Chemicals'),
    ('FINPIPE','Finolex Industries','Infrastructure'),('FORTIS','Fortis Healthcare','Healthcare'),
    ('FSL','Firstsource Solutions','IT'),('GALAXYSURF','Galaxy Surfactants','Chemicals'),
    ('GICRE','GIC Re','Insurance'),('GLAXO','GlaxoSmithKline Pharma','Pharma'),
    ('GLENMARK','Glenmark Pharma','Pharma'),('GMRINFRA','GMR Airports','Infrastructure'),
    ('GPPL','Gujarat Pipavav Port','Logistics'),('GRASIM','Grasim Industries','Infrastructure'),
    ('GRINFRA','GR Infraprojects','Infrastructure'),('GSFC','Gujarat State Fertilizers','Chemicals'),
    ('GSPL','Gujarat State Petronet','Energy'),('HCC','HCC','Infrastructure'),
    ('HDFCAMC','HDFC AMC','Financial Services'),('HEG','HEG Ltd','Infrastructure'),
    ('HINDCOPPER','Hindustan Copper','Metals'),('HINDPETRO','HPCL','Energy'),
    ('HOMEFIRST','Home First Finance','NBFC'),('ICICIGI','ICICI Lombard','Insurance'),
    ('ICICIPRULI','ICICI Prudential','Insurance'),('IDBI','IDBI Bank','Banking'),
    ('IGL','Indraprastha Gas','Energy'),('IIFL','IIFL Finance','NBFC'),
    ('INDHOTEL','Indian Hotels','Hospitality'),('INDIACEM','India Cements','Infrastructure'),
    ('IRB','IRB Infra','Infrastructure'),('IRCON','Ircon International','Infrastructure'),
    ('JAMNAAUTO','Jamna Auto','Auto'),('JBCHEPHARM','JB Chemicals','Pharma'),
    ('JKCEMENT','JK Cement','Infrastructure'),('JSL','Jindal Stainless','Metals'),
    ('JYOTHYLAB','Jyothy Labs','FMCG'),('KALPANKALP','Kalpataru Projects','Infrastructure'),
    ('KANSAINER','Kansai Nerolac','Consumer'),('KEC','KEC International','Infrastructure'),
    ('KEI','KEI Industries','Infrastructure'),('KPITTECH','KPIT Technologies','IT'),
    ('KRBL','KRBL Ltd','FMCG'),('L&TFH','L&T Finance','NBFC'),
    ('LAURUSLABS','Laurus Labs','Pharma'),('LEMONTREE','Lemon Tree Hotels','Hospitality'),
    ('LINDEINDIA','Linde India','Chemicals'),('LTTS','L&T Technology Services','IT'),
    ('MAHABANK','Bank of Maharashtra','Banking'),('MANAPPURAM','Manappuram Finance','NBFC'),
    ('MARICO','Marico','FMCG'),('MAZDOCK','Mazagon Dock','Defence'),
    ('MCX','MCX','Financial Services'),('METROPOLIS','Metropolis Healthcare','Healthcare'),
    ('MGL','Mahanagar Gas','Energy'),('MINDACORP','Minda Corporation','Auto'),
    ('MOLDTKPAC','Mold-Tek Packaging','Packaging'),('MPHASIS','Mphasis','IT'),
    ('MRPL','Mangalore Refinery','Energy'),('NATIONALUM','National Aluminium','Metals'),
    ('NAVINFLUOR','Navin Fluorine','Chemicals'),('NBCC','NBCC','Infrastructure'),
    ('NCC','NCC Ltd','Infrastructure'),('NESTLEIND','Nestle India','FMCG'),
    ('NFSL','Nippon Life AMC','Financial Services'),('NH','Narayana Hrudayalaya','Healthcare'),
    ('NIACL','New India Assurance','Insurance'),('NIITMTS','NIIT Learning Systems','IT'),
    ('NLCINDIA','NLC India','Power'),('NUVAMA','Nuvama Wealth Mgmt','Financial Services'),
    ('OBEROIRLTY','Oberoi Realty','Real Estate'),('OFSS','Oracle Financial','IT'),
    ('OIL','Oil India','Energy'),('OLECTRA','Olectra Greentech','Auto'),
    ('PERSISTENT','Persistent Systems','IT'),('PHOENIXLTD','Phoenix Mills','Retail'),
    ('PNBHOUSING','PNB Housing','NBFC'),('POLICYBZR','PB Fintech','IT'),
    ('PRAJIND','Praj Industries','Infrastructure'),('PRESTIGE','Prestige Estates','Real Estate'),
    ('PSB','Punjab & Sind Bank','Banking'),('QUESS','Quess Corp','IT'),
    ('RADICO','Radico Khaitan','FMCG'),('RAJESHEXPO','Rajesh Exports','Retail'),
    ('RATEGAIN','RateGain Travel','IT'),('RCF','RCF','Chemicals'),
    ('REDINGTON','Redington','IT'),('RELINFRA','Reliance Infra','Infrastructure'),
    ('REPCOHOME','Repco Home Finance','NBFC'),('RITES','RITES','Infrastructure'),
    ('ROSSARI','Rossari Biotech','Chemicals'),('RVNL','RVNL','Infrastructure'),
    ('SADBHAV','Sadbhav Engineering','Infrastructure'),('SASKEN','Sasken Technologies','IT'),
    ('SBICARD','SBI Cards','NBFC'),('SCHAEFFLER','Schaeffler India','Auto'),
    ('SEQUENT','Sequent Scientific','Pharma'),('SHARDAMOTR','Sharda Motor','Auto'),
    ('SHRIRAMFIN','Shriram Finance','NBFC'),('SJVN','SJVN','Power'),
    ('SKFINDIA','SKF India','Auto'),('SOBHA','Sobha Ltd','Real Estate'),
    ('SOLARINDS','Solar Industries','Chemicals'),('SONACOMS','Sona BLW','Auto'),
    ('SPICEJET','SpiceJet','Aviation'),('SRF','SRF Ltd','Chemicals'),
    ('STARHEALTH','Star Health','Insurance'),('STERLING','Sterling & Wilson','Infrastructure'),
    ('STLTECH','Sterlite Tech','Telecom'),('SUNPHARMA','Sun Pharma','Pharma'),
    ('SUPREMEIND','Supreme Industries','Infrastructure'),('SURYAROSNI','Surya Roshni','Infrastructure'),
    ('SUVEN','Suven Pharma','Pharma'),('SWANENERGY','Swan Energy','Energy'),
    ('SYMPHONY','Symphony Ltd','Consumer'),('TANLA','Tanla Platforms','IT'),
    ('TATACHEM','Tata Chemicals','Chemicals'),('TATAELXSI','Tata Elxsi','IT'),
    ('TATASTEEL','Tata Steel','Metals'),('TBZ','Tribhovandas Bhimji','Retail'),
    ('TCI','Transport Corp','Logistics'),('TCIEXP','TCI Express','Logistics'),
    ('TEJASNET','Tejas Networks','Telecom'),('TORNTPOWER','Torrent Power','Power'),
    ('TRIDENT','Trident','Textiles'),('TRITURBINE','Triveni Turbine','Capital Goods'),
    ('TTML','TTML','Telecom'),('TV18BRDCST','TV18 Broadcast','Media'),
    ('UCOBANK','UCO Bank','Banking'),('UNITDSPR','United Spirits','FMCG'),
    ('UNOMINDA','UNO Minda','Auto'),('UTIAMC','UTI AMC','Financial Services'),
    ('VBL','Varun Beverages','FMCG'),('VGUARD','V-Guard Industries','Consumer'),
    ('VINATIORGA','Vinati Organics','Chemicals'),('VIPIND','VIP Industries','Consumer'),
    ('VSTIND','VST Industries','FMCG'),('WELCORP','Welcorp','Metals'),
    ('YESBANK','Yes Bank','Banking'),('ZENSARTECH','Zensar Technologies','IT'),
    ('ZFCVINDIA','ZF Commercial','Auto'),('ZYDUSLIFE','Zydus Lifesciences','Pharma'),
    ('ZYDUSWELL','Zydus Wellness','FMCG'),('AFFLE','Affle India','IT'),
    ('ALKEM','Alkem Labs','Pharma'),('AMBER','Amber Enterprises','Consumer'),
    ('ANURAS','Anupam Rasayan','Chemicals'),('APOLLOTYRE','Apollo Tyres','Auto'),
    ('ASAHIINDIA','Asahi India Glass','Auto'),('ASHOKLEY','Ashok Leyland','Auto'),
    ('ASTRAZEN','AstraZeneca Pharma','Pharma'),('ATUL','Atul Ltd','Chemicals'),
    ('AURUM','Aurum PropTech','IT'),('BAJAJ-AUTO','Bajaj Auto','Auto'),
    ('BAJAJCHEM','Bajaj Chemicals','Chemicals'),('BAJAJCON','Bajaj Consumer','FMCG'),
    ('BALAMINES','BAL Pharma','Pharma'),('BALLARPUR','Ballarpur Industries','Paper'),
    ('BHARATFORG','Bharat Forge','Auto'),('BHEL','BHEL','Capital Goods'),
    ('BIGBLOC','Bigbloc Construction','Infrastructure'),('BLUEDART','Blue Dart Express','Logistics'),
    ('BNL','Bombay Dyeing','Textiles'),('BRIGADE','Brigade Enterprises','Real Estate'),
    ('BRITANNIA','Britannia Industries','FMCG'),('BROOKS','Brooks Laboratories','Pharma'),
    ('CADILAHC','Cadila Healthcare','Pharma'),('CAPACITE','Capacite Infra','Infrastructure'),
    ('CARERATING','CARE Ratings','Financial Services'),('CASTROL','Castrol India','Energy'),
    ('CCL','CCL Products','FMCG'),('CENTENKA','Century Enka','Textiles'),
    ('CENTRUM','Centrum Capital','Financial Services'),('CHALET','Chalet Hotels','Hospitality'),
    ('CHEMFAB','Chemfab Alkalis','Chemicals'),('CHENNPETRO','Chennai Petroleum','Energy'),
    ('CHOLA','Cholamandalam Inv','Financial Services'),('CLEAN','Clean Science','Chemicals'),
    ('COFFEEDAY','Coffee Day','FMCG'),('COROMANDEL','Coromandel International','Chemicals'),
    ('CRSL','CRSL','Financial'),('CYIENT','Cyient','IT'),
    ('DALBHARAT','Dalmia Bharat','Infrastructure'),('DCAL','Dishman Carbogen','Pharma'),
    ('DECCANCE','Deccan Cements','Infrastructure'),('DEEPAKFERT','Deepak Fertilisers','Chemicals'),
    ('DELTACORP','Delta Corp','Hospitality'),('DHANI','Dhani Services','Financial Services'),
    ('DIXON','Dixon Technologies','Consumer'),('DMART','Avenue Supermarts','Retail'),
    ('DTIL','DTIL','IT'),('EASEMYTRIP','Easy Trip Planners','IT'),
    ('ECLERX','Eclerx Services','IT'),('EDELWEISS','Edelweiss Financial','Financial Services'),
    ('EIHOTEL','EIH Hotels','Hospitality'),('ELECON','Elecon Engineering','Capital Goods'),
    ('EMCURE','Emcure Pharma','Pharma'),('ENGINERSIN','Engineers India','Infrastructure'),
    ('EQUITASBNK','Equitas Bank','Banking'),('FDC','FDC Ltd','Pharma'),
    ('FIEMIND','Fiem Industries','Auto'),('FIVESTAR','Five-Star Business','NBFC'),
    ('FOSE','Foseco India','Infrastructure'),('GALLANTT','Gallantt Ispat','Metals'),
    ('GANDHAR','Gandhar Oil','Energy'),('GARFIBRES','Garware Technical','Textiles'),
    ('GATEWAY','Gateway Distriparks','Logistics'),('GEECEE','GeeCee Ventures','Financial'),
    ('GESHIP','Great Eastern Shipping','Logistics'),('GHCL','GHCL','Chemicals'),
    ('GILLETTE','Gillette India','FMCG'),('GLAND','Gland Pharma','Pharma'),
    ('GMMPFAUDLR','GMM Pfaudler','Capital Goods'),('GODREJAGRO','Godrej Agrovet','FMCG'),
    ('GOODYEAR','Goodyear India','Auto'),('GPIL','Godawari Power','Metals'),
    ('GRANULES','Granules India','Pharma'),('GRAPHITE','Graphite India','Infrastructure'),
    ('GRINDWELL','Grindwell Norton','Infrastructure'),('GRSE','GRSE','Defence'),
    ('GULFOILLUB','Gulf Oil Lubricants','Energy'),('HAPPSTMNDS','Happiest Minds','IT'),
    ('HARSHA','Harsha Engineers','Capital Goods'),('HCL-INSYS','HCL Infosystems','IT'),
    ('HCLTECH','HCL Tech','IT'),('HEROMOTOCO','Hero MotoCorp','Auto'),
    ('HFCL','HFCL','Telecom'),('HGS','Hinduja Global','IT'),
    ('HIKAL','Hikal Ltd','Pharma'),('HIL','HIL Ltd','Infrastructure'),
    ('HINDCON','Hindcon Chemicals','Chemicals'),('ICICIBNK','ICICI Bank','Banking'),
    ('INDOSTAR','Indostar Capital','NBFC'),('INFIBEAM','Infibeam Avenues','IT'),
    ('INGERRAND','Ingersoll Rand','Capital Goods'),('INTELLECT','Intellect Design','IT'),
    ('IOLCP','IOL Chemicals','Chemicals'),('IPCALAB','Ipca Labs','Pharma'),
    ('IRFC','IRFC','NBFC'),('ISEC','ICICI Securities','Financial Services'),
    ('ITC','ITC','FMCG'),('J&KBANK','J&K Bank','Banking'),
    ('JAGRAN','Jagran Prakashan','Media'),('JAIBALAJI','Jai Balaji Industries','Metals'),
    ('JAL','JAL','Infrastructure'),('JBMA','JBMA Auto','Auto'),
    ('JINDALSAW','Jindal Saw','Metals'),('JKPAPER','JK Paper','Paper'),
    ('JKTYRE','JK Tyre','Auto'),('JMCPROJECT','JMC Projects','Infrastructure'),
    ('JMFINANCIL','JM Financial','Financial Services'),('JPPOWER','Jaiprakash Power','Power'),
    ('JSL','Jindal Stainless','Metals'),('JSWSTEEL','JSW Steel','Metals'),
    ('JUBLINDS','Jubilant Industries','Chemicals'),('JUBLPHARMA','Jubilant Pharma','Pharma'),
    ('KABRAEXTRU','Kabra Extrusion','Infrastructure'),('KAJARIACER','Kajaria Ceramics','Consumer'),
    ('KAKATCEM','Kakatiya Cement','Infrastructure'),('KALYANKJIL','Kalyan Jewellers','Retail'),
    ('KARURVYSYA','Karur Vysya Bank','Banking'),('KAUSHALYA','Kaushalya Infra','Infrastructure'),
    ('KDDL','KDDL Ltd','Consumer'),('KECL','Kirloskar Electric','Capital Goods'),
    ('KESORAMIND','Kesoram Industries','Infrastructure'),('KHAITAN','Khaitan Chemicals','Chemicals'),
    ('KIRLOSENG','Kirloskar Engines','Capital Goods'),('KKCL','KKCL Ltd','Textiles'),
    ('KMSUGAR','K M Sugar','FMCG'),('KNRCON','KNR Constructions','Infrastructure'),
    ('KOHINOOR','Kohinoor Foods','FMCG'),('KOKUYOCMLN','Kokuyo Camlin','Consumer'),
    ('KOTAKBANK','Kotak Mahindra Bank','Banking'),('KOTARISUG','Kothari Sugars','FMCG'),
    ('KOTHARIPET','Kothari Petrochem','Chemicals'),('KOVAI','Kovai Medical','Healthcare'),
    ('KPIGREEN','KPI Green Energy','Energy'),('KSCL','Kaveri Seed','FMCG'),
    ('KSL','KSL Industries','Infrastructure'),('KTKBANK','Karnataka Bank','Banking'),
    ('KUANTUM','Kuantum Papers','Paper'),('L&TFH','L&T Finance','NBFC'),
    ('LAKPRE','Lakshmi Precision','Auto'),('LAMBODHARA','Lambodhara Textiles','Textiles'),
    ('LANCORHOL','Lancor Holdings','Real Estate'),('LAOPALA','La Opala RG','Consumer'),
    ('LATENTVIEW','Latent View Analytics','IT'),('LAURUSLABS','Laurus Labs','Pharma'),
    ('LAXMI','Laxmi Organic','Chemicals'),('LCCINFOTEC','LCC Infotech','IT'),
    ('LEEL','Leela Hotels','Hospitality'),('LEMONTREE','Lemon Tree Hotels','Hospitality'),
    ('LEXUS','Lexus Granito','Infrastructure'),('LFIC','LFIC','Financial'),
    ('LIBAS','Libas Designs','Retail'),('LIBERTSHOE','Liberty Shoes','Retail'),
    ('LICHSGFIN','LIC Housing Finance','NBFC'),('LIKHITHA','Likhitha Infra','Infrastructure'),
    ('LINC','Linc Pen & Plastics','Consumer'),('LINCOLN','Lincoln Pharma','Pharma'),
    ('LINDEINDIA','Linde India','Chemicals'),('LODHA','Macrotech Developers','Real Estate'),
    ('LOKESHMACH','Lokesh Machines','Capital Goods'),('LOTUSEYE','Lotus Eye Hospital','Healthcare'),
    ('LOVABLE','Lovable Lingerie','Retail'),('LOYALTEX','Loyal Textiles','Textiles'),
    ('LPDC','LPDC','Infrastructure'),('LSIL','Lloyds Steels','Metals'),
    ('LTTS','L&T Technology Services','IT'),('LUPIN','Lupin','Pharma'),
    ('LUMAXIND','Lumax Industries','Auto'),('LUMAXTECH','Lumax Auto Tech','Auto'),
    ('M&M','M&M','Auto'),('MAANALU','Maan Aluminium','Metals'),
    ('MACHINO','Machino Plastics','Auto'),('MADHUCON','Madhucon Projects','Infrastructure'),
    ('MADRASFERT','Madras Fertilizers','Chemicals'),('MAGADSUGAR','Magadh Sugar','FMCG'),
    ('MAGMA','Magma Fincorp','NBFC'),('MAHABANK','Bank of Maharashtra','Banking'),
    ('MAHESHWARI','Maheshwari Logistics','Logistics'),('MAHLIFE','Mahindra Lifespace','Real Estate'),
    ('MAHLOG','Mahindra Logistics','Logistics'),('MAHSCOOTER','Maharashtra Scooters','Auto'),
    ('MAITHANALL','Maithan Alloys','Metals'),('MALLCOM','Mallcom India','Consumer'),
    ('MALUPAPER','Malu Paper Mills','Paper'),('MANAKSIA','Manaksia','Metals'),
    ('MANALIPETC','Manali Petrochemicals','Chemicals'),('MANAPPURAM','Manappuram Finance','NBFC'),
    ('MANDHANA','Mandhana Retail','Retail'),('MANGCHEFER','Mangalore Chemicals','Chemicals'),
    ('MANGLMCEM','Mangalam Cement','Infrastructure'),('MANINDS','Man Industries','Infrastructure'),
    ('MANINFRA','Man Infra','Infrastructure'),('MANKIND','Mankind Pharma','Pharma'),
    ('MANOMAY','Manomay Tex India','Textiles'),('MANORAMA','Manorama Industries','FMCG'),
    ('MARALOVER','Maral Overseas','Textiles'),('MARATHON','Marathon Nextgen','Real Estate'),
    ('MARICO','Marico','FMCG'),('MARKSANS','Marksans Pharma','Pharma'),
    ('MASTEK','Mastek','IT'),('MATHERPLAT','Mather & Platt','Capital Goods'),
    ('MATRIMONY','Matrimony.com','IT'),('MAWANA','Mawana Sugars','FMCG'),
    ('MAXHEALTH','Max Healthcare','Healthcare'),('MAYURUNIQ','Mayur Uniquoters','Textiles'),
    ('MAZDA','Mazda Ltd','Auto'),('MCLEODRUSS','McLeod Russel','FMCG'),
    ('MCNALLY','McNally Bharat','Infrastructure'),('MEGASOFT','Megasoft','IT'),
    ('MELSTAR','Melstar Infotech','IT'),('MENONBEAR','Menon Bearings','Auto'),
    ('MEP','MEP Infrastructure','Infrastructure'),('MERCATOR','Mercator','Logistics'),
    ('MERCURY','Mercury Metals','Metals'),('METALFORGE','Metal Forge','Auto'),
    ('METKORE','Metkore Alloys','Metals'),('MFSL','Max Financial','Insurance'),
    ('MGL','Mahanagar Gas','Energy'),('MHRIL','Mahindra Holidays','Hospitality'),
    ('MICEL','MIC Electronics','IT'),('MICHISO','Michaelsons','IT'),
    ('MICROPRO','Micropro Software','IT'),('MIDHANI','Mishra Dhatu','Metals'),
    ('MILKFOOD','Milkfood','FMCG'),('MINDACORP','Minda Corp','Auto'),
    ('MINDAIND','Minda Industries','Auto'),('MINDTECK','Mindteck','IT'),
    ('MIRCELECTR','MIRC Electronics','Consumer'),('MIRZAINT','Mirza International','Textiles'),
    ('MITTAL','Mittal Life Style','Textiles'),('MMFL','MM Forgings','Auto'),
    ('MMP','MMP Industries','Infrastructure'),('MOHOTAIND','Mohota Industries','Textiles'),
    ('MOIL','MOIL','Metals'),('MOKSH','Moksh Ornaments','Retail'),
    ('MOLDTKPAC','Mold-Tek Packaging','Packaging'),('MONARCH','Monarch Networth','Financial Services'),
    ('MONTECARLO','Monte Carlo Fashions','Retail'),('MORARJEE','Morarjee Textiles','Textiles'),
    ('MOREPENLAB','Morepen Labs','Pharma'),('MORGAN','Morgan Ventures','Financial Services'),
    ('MOTHERSON','Motherson Sumi','Auto'),('MOTILALOFS','Motilal Oswal','Financial Services'),
    ('MOTHERSUMI','Motherson Sumi','Auto'),('MOUNTAIN','Mountain Energy','Energy'),
    ('MPHASIS','Mphasis','IT'),('MRF','MRF','Auto'),
    ('MRO','MRO-TEK Realty','IT'),('MSPL','MSP Steel','Metals'),
    ('MTARTECH','MTAR Technologies','Capital Goods'),('MTNL','MTNL','Telecom'),
    ('MUKANDLTD','Mukand','Metals'),('MUKTAARTS','Mukta Arts','Media'),
    ('MUNJALAU','Munjal Auto','Auto'),('MUNJALSHOW','Munjal Showa','Auto'),
    ('MURUDCERA','Murudeshwar Ceramics','Consumer'),('MUTHOOTFIN','Muthoot Finance','NBFC'),
    ('MUTHOOTMF','Muthoot Microfin','NBFC'),('MVG','MVG','Textiles'),
    ('NAGAFERT','Nagarjuna Fertilizers','Chemicals'),('NAGREEKCAP','Nagreeka Capital','Financial Services'),
    ('NAHARINDUS','Nahar Industrial','Textiles'),('NAHARPOLY','Nahar Poly','Textiles'),
    ('NAHARSPING','Nahar Spinning','Textiles'),('NAM-INDIA','Nippon Life AMC','Financial Services'),
    ('NARMADA','Narmada Agrobase','FMCG'),('NATCOPHARM','Natco Pharma','Pharma'),
    ('NAUKRI','Info Edge','IT'),('NAVINFLUOR','Navin Fluorine','Chemicals'),
    ('NAVKARCORP','Navkar Corporation','Logistics'),('NAVNETEDUL','Navneet Education','Media'),
    ('NBCC','NBCC','Infrastructure'),('NBFOOT','NB Footwear','Retail'),
    ('NCC','NCC','Infrastructure'),('NCLIND','NCL Industries','Infrastructure'),
    ('NDGL','Naga Dhunseri','FMCG'),('NDL','Nandan Denim','Textiles'),
    ('NDTV','NDTV','Media'),('NECLIFE','Neclife','Pharma'),
    ('NELCAST','Nelcast','Auto'),('NELCO','Nelco','Telecom'),
    ('NEOGEN','Neogen Chemicals','Chemicals'),('NESCO','Nesco','Consumer'),
    ('NESTLEIND','Nestle India','FMCG'),('NETWORK18','Network18','Media'),
    ('NEULANDLAB','Neuland Labs','Pharma'),('NEWGEN','Newgen Software','IT'),
    ('NEXTMEDIA','Next Mediaworks','Media'),('NFL','National Fertilizers','Chemicals'),
    ('NHPC','NHPC','Power'),('NIACL','New India Assurance','Insurance'),
    ('NIBL','NIBL','Financial'),('NIDAN','Nidan Labs','Healthcare'),
    ('NIFTYBEES','Nifty Bees','Financial'),('NIPPOBATRY','Nippo Batteries','Auto'),
    ('NITINSPIN','Nitin Spinners','Textiles'),('NLCINDIA','NLC India','Power'),
    ('NMDC','NMDC','Metals'),('NOCIL','Nocil','Chemicals'),
    ('NOIDATN','Noida Toll Bridge','Infrastructure'),('NORBTEA','Norben Tea','FMCG'),
    ('NOVARTIND','Novartis India','Pharma'),('NPBET','NPBET','Financial'),
    ('NPST','NPST','IT'),('NRAIL','NR Agarwal','Infrastructure'),
    ('NRBBEARING','NRB Bearings','Auto'),('NSIL','Nalco','Metals'),
    ('NTPC','NTPC','Power'),('NUCLEUS','Nucleus Software','IT'),
    ('NURECA','Nureca','Consumer'),('NUVAMA','Nuvama Wealth','Financial Services'),
    ('NUVOCO','Nuvoco Vistas','Infrastructure'),('NXTDIGITAL','Nxtdigital','Media'),
    ('NYTAA','Nykaa FSN','Retail'),('OAL','Oriental Aromatics','Chemicals'),
    ('OBC','Oriental Bank','Banking'),('OBEROIRLTY','Oberoi Realty','Real Estate'),
    ('OCCL','Oriental Carbon','Chemicals'),('OFSS','Oracle Financial','IT'),
    ('OIL','Oil India','Energy'),('OILCOUNTUB','Oil Country Tubular','Energy'),
    ('OLECTRA','Olectra Greentech','Auto'),('OMAXAUTO','Omax Auto','Auto'),
    ('OMAXE','Omaxe','Real Estate'),('OMKARCHEM','Omkar Chemicals','Chemicals'),
    ('ONGC','ONGC','Energy'),('ONMOBILE','OnMobile','Telecom'),
    ('ONWARDTEC','Onward Technologies','IT'),('OPTIEMUS','Optiemus Infra','Telecom'),
    ('ORBTEXP','Orbit Exports','Textiles'),('ORIENTALTL','Oriental Trimex','Infrastructure'),
    ('ORIENTBELL','Orient Bell','Consumer'),('ORIENTCEM','Orient Cement','Infrastructure'),
    ('ORIENTELEC','Orient Electric','Consumer'),('ORIENTHOT','Oriental Hotels','Hospitality'),
    ('ORIENTLTD','Orient Press','Packaging'),('ORIENTPPR','Orient Paper','Paper'),
    ('ORISSAMINE','Orissa Minerals','Metals'),('ORTEL','Ortel Comm','Telecom'),
    ('OSWALAGRO','Oswal Agro','FMCG'),('OSWALYARN','Oswal Yarns','Textiles'),
    ('PAGEIND','Page Industries','Textiles'),('PAISALO','Paisalo Digital','NBFC'),
    ('PALASHSEC','Palash Securities','Financial'),('PALREDTEC','Palred Technologies','IT'),
    ('PANACEABIO','Panacea Biotec','Pharma'),('PANAMAPET','Panama Petrochem','Chemicals'),
    ('PARACABLES','Paramount Cable','Infrastructure'),('PARADEEP','Paradeep Phosphates','Chemicals'),
    ('PARAGMILK','Parag Milk Foods','FMCG'),('PARKHOTELS','Park Hotels','Hospitality'),
    ('PARSVNATH','Parsvnath Developers','Real Estate'),('PASUPTAC','Pasupati Acrylon','Textiles'),
    ('PATELENG','Patel Engineering','Infrastructure'),('PATINTLOG','Patel Integrated','Logistics'),
    ('PAYTM','One97 Comm','IT'),('PCBL','PCBL','Chemicals'),
    ('PCJEWELLER','PC Jeweller','Retail'),('PDMJEPAPER','PDM Paper','Paper'),
    ('PDSL','PDSL','IT'),('PEARLPOLY','Pearl Polymers','Consumer'),
    ('PEL','Piramal Enterprises','Pharma'),('PENIND','Peninsula Land','Real Estate'),
    ('PENINLAND','Peninsular Land','Real Estate'),('PENUMAN','Penumudy Pharma','Pharma'),
    ('PERFECT','Perfect Infra','Infrastructure'),('PERSISTENT','Persistent Systems','IT'),
    ('PETRONET','Petronet LNG','Energy'),('PFC','Power Finance','NBFC'),
    ('PFIZER','Pfizer India','Pharma'),('PGEL','PG Electroplast','Consumer'),
    ('PGHH','Procter & Gamble','FMCG'),('PGIL','Pearl Global','Textiles'),
    ('PHANTOMFX','Phantom Digital','IT'),('PHILIPCARB','Philips Carbon','Chemicals'),
    ('PHOENIXLTD','Phoenix Mills','Retail'),('PIDILITIND','Pidilite Industries','Chemicals'),
    ('PIIND','PI Industries','Chemicals'),('PILANIINVS','Pilani Investments','Financial'),
    ('PILITA','Pil Italica','FMCG'),('PIONEEREMB','Pioneer Embroideries','Textiles'),
    ('PITTIENG','Pitti Engineering','Capital Goods'),('PIXTRANS','Pix Transmissions','Auto'),
    ('PLASTIBLEN','Plastiblends','Chemicals'),('PLATIND','Platinum Industries','Chemicals'),
    ('PLAZA','Plaza Wires','Infrastructure'),('PNB','PNB','Banking'),
    ('PNBGILTS','PNB Gilts','Financial Services'),('PNBHOUSING','PNB Housing','NBFC'),
    ('PODDARHOUS','Poddar Housing','Real Estate'),('PODDARMENT','Poddar Pigments','Chemicals'),
    ('POKARNA','Pokarna','Infrastructure'),('POLICYBZR','PB Fintech','IT'),
    ('POLYPLEX','Polyplex','Packaging'),('POLYSPIN','Polyspin','Textiles'),
    ('POONAWALLA','Poonawalla Fincorp','NBFC'),('POWERGRID','Power Grid','Power'),
    ('POWERMECH','Power Mech Projects','Infrastructure'),('PPAP','PPAP Automotive','Auto'),
    ('PRABHAT','Prabhat Dairy','FMCG'),('PRAENG','Prajay Engineers','Infrastructure'),
    ('PRAJIND','Praj Industries','Infrastructure'),('PRAKASH','Prakash Industries','Metals'),
    ('PRAKASHSTL','Prakash Steel','Metals'),('PRECAM','Precision Camshafts','Auto'),
    ('PRECOT','Precot Meridian','Textiles'),('PRECWIRE','Precision Wires','Infrastructure'),
    ('PREMEXPLN','Premier Explosives','Chemicals'),('PREMIERPOL','Premier Polyfilm','Packaging'),
    ('PRESTIGE','Prestige Estates','Real Estate'),('PRICOLLTD','Pricol','Auto'),
    ('PRIMESECU','Prime Securities','Financial Services'),('PRINCEPIPE','Prince Pipes','Infrastructure'),
    ('PRITI','Priti Auto','Auto'),('PRIVISCL','Privis Clinic','Healthcare'),
    ('PROTEAN','Protean eGov','IT'),('PROVENCE','Provence Realty','Real Estate'),
    ('PRSMJOHNSN','Prism Johnson','Infrastructure'),('PSB','PSB','Banking'),
    ('PSPPROJECT','PSP Projects','Infrastructure'),('PTC','PTC India','Power'),
    ('PTCIL','PTC Industries','Capital Goods'),('PTL','PTL Enterprises','Healthcare'),
    ('PUNJABCHEM','Punjab Chemicals','Chemicals'),('PURVA','Purvankara','Real Estate'),
    ('PVRINOX','PVR INOX','Media'),('PYRAMID','Pyramid Technoplast','Packaging'),
    ('QUADRANT','Quadrant Televentures','Telecom'),('QUESS','Quess Corp','IT'),
    ('QUICKHEAL','Quick Heal Tech','IT'),('RADAAN','Radaan Mediaworks','Media'),
    ('RADHIKA','Radhika Jeweltech','Retail'),('RADICO','Radico Khaitan','FMCG'),
    ('RADIOCITY','Music Broadcast','Media'),('RAILTEL','RailTel Corp','Telecom'),
    ('RAIN','Rain Industries','Chemicals'),('RAJESHEXPO','Rajesh Exports','Retail'),
    ('RAJRATAN','Rajratan Global Wire','Auto'),('RAJSREESUG','Rajshree Sugars','FMCG'),
    ('RAJTV','Raj TV','Media'),('RALLIS','Rallis India','Chemicals'),
    ('RAMANEWS','Rama Newsprint','Paper'),('RAMASTEEL','Rama Steel','Metals'),
    ('RAMCOCEM','Ramco Cements','Infrastructure'),('RAMCOIND','Ramco Industries','Infrastructure'),
    ('RAMCOSYS','Ramco Systems','IT'),('RAMKY','Ramky Infra','Infrastructure'),
    ('RAMSARUP','Ramsarup Industries','Metals'),('RANASUG','Rana Sugars','FMCG'),
    ('RANEENGINE','Rane Engine','Auto'),('RANEHOLDIN','Rane Holdings','Auto'),
    ('RATEGAIN','RateGain Travel','IT'),('RATNAMANI','Ratnamani Metals','Metals'),
    ('RAYMOND','Raymond','Textiles'),('RBL','RBL','Retail'),
    ('RBLBANK','RBL Bank','Banking'),('RCF','RCF','Chemicals'),
    ('RECLTD','REC','NBFC'),('REDINGTON','Redington','IT'),
    ('REFEX','Refex Industries','Energy'),('REGENCERAM','Regency Ceramics','Consumer'),
    ('RELCAPITAL','Reliance Capital','NBFC'),('RELCHEMQ','Reliance Chemotex','Textiles'),
    ('RELAXO','Relaxo Footwear','Retail'),('RELINFRA','Reliance Infra','Infrastructure'),
    ('REMSONSIND','Remsons Industries','Auto'),('RENUKA','Shree Renuka','FMCG'),
    ('REPRO','Repro India','Media'),('RESPONIND','Responsive Ind','Textiles'),
    ('RETAIL','Retail','Retail'),('REVATHI','Revathi Equipment','Capital Goods'),
    ('RGL','RGL Reserve','Financial'),('RHIM','RHI Magnesita','Infrastructure'),
    ('RICOAUTO','Rico Auto','Auto'),('RIIL','Reliance Indl Infra','Infrastructure'),
    ('RITES','RITES','Infrastructure'),('RKDL','Ravi Kumar Dist','FMCG'),
    ('RKEC','RKEC Projects','Infrastructure'),('RKFORGE','Ramkrishna Forgings','Auto'),
    ('RML','RML','Healthcare'),('RNAVAL','Reliance Naval','Logistics'),
    ('ROBL','Roberts & Lombard','Financial'),('ROHLTD','Royal Orchid Hotels','Hospitality'),
    ('ROLTA','Rolta India','IT'),('ROSSARI','Rossari Biotech','Chemicals'),
    ('ROUTE','Route Mobile','IT'),('RPGLIFE','RPG Life Sciences','Pharma'),
    ('RPPINFRA','RPP Infra','Infrastructure'),('RPPL','RPPL','Retail'),
    ('RSSOFTWARE','R S Software','IT'),('RSWM','RSWM','Textiles'),
    ('RSYSTEMS','R Systems','IT'),('RTNINFRA','RTN Infra','Infrastructure'),
    ('RUBFILA','Rubfila International','Chemicals'),('RUCHI','Ruchi Soya','FMCG'),
    ('RUCHIRA','Ruchira Papers','Paper'),('RUPA','Rupa Company','Retail'),
    ('RUSHIL','Rushil Decor','Infrastructure'),('RVNL','RVNL','Infrastructure'),
    ('S&SPOWER','S&S Power','Energy'),('SABEVENTS','Sab Events','Media'),
    ('SABOOBHAI','Saboo Sodium','FMCG'),('SACHEMT','Sacheta Metals','Metals'),
    ('SADBHIN','Sadbhav Infra','Infrastructure'),('SADBHAV','Sadbhav Engg','Infrastructure'),
    ('SAFARI','Safari Industries','Consumer'),('SAGARDEEP','Sagar Deep','FMCG'),
    ('SAGCEM','Sagar Cement','Infrastructure'),('SAHARA','Sahara Housing','Real Estate'),
    ('SAHASRA','Sahasra Electronics','IT'),('SAHJAINFOR','Sahaj Fashions','Retail'),
    ('SALASAR','Salasar Techno','Infrastructure'),('SALONA','Salona Cotspin','Textiles'),
    ('SALSTEEL','Sal Steel','Metals'),('SALZER','Salzer Electronics','Consumer'),
    ('SAMBANDAM','Sambandam Spinning','Textiles'),('SAMBHAAV','Sambhaav Media','Media'),
    ('SAMHI','Samhi Hotels','Hospitality'),('SAMRATFORG','Samrat Forgings','Auto'),
    ('SANDESH','Sandesh','Media'),('SANDHAR','Sandhar Tech','Auto'),
    ('SANGAMIND','Sangam India','Textiles'),('SANGHIIND','Sanghi Industries','Infrastructure'),
    ('SANGHVIMOV','Sanghvi Movers','Infrastructure'),('SANJIVIN','Sanjivani Paranteral','Pharma'),
    ('SANKHYA','Sankhya Infotech','IT'),('SANOFI','Sanofi India','Pharma'),
    ('SANSERA','Sansera Engineering','Auto'),('SAPPHIRE','Sapphire Foods','FMCG'),
    ('SARDAEN','Sarda Energy','Metals'),('SAREGAMA','Saregama India','Media'),
    ('SARLAPOLY','Sarla Performance','Textiles'),('SARTHAK','Sarthak Metals','Metals'),
    ('SASKEN','Sasken Technologies','IT'),('SATIA','Satia Industries','Paper'),
    ('SAURASHCEM','Saurashtra Cement','Infrastructure'),('SAWABUSI','Sawaca Business','Financial Services'),
    ('SBICARD','SBI Cards','NBFC'),('SBILIFE','SBI Life','Insurance'),
    ('SBI','SBI','Banking'),('SBL','SBL','Insurance'),
    ('SCAP','SCAP','Packaging'),('SCHAEFFLER','Schaeffler India','Auto'),
    ('SCHAND','S Chand Publishers','Media'),('SCHNEIDER','Schneider Electric','Capital Goods'),
    ('SCI','Shipping Corp','Logistics'),('SCILAL','SCILAL','IT'),
    ('SEAMECLTD','Seamec','Logistics'),('SECUN','Secure Notes','IT'),
    ('SECURKLOUD','SecureKloud','IT'),('SEJALLTD','Sejal Glass','Consumer'),
    ('SELAN','Selan Exploration','Energy'),('SELLWIN','Sellwin Industries','Financial'),
    ('SEMAC','Semac Consultants','Infrastructure'),('SENGOA','SEN Gold','Retail'),
    ('SENORES','SEN Resources','Financial'),('SEPC','SEPC','Infrastructure'),
    ('SEQUENT','Sequent Scientific','Pharma'),('SERVOTECH','Servotech Power','Energy'),
    ('SESHAPAPER','Seshasayee Paper','Paper'),('SETCO','Setco Automotive','Auto'),
    ('SETUINFRA','Setu Infrastructure','Infrastructure'),('SEYA','Seya Industries','Chemicals'),
    ('SFL','Sheela Foam','Consumer'),('SGJL','SGJL','Financial'),
    ('SGL','SGL','Textiles'),('SHAHALLOYS','Shah Alloys','Metals'),
    ('SHAILY','Shaily Engineering','Chemicals'),('SHAKTIPUMP','Shakti Pumps','Capital Goods'),
    ('SHALBY','Shalby Hospitals','Healthcare'),('SHALPAINTS','Shalimar Paints','Consumer'),
    ('SHANKARA','Shankara Building','Retail'),('SHANTI','Shanti Spintex','Textiles'),
    ('SHANTIGEAR','Shanti Gears','Auto'),('SHARDACROP','Sharda Cropchem','Chemicals'),
    ('SHARDAMOTR','Sharda Motor','Auto'),('SHAREINDIA','Share India','Financial Services'),
    ('SHEMAROO','Shemaroo Entertainment','Media'),('SHILPAMED','Shilpa Medicare','Pharma'),
    ('SHIVALIK','Shivalik Bimetal','Auto'),('SHIVAMILLS','Shiva Mills','Textiles'),
    ('SHIVATEX','Shiva Texyarn','Textiles'),('SHK','S H K','FMCG'),
    ('SHOPERSTOP','Shoppers Stop','Retail'),('SHRADHA','Shradha Infra','Infrastructure'),
    ('SHREEOSFM','Shree OSFM','Logistics'),('SHRENIK','Shrenik','Textiles'),
    ('SHREYANIND','Shreyans Industries','Paper'),('SHREYAS','Shreyas Shipping','Logistics'),
    ('SHRIRAMFIN','Shriram Finance','NBFC'),('SHRIRAMPPS','Shriram Properties','Real Estate'),
    ('SHYAMCENT','Shyam Century','Metals'),('SHYAMMETL','Shyam Metalics','Metals'),
    ('SICAL','Sical Logistics','Logistics'),('SIDDHA','Siddha Ventures','Financial'),
    ('SIDDHIKA','Siddhika Coatings','Chemicals'),('SIEMENS','Siemens India','Capital Goods'),
    ('SIGMA','Sigma Solve','IT'),('SIGNATURE','Signature Global','Real Estate'),
    ('SIGNETIN','Signet Industries','Infrastructure'),('SIKKO','Sikko Industries','FMCG'),
    ('SIL','Standard Industries','Textiles'),('SILGO','Silgo Retail','Retail'),
    ('SILINV','Sil Investments','Financial'),('SILLYMONKS','Silly Monks','Media'),
    ('SILVERTUC','Silver Touch','IT'),('SIMBHALS','SimBha Solvents','FMCG'),
    ('SIMPLEXINF','Simplex Infra','Infrastructure'),('SINDHUBAD','Sindhu Trade','Logistics'),
    ('SINTERCOM','Sintercom India','Auto'),('SIRCA','Sirca Paints','Consumer'),
    ('SIS','SIS','IT'),('SITINET','Siti Networks','Media'),
    ('SJVN','SJVN','Power'),('SKFINDIA','SKF India','Auto'),
    ('SKIPPER','Skipper','Infrastructure'),('SKMEGGPROD','SKM Egg Products','FMCG'),
    ('SKP','SKP Securities','Financial Services'),('SKSTEXTILE','SKS Textiles','Textiles'),
    ('SMARTLINK','Smartlink Holdings','IT'),('SMCGLOBAL','SMC Global','Financial Services'),
    ('SMLISUZU','SML Isuzu','Auto'),('SMPL','SMPL','Textiles'),
    ('SMSLIFE','SMS Lifesciences','Pharma'),('SMSPHARMA','SMS Pharma','Pharma'),
    ('SNOWMAN','Snowman Logistics','Logistics'),('SOBHA','Sobha','Real Estate'),
    ('SOFCOM','Sofcom Systems','IT'),('SOFTTECH','SoftTech Engineers','IT'),
    ('SOLARA','Solara Active','Pharma'),('SOLARINDS','Solar Industries','Chemicals'),
    ('SOMANYCERA','Somany Ceramics','Consumer'),('SONACOMS','Sona BLW','Auto'),
    ('SONAMCLOCK','Sonam Clock','Consumer'),('SONATSOFTW','Sonata Software','IT'),
    ('SONUINFRA','Sonu Infratech','Infrastructure'),('SORILINFRA','SORIL Infra','Real Estate'),
    ('SOTL','SOTL','Pharma'),('SOUTHBANK','South Indian Bank','Banking'),
    ('SOUTHWEST','South West Pinnacle','Infrastructure'),('SPAL','SPAL','Auto'),
    ('SPANDANA','Spandana Sphoorty','NBFC'),('SPARC','SPARC','Pharma'),
    ('SPECIALITY','Speciality Restaurants','Hospitality'),('SPENCERS','Spencers Retail','Retail'),
    ('SPIC','SPIC','Chemicals'),('SPICEJET','SpiceJet','Aviation'),
    ('SPLIL','SPL Industries','Textiles'),('SPLPETRO','SPL Petrochem','Chemicals'),
    ('SPORTKING','Sportking India','Textiles'),('SPRL','SPRL','Financial'),
    ('SPTL','SPTL','Packaging'),('SREEL','Sreeleathers','Retail'),
    ('SRF','SRF','Chemicals'),('SRHHYPOLTD','SHR Housing','Real Estate'),
    ('SRIPIPES','SRIPIPES','Infrastructure'),('SRIRAM','Sriram Finance','NBFC'),
    ('SRPL','SRPL','Retail'),('SSINFRA','SS Infra','Infrastructure'),
    ('SSPDL','SSPDL','Textiles'),('SSWL','SSWL','Auto'),
    ('STAMPEDE','Stampede Capital','Financial Services'),('STAR','Starlite Components','Auto'),
    ('STARCEMENT','Star Cement','Infrastructure'),('STARHEALTH','Star Health','Insurance'),
    ('STARPAPER','Star Paper','Paper'),('STARTECK','Starteck Finance','NBFC'),
    ('STCINDIA','STC India','Logistics'),('STEELCITY','Steel City Securities','Financial Services'),
    ('STEELXIND','SteelX India','IT'),('STEL','Stel Holdings','Consumer'),
    ('STERLING','Sterling & Wilson','Infrastructure'),('STERTOOLS','Sterling Tools','Auto'),
    ('STLTECH','Sterlite Tech','Telecom'),('STOVEKRAFT','Stove Kraft','Consumer'),
    ('STRENGTH','Strength International','Financial'),('STRIDES','Strides Pharma','Pharma'),
    ('STYLAMIND','Stylam Industries','Infrastructure'),('STYRENIX','Styrenix Chemicals','Chemicals'),
    ('SUBEXLTD','Subex','IT'),('SUBROS','Subros','Auto'),
    ('SUDARSHAN','Sudarshan Chemicals','Chemicals'),('SUKHJITS','Sukhjit Starch','FMCG'),
    ('SULDER','Sulder Engineering','Infrastructure'),('SUNCLAYLTD','Sunclay','Infrastructure'),
    ('SUNDARAM','Sundaram Finance','NBFC'),('SUNDARMHLD','Sundaram Holdings','Financial Services'),
    ('SUNDRMBRAK','Sundaram Brake','Auto'),('SUNDRMFAST','Sundram Fasteners','Auto'),
    ('SUNFLAG','Sunflag Iron','Metals'),('SUNPHARMA','Sun Pharma','Pharma'),
    ('SUNTECK','Sunteck Realty','Real Estate'),('SUNTV','Sun TV','Media'),
    ('SUPERHOUSE','Superhouse','Textiles'),('SUPERSPIN','Super Spintex','Textiles'),
    ('SUPRAJIT','Suprajit Engineering','Auto'),('SUPREMEIND','Supreme Industries','Infrastructure'),
    ('SUPREMEINF','Supreme Infra','Infrastructure'),('SURAJEST','Suraj Estates','Real Estate'),
    ('SURANASOL','Surana Solar','Energy'),('SURANAT&P','Surana Telcom','Telecom'),
    ('SURYALAXMI','Suryalakshmi','Textiles'),('SURYAROSNI','Surya Roshni','Infrastructure'),
    ('SURYODAY','Suryoday Bank','Banking'),('SUTLEJTEX','Sutlej Textiles','Textiles'),
    ('SUVEN','Suven Pharma','Pharma'),('SUVIDHAA','Suvidhaa Infoserve','IT'),
    ('SUVPHARMA','SUV Pharma','Pharma'),('SWANDEF','Swan Defence','Defence'),
    ('SWANENERGY','Swan Energy','Energy'),('SWARAJENG','Swaraj Engines','Auto'),
    ('SWELECTES','Swelect Energy','Energy'),('SYMPHONY','Symphony','Consumer'),
    ('SYNCOM','Syncom Healthcare','Healthcare'),('SYNGENE','Syngene','Pharma'),
    ('SYRMA','Syrma SGS','IT'),('TAJGVK','Taj GVK Hotels','Hospitality'),
    ('TAKE','Take Solutions','IT'),('TALBROAUTO','Talbro Automotive','Auto'),
    ('TALWALKARS','Talwalkars','Consumer'),('TALWGYM','Talwalkars Gym','Consumer'),
    ('TAMILNADU','Tamilnad Mercantile','Banking'),('TANAA','Tanaa','IT'),
    ('TANLA','Tanla Platforms','IT'),('TANTI','Tanti Industries','Textiles'),
    ('TARACHAND','Tara Chand Logistic','Logistics'),('TARAPUR','Tarapur Transformers','Capital Goods'),
    ('TARC','TARC','Real Estate'),('TARMAT','Tarmat','Infrastructure'),
    ('TASTYBIT','Tasty Bite','FMCG'),('TATACHEM','Tata Chemicals','Chemicals'),
    ('TATACOFFEE','Tata Coffee','FMCG'),('TATACOMM','Tata Comm','Telecom'),
    ('TATAELXSI','Tata Elxsi','IT'),('TATAINVEST','Tata Investment','Financial Services'),
    ('TATAMOTORS','Tata Motors','Auto'),('TATAMTRDVR','Tata Motors DVR','Auto'),
    ('TATAPOWER','Tata Power','Power'),('TATASTEEL','Tata Steel','Metals'),
    ('TATVA','Tatva Chintan','Chemicals'),('TBZ','TBZ','Retail'),
    ('TCI','Transport Corp','Logistics'),('TCIEXP','TCI Express','Logistics'),
    ('TCIFINANCE','TCI Finance','Financial'),('TCIIND','TCI Industries','Financial'),
    ('TDPOWERSYS','TD Power Systems','Capital Goods'),('TEAMLEASE','Teamlease Services','IT'),
    ('TECILCHEM','TECIL Chemicals','Chemicals'),('TECHM','Tech Mahindra','IT'),
    ('TECHNOFAB','Technofab Engg','Infrastructure'),('TEJASNET','Tejas Networks','Telecom'),
    ('TELECOM','Telecom','Telecom'),('TEMBO','Tembo Global','Infrastructure'),
    ('TEXCARD','Texcard','IT'),('TEXMOPIPES','Texmo Pipes','Infrastructure'),
    ('TEXRAIL','Texmaco Rail','Capital Goods'),('TFCILTD','TFCI','NBFC'),
    ('TGBHOTELS','TGB Banquets','Hospitality'),('THANGAMAYL','Thangamayil Jewellery','Retail'),
    ('THEINVEST','The Investment Trust','Financial'),('THEMISMED','Themis Medicare','Pharma'),
    ('THERMAX','Thermax','Capital Goods'),('THOMASCOOK','Thomas Cook','Hospitality'),
    ('THYROCARE','Thyrocare Tech','Healthcare'),('TIINDIA','Tube Investments','Auto'),
    ('TIDEWATER','Tide Water Oil','Energy'),('TIIC','TIIC','Financial'),
    ('TIL','TIL','Infrastructure'),('TIMESGTY','Times Guaranty','Financial'),
    ('TIMETECHNO','Time Technoplast','Packaging'),('TIMKEN','Timken India','Auto'),
    ('TINPLATE','Tinplate Company','Metals'),('TIPSINDLTD','TIPS Industries','Media'),
    ('TIRUMALCHM','Tirumala Chemicals','Chemicals'),('TITAN','Titan','Retail'),
    ('TMB','Tamilnad Mercantile','Banking'),('TMC','TMC','Media'),
    ('TMF','TMF','Financial'),('TMRVL','TMRVL','Financial'),
    ('TNIDF','TNIDF','Financial'),('TNPL','Tamil Nadu Newsprint','Paper'),
    ('TOKYOPLAST','Tokyo Plast','Consumer'),('TORNTPHARM','Torrent Pharma','Pharma'),
    ('TORNTPOWER','Torrent Power','Power'),('TPLPLASTEH','TPL Plastech','Packaging'),
    ('TREEHOUSE','Tree House','Media'),('TRENT','Trent','Retail'),
    ('TRF','TRF','Capital Goods'),('TRIDENT','Trident','Textiles'),
    ('TRIGYN','Trigyn Technologies','IT'),('TRIL','Triliance Polymers','Chemicals'),
    ('TRITURBINE','Triveni Turbine','Capital Goods'),('TRIVENI','Triveni Engineering','FMCG'),
    ('TTKHLTCARE','TTK Healthcare','Pharma'),('TTKPRESTIG','TTK Prestige','Consumer'),
    ('TTML','TTML','Telecom'),('TV18BRDCST','TV18 Broadcast','Media'),
    ('TVSELECT','TVS Electronics','IT'),('TVSMOTOR','TVS Motor','Auto'),
    ('TVSSRICHAK','TVS Srichakra','Auto'),('TVTODAY','TV Today','Media'),
    ('UBL','United Breweries','FMCG'),('UCOBANK','UCO Bank','Banking'),
    ('UDAICEMENT','Udaipur Cement','Infrastructure'),('UFLEX','UFLEX','Packaging'),
    ('UGARSUGAR','Ugar Sugar','FMCG'),('UJAAS','Ujaas Energy','Energy'),
    ('UJJIVAN','Ujjivan SFB','Banking'),('UJJIVANSFB','Ujjivan Small Finance','Banking'),
    ('ULTRACEMCO','UltraTech Cement','Infrastructure'),('UMANGDAIRY','Umang Dairies','FMCG'),
    ('UMESLTD','Umes Ltd','Chemicals'),('UNICHEMLAB','Unichem Labs','Pharma'),
    ('UNIDT','UnidT','Textiles'),('UNIENTER','UniEnterprises','Pharma'),
    ('UNIINFO','Uniinfo Telecom','Telecom'),('UNIONBANK','Union Bank','Banking'),
    ('UNIPLY','Uniply Industries','Infrastructure'),('UNISHIRE','Unishire Urban','Real Estate'),
    ('UNITEDTEA','United Tea','FMCG'),('UNIVASTU','Univastu','Real Estate'),
    ('UNIVCABLES','Univ Cables','Infrastructure'),('UNJHA','Unjha','Chemicals'),
    ('UNOMINDA','UNO Minda','Auto'),('UPL','UPL','Chemicals'),
    ('URAVI','Uravi T & Wedge','Auto'),('URBANENVIRO','Urban Enviro','Infrastructure'),
    ('URJA','Urja Global','Energy'),('USHAMART','Ushamart','Consumer'),
    ('USK','USK','Infrastructure'),('UTIAMC','UTI AMC','Financial Services'),
    ('UTKARSHBNK','Utkarsh Small Finance','Banking'),('UTTAMSUGAR','Uttam Sugar','FMCG'),
    ('V2RETAIL','V2 Retail','Retail'),('VADILAL','Vadilal Industries','FMCG'),
    ('VAIBHAVGBL','Vaibhav Global','Retail'),('VAISHALI','Vaishali Pharma','Pharma'),
    ('VAKRANGEE','Vakrangee','IT'),('VALIANT','Valiant Organics','Chemicals'),
    ('VALUEMOMT','Value Momentum','Financial'),('VAMA','Vama Industries','IT'),
    ('VARDHACRLC','Vardhman Acrylic','Textiles'),('VARDHMAN','Vardhman Textiles','Textiles'),
    ('VARROC','Varroc Engineering','Auto'),('VASCONEQ','Vascon Engineers','Infrastructure'),
    ('VASWANI','Vaswani Industries','Metals'),('VBL','Varun Beverages','FMCG'),
    ('VEDL','Vedanta','Metals'),('VENKEYS','Venky''s','FMCG'),
    ('VENUSPIPES','Venus Pipes','Infrastructure'),('VENUSREM','Venus Remedies','Pharma'),
    ('VERA','Vera Synthetic','Textiles'),('VERTOZ','Vertoz','IT'),
    ('VESUVIUS','Vesuvius India','Infrastructure'),('VETO','Veto Switchgears','Consumer'),
    ('VGUARD','V-Guard','Consumer'),('VHL','VHL','Financial'),
    ('VIABILITY','Viabilité','Financial'),('VICEROY','Viceroy Hotels','Hospitality'),
    ('VIDHIING','Vidhi Specialty','Chemicals'),('VIJAYA','Vijaya Diagnostic','Healthcare'),
    ('VIJAYABANK','Vijaya Bank','Banking'),('VIKASECO','Vikas EcoTech','Textiles'),
    ('VIKASLIFE','Vikas Lifecare','Pharma'),('VIKASPROP','Vikas Proppant','Infrastructure'),
    ('VILINBIO','Vilin Bio','Pharma'),('VIMTALABS','Vimta Labs','Pharma'),
    ('VINATIORGA','Vinati Organics','Chemicals'),('VINDHYATEL','Vindhya Telelinks','IT'),
    ('VINEETLAB','Vineet Laboratories','Pharma'),('VINNY','Vinny Overseas','Textiles'),
    ('VINYLINDIA','Vinyl Chemicals','Chemicals'),('VIPCLOTHNG','VIP Clothing','Textiles'),
    ('VIPIND','VIP Industries','Consumer'),('VIPULLTD','Vipul Ltd','Real Estate'),
    ('VIRINCHI','Virinchi','IT'),('VISAKAIND','Visaka Industries','Infrastructure'),
    ('VISHAL','Vishal Fabrics','Textiles'),('VISHNU','Vishnu Chemicals','Chemicals'),
    ('VISHWARAJ','Vishwaraj Sugar','FMCG'),('VIVIDHA','Vividha','Real Estate'),
    ('VIVIMEDLAB','Vivimed Labs','Pharma'),('VLF','VLF','Financial'),
    ('VMART','V-Mart Retail','Retail'),('VMS','VMS Industries','Financial'),
    ('VODAFONE','Vodafone Idea','Telecom'),('VOLTAMP','Voltamp','Capital Goods'),
    ('VOLTAS','Voltas','Consumer'),('VRLLOG','VRL Logistics','Logistics'),
    ('VSSL','VSSL','Infrastructure'),('VSTIND','VST Industries','FMCG'),
    ('VSTTILLERS','VST Tillers','Auto'),('VTL','Vardhaman Textiles','Textiles'),
    ('WABAG','WABAG','Infrastructure'),('WALCHANNAG','Walchandnagar','Capital Goods'),
    ('WANBURY','Wanbury','Pharma'),('WCIL','WCIL','Infrastructure'),
    ('WEBELSOLAR','Webel Solar','Energy'),('WEIZMANN','Weizmann','Textiles'),
    ('WELCORP','Welcorp','Metals'),('WELENT','Welspun Enterprises','Infrastructure'),
    ('WELINV','Welspun Invest','Financial'),('WELSPUNLIV','Welspun Living','Textiles'),
    ('WENDT','Wendt India','Infrastructure'),('WESTLEISURE','Westlife Foodpark','Hospitality'),
    ('WFL','WFL','Financial'),('WHIRLPOOL','Whirlpool','Consumer'),
    ('WILLAMAGOR','Williamson Magor','FMCG'),('WINDMACHIN','Windmills Machines','Capital Goods'),
    ('WINSOME','Winsome Textiles','Textiles'),('WIPRO','Wipro','IT'),
    ('WOCKPHARMA','Wockhardt','Pharma'),('WONDERLA','Wonderla Holidays','Hospitality'),
    ('WORTH','Worth Peripherals','Packaging'),('WSI','WSI','IT'),
    ('XCHANGING','Xchanging Solutions','IT'),('XPRO','Xpro India','Chemicals'),
    ('YAARII','Yaarii Digital','IT'),('YAMNINV','Yamini Investments','Financial'),
    ('YASHO','Yasho Industries','Chemicals'),('YATHARTH','Yatharth Hospital','Healthcare'),
    ('YCCL','YCCL','Financial'),('YENKAY','Yenkay','Auto'),
    ('YESBANK','Yes Bank','Banking'),('YOGI','Yogi Infra','Infrastructure'),
    ('YORK','York Exports','Textiles'),('YUDIZ','Yudiz Solutions','IT'),
    ('ZEEL','Zee Entertainment','Media'),('ZEEMEDIA','Zee Media','Media'),
    ('ZENSARTECH','Zensar Technologies','IT'),('ZENSTAINLESS','Zenith Steel','Metals'),
    ('ZENTEC','Zen Technologies','Defence'),('ZFCVINDIA','ZF Commercial','Auto'),
    ('ZODIACLOTH','Zodiac Clothing','Textiles'),('ZOMATO','Zomato','IT'),
    ('ZUARI','Zuari Agro','Chemicals'),('ZYDUSLIFE','Zydus Lifesciences','Pharma'),
    ('ZYDUSWELL','Zydus Wellness','FMCG'),
]


# ── Deduplicated merged universe ──────────────────────────────────────
_STOCK_MAP: dict[str, tuple] = {}
for _s in STOCK_MASTER + EXTRA_STOCKS:
    _STOCK_MAP[_s[0]] = _s
ALL_STOCKS = list(_STOCK_MAP.values())
DEFAULT_TICKERS = [s[0] for s in ALL_STOCKS]


def _rng(ticker):
    seed = int(hashlib.md5(ticker.encode()).hexdigest()[:8], 16)
    return random.Random(seed)


def _daily_rng(ticker):
    seed = int(hashlib.md5(f"{datetime.now().strftime('%Y-%m-%d')}_{ticker}".encode()).hexdigest()[:8], 16)
    return random.Random(seed)


def _stock_dict(ticker):
    s = _STOCK_MAP.get(ticker.upper())
    if s is not None:
        if len(s) >= 13:
            return {
                "ticker": s[0], "name": s[1], "sector": s[2],
                "basePrice": s[3], "pe": s[4], "pb": s[5], "roe": s[6],
                "revGrowth": s[7], "momentum": s[8], "quality": s[9],
                "value": s[10], "growth": s[11], "marketCap": s[12],
            }
        # 3-field entry — generate financials dynamically
        rng = _rng(ticker)
        bp = round(rng.uniform(50, 5000), 2)
        return {
            "ticker": s[0], "name": s[1], "sector": s[2],
            "basePrice": bp, "pe": round(rng.uniform(5, 80), 1),
            "pb": round(rng.uniform(0.5, 20), 1),
            "roe": round(rng.uniform(5, 40), 1),
            "revGrowth": round(rng.uniform(2, 30), 1),
            "momentum": rng.randint(30, 85),
            "quality": rng.randint(35, 85),
            "value": rng.randint(20, 90),
            "growth": rng.randint(35, 85),
            "marketCap": round(rng.uniform(1000, 50000), 0),
        }
    rng = _rng(ticker)
    ticker_upper = ticker.upper()
    bp = round(rng.uniform(50, 5000), 2)
    return {
        "ticker": ticker_upper, "name": ticker_upper,
        "sector": rng.choice(["Banking", "IT", "Auto", "Pharma", "FMCG", "Energy", "Consumer", "Others"]),
        "basePrice": bp, "pe": round(rng.uniform(5, 80), 1),
        "pb": round(rng.uniform(0.5, 20), 1),
        "roe": round(rng.uniform(5, 40), 1),
        "revGrowth": round(rng.uniform(2, 30), 1),
        "momentum": rng.randint(30, 85),
        "quality": rng.randint(35, 85),
        "value": rng.randint(20, 90),
        "growth": rng.randint(35, 85),
        "marketCap": round(rng.uniform(1000, 50000), 0),
    }


def get_seed_quote(ticker):
    s = _stock_dict(ticker)
    rng = _daily_rng(ticker)
    bp = s["basePrice"]
    daily_drift = rng.uniform(-0.03, 0.03)
    daily_price = round(bp * (1 + daily_drift), 2)
    change_pct = round(rng.uniform(-1.5, 1.5), 2)
    change = round(daily_price * change_pct / 100, 2)
    return {
        "ticker": s["ticker"], "name": s["name"], "sector": s["sector"],
        "price": daily_price, "change": change,
        "changePercent": change_pct,
        "volume": rng.randint(100000, 5000000),
        "marketCap": round(s["marketCap"] * (1 + rng.uniform(-0.01, 0.01)), 0),
    }


def get_seed_fundamentals(ticker):
    s = _stock_dict(ticker)
    rng = _rng(ticker)
    return {
        "ticker": s["ticker"], "name": s["name"],
        "pe": s["pe"], "pb": s["pb"], "roe": s["roe"],
        "eps": round(s["basePrice"] / s["pe"], 2) if s["pe"] > 0 else 0,
        "revenueGrowth": s["revGrowth"],
        "debtToEquity": round(rng.uniform(0.1, 3.0), 2),
        "currentRatio": round(rng.uniform(0.5, 3.5), 2),
        "dividendYield": round(rng.uniform(0, 4), 2),
        "sector": s["sector"], "marketCap": s["marketCap"],
        "marketCapCategory": "Large Cap" if s["marketCap"] > 20000 else "Mid Cap" if s["marketCap"] > 5000 else "Small Cap",
    }


def get_seed_price_history(ticker, days=365):
    s = _stock_dict(ticker)
    rng = _rng(ticker + "_hist")
    base = s["basePrice"]
    prices = []
    p = base * 0.80
    start = datetime.now() - timedelta(days=days)
    for i in range(days):
        d = start + timedelta(days=i)
        if d.weekday() >= 5:
            continue
        shock = rng.uniform(-0.02, 0.02) if rng.random() < 0.06 else 0
        p *= 1 + 0.0004 + rng.uniform(-0.009, 0.009) + shock
        high = p * (1 + rng.uniform(0, 0.015))
        low = p * (1 - rng.uniform(0, 0.015))
        prices.append({
            "date": d.strftime("%Y-%m-%d"),
            "open": round(p * (1 + rng.uniform(-0.005, 0.005)), 2),
            "high": round(high, 2),
            "low": round(low, 2),
            "close": round(p, 2),
            "volume": rng.randint(50000, 3000000),
        })
    if prices:
        scale = base / prices[-1]["close"]
        for i in range(len(prices)):
            prices[i]["open"] = round(prices[i]["open"] * scale, 2)
            prices[i]["high"] = round(prices[i]["high"] * scale, 2)
            prices[i]["low"] = round(prices[i]["low"] * scale, 2)
            prices[i]["close"] = round(prices[i]["close"] * scale, 2)
    return prices


def get_seed_screener_results(filters=None):
    results = []
    for s in ALL_STOCKS:
        d = _stock_dict(s[0])
        item = {
            "ticker": d["ticker"], "name": d["name"], "sector": d["sector"],
            "price": d["basePrice"], "pe": d["pe"], "pb": d["pb"], "roe": d["roe"],
            "revenueGrowth": d["revGrowth"], "momentum": d["momentum"], "quality": d["quality"],
            "value": d["value"], "growth": d["growth"], "marketCap": d["marketCap"],
        }
        if filters:
            if filters.get("sector") and item["sector"] != filters["sector"]:
                continue
            if filters.get("min_roe") and item["roe"] < filters["min_roe"]:
                continue
            if filters.get("max_pe") and item["pe"] > filters["max_pe"]:
                continue
            if filters.get("min_mom") and item["momentum"] < filters["min_mom"]:
                continue
        results.append(item)
    return sorted(results, key=lambda x: (x.get("momentum") or 0) + (x.get("quality") or 0), reverse=True)



def get_seed_sectors():
    return sorted({s[2] for s in ALL_STOCKS})


def get_seed_stock_list():
    return [{"ticker": s[0], "name": s[1], "sector": s[2]} for s in ALL_STOCKS]


def search_tickers(query):
    q = query.upper().strip()
    results = []
    for s in ALL_STOCKS:
        if q in s[0].upper() or q in s[1].upper():
            results.append({"ticker": s[0], "name": s[1], "sector": s[2]})
    # Also search generated stocks for unknown tickers
    if not results:
        s = _stock_dict(q)
        results.append({"ticker": s["ticker"], "name": s["name"], "sector": s["sector"]})
    return results


def get_batch_quotes(tickers):
    return {t: get_seed_quote(t) for t in tickers}


def get_sector_performance():
    sectors = get_seed_sectors()
    from random import Random
    r = Random("sector_perf")
    return {s: {"1d": round(r.uniform(-2, 2), 2), "1w": round(r.uniform(-5, 5), 2), "1m": round(r.uniform(-10, 10), 2)} for s in sectors}


def get_universe_overview():
    """Return overview data for all stocks."""
    result = []
    for entry in ALL_STOCKS:
        s = _stock_dict(entry[0])
        base = s["basePrice"]
        change = round(_rng(entry[0]).uniform(-base * 0.03, base * 0.03), 2)
        change_pct = round(change / base * 100, 2)
        result.append({
            "ticker": s["ticker"], "name": s["name"], "sector": s["sector"],
            "price": base, "change": change, "change_pct": change_pct,
            "volume": s.get("avgVolume", round(_rng(entry[0]).uniform(100000, 5000000), 0)), "market_cap": s["marketCap"],
        })
    return result


def get_market_indices():
    """Return market index data (NIFTY 50, SENSEX, BANK NIFTY)."""
    r = _rng("indices")
    indices = [
        {"name": "NIFTY 50", "last": round(r.uniform(22000, 26000), 2)},
        {"name": "SENSEX", "last": round(r.uniform(72000, 86000), 2)},
        {"name": "BANK NIFTY", "last": round(r.uniform(46000, 56000), 2)},
    ]
    for idx in indices:
        chg = round(r.uniform(-idx["last"] * 0.01, idx["last"] * 0.01), 2)
        idx["change"] = chg
        idx["change_pct"] = round(chg / idx["last"] * 100, 2)
    return indices


# ── DEPRECATED ALIASES (backward compat with data_service.py) ─────
def get_quote(ticker):
    return get_seed_quote(ticker)


def get_fundamentals(ticker):
    return get_seed_fundamentals(ticker)


_PERIOD_DAYS = {"1mo": 30, "3mo": 90, "6mo": 180, "1y": 365, "2y": 730, "5y": 1825}


def get_price_history(ticker, period="1y", interval="1d"):
    days = _PERIOD_DAYS.get(period, 365)
    return get_seed_price_history(ticker, days)
