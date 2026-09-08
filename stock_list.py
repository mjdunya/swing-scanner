"""
Stock universes for both markets (Yahoo Finance symbols).
"""

INDIA_STOCKS = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "ITC",
    "SBIN", "BHARTIARTL", "LT", "AXISBANK", "MARUTI", "TATAMOTORS",
    "TATASTEEL", "TATAPOWER", "WIPRO", "HCLTECH", "SUNPHARMA",
    "BAJFINANCE", "ADANIENT", "ADANIPORTS", "ASIANPAINT", "DMART",
    "TITAN", "NESTLEIND", "ULTRACEMCO", "JSWSTEEL", "COALINDIA",
    "ONGC", "NTPC", "POWERGRID", "M&M", "TECHM", "HINDUNILVR",
    "DRREDDY", "CIPLA", "DIVISLAB", "EICHERMOT", "HEROMOTOCO",
    "BAJAJ-AUTO", "BPCL", "GRASIM", "HINDALCO", "VEDL", "PFC",
    "RECLTD", "DLF", "GODREJPROP", "ZOMATO", "NYKAA", "POLICYBZR",
    "DABUR", "BRITANNIA", "GAIL", "IOC", "BEL", "HAL", "IRFC",
    "LICI", "TRENT", "PIDILITIND", "SIEMENS", "ABB", "CUMMINSIND",
    "ASHOKLEY", "TVSMOTOR", "BAJAJFINSV", "SBILIFE", "HDFCLIFE",
    "ICICIGI", "INDUSINDBK", "BANKBARODA", "PNB", "CANBK", "UNIONBANK",
    "IDEA", "YESBANK", "SUZLON", "IEX", "IREDA", "RVNL", "IRCTC",
    "CPSEETF", "NHPC", "SJVN", "TATAINVEST", "ABCAPITAL", "LTF",
    "CHOLAFIN", "MUTHOOTFIN", "MANAPPURAM", "CDSL", "BSE", "MCX",
    "ANGELONE", "KOTAKBANK", "FEDERALBNK", "IDFCFIRSTB", "AUBANK",
    "PAYTM", "CAMS", "KEI", "POLYCAB", "HAVELLS", "VOLTAS",
    "BLUESTAR", "AMBER", "DIXON", "KAYNES", "SYRMA", "CGPOWER",
    "BJAJHLDNG", "WHLPOOL", "ASTRAL", "SUPREMEIND", "ESCORTS",
]

SAUDI_STOCKS = [
    "2222.SR",   # Saudi Aramco
    "1120.SR",   # Al Rajhi Bank
    "2010.SR",   # SABIC
    "1180.SR",   # Al Ahli Bank / SNB
    "7010.SR",   # STC
    "2350.SR",   # Riyad Bank
    "1050.SR",   # Alinma Bank
    "1150.SR",   # Alinma
    "4030.SR",   # Al Rajhi Takaful
    "2280.SR",   # Almarai
    "4004.SR",   # Saudi Telecom wait — see note below
    "7020.SR",   # Etihad Etisalat (Mobily)
    "2001.SR",   # Sipchem
    "2310.SR",   # Sahara Petrochemicals
    "2082.SR",   # Yanbu National Petrochemicals
    "2020.SR",   # SADAFCO
    "4161.SR",   # Bank Albilad
    "4164.SR",   # Bank Aljazira
    "3020.SR",   # Saudi Cement
    "2170.SR",   # Al Yamamah Steel
    "1301.SR",   # Abdulla Al Aqeel? use: 1302.SR
    "1302.SR",   # 1302 Group
    "1214.SR",   # SAVOLA wait — see note below
    "4142.SR",   # Salama Cooperative Insurance
    "8240.SR",   # Saudi British Bank (SABB)
    "3060.SR",   # FIPCO
    "1810.SR",   # Saudi Airlines? use: 4190.SR
    "4190.SR",   # SAL Saudi Logistics
    "4321.SR",   # Dr. Sulaiman Al Habib
    "4006.SR",   # Saudi Telecom wait — see note below
    "6004.SR",   # Amiantit
    "2070.SR",   # Chemanol
    "2100.SR",   # Al-Babtain
    "4210.SR",   # Al Kathiri
    "4330.SR",   # Saudi Industrial Development
    "4300.SR",   # Dar Al Arkan
    "4250.SR",   # Jazira? use: 4260.SR
    "4260.SR",   # Anaam International
    "9520.SR",   # Alinma Retail? use: 9500.SR
    "9500.SR",   # Riyadh REIT
]

# NOTE: common correct tickers — keep these if present:
# Saudi Telecom (STC)  = 7010.SR
# Savola               = 4030 wait — Savola is 2050.SR
SAUDI_FIXES = [
    "2050.SR",   # Savola Group
]

SAUDI_STOCKS = SAUDI_STOCKS + SAUDI_FIXES

MARKETS = {
    "india": {
        "name": "India (NSE)",
        "flag": "🇮🇳",
        "currency": "₹",
        "benchmark": "^NSEI",        # NIFTY 50
    },
    "saudi": {
        "name": "Saudi (Tadawul)",
        "flag": "🇸🇦",
        "currency": "SAR ",
        "benchmark": "^TASI.SR",     # Tadawul All Share
    },
}


def get_yahoo_symbols(market="india"):
    if market == "saudi":
        return SAUDI_STOCKS
    return [s + ".NS" for s in INDIA_STOCKS]


def get_market_info(market="india"):
    return MARKETS.get(market, MARKETS["india"])
