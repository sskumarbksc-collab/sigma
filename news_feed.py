import urllib.request
import xml.etree.ElementTree as ET
import re
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

logger = logging.getLogger("MarketNewsFeed")

class MarketNewsFeed:
    """
    Live RSS News Feed & Financial Sentiment Engine for Indian Markets (NSE/BSE).
    Fetches real-time market updates from Google News India Finance & Economic Times Markets.
    Performs keyword-based NLP sentiment scoring and stock symbol tagging.
    """

    RSS_FEEDS = [
        {
            "name": "Google News NSE",
            "url": "https://news.google.com/rss/search?q=Nifty+NSE+Stock+Market+India&hl=en-IN&gl=IN&ceid=IN:en",
            "weight": 1.0
        },
        {
            "name": "Economic Times Markets",
            "url": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
            "weight": 1.2
        }
    ]

    BULLISH_KEYWORDS = [
        "PROFIT JUMPS", "PROFIT RISES", "PROFIT SOARS", "SURGE", "RALLY", "SURGES", "RALLIES",
        "BEATS ESTIMATES", "BEATS EXPECTATIONS", "ORDER WIN", "WINS ORDER", "WINS CONTRACT",
        "UPGRADE", "UPGRADES", "DIVIDEND", "STAKE BUY", "BUYS STAKE", "EXPANSION", "GROWTH",
        "RECORD HIGH", "ALL-TIME HIGH", "OUTPERFORM", "BUY CALL", "BULL RUN", "REBOUND",
        "RECOVERS", "TARGET RAISED", "POSITIVE", "ACQUISITION", "DEAL SIGNED", "BLOCK DEAL",
        "HIGHEST EVER", "BONUS ISSUE", "STAKE INCREASE"
    ]

    BEARISH_KEYWORDS = [
        "PROFIT DROPS", "PROFIT FALLS", "PROFIT SLUMPS", "LOSS WIDENS", "NET LOSS",
        "SLUMP", "SLUMPS", "PLUNGE", "PLUNGES", "PROBE", "DOWNGRADE", "DOWNGRADES",
        "SELLOFF", "WEAK GROWTH", "MISSES ESTIMATES", "FRAUD", "PENALTY", "RESIGNS",
        "DEFAULT", "HEADWINDS", "CRASH", "CRASHES", "BEARISH", "INFLATION SURGE",
        "RATE HIKE", "SEBI NOTICE", "TAX DEMAND", "DISPUTE", "STRIKE", "FALLS OVER",
        "TARGET CUT", "WARNING", "CAUTION"
    ]

    # Common NSE Large & Midcap tickers to tag
    KNOWN_TICKERS = {
        "RELIANCE": ["RELIANCE", "RIL", "JIO"],
        "TCS": ["TCS", "TATA CONSULTANCY"],
        "HDFCBANK": ["HDFC BANK", "HDFCBANK"],
        "ICICIBANK": ["ICICI BANK", "ICICIBANK"],
        "SBIN": ["SBI", "STATE BANK OF INDIA", "SBIN"],
        "INFY": ["INFOSYS", "INFY"],
        "ITC": ["ITC"],
        "TMPV": ["TATA MOTORS", "TMPV"],
        "TATAMOTORS": ["TATA MOTORS"],
        "BAJFINANCE": ["BAJAJ FINANCE", "BAJFINANCE"],
        "BHARTIARTL": ["BHARTI AIRTEL", "AIRTEL"],
        "LT": ["L&T", "LARSEN & TOUBRO"],
        "KOTAKBANK": ["KOTAK", "KOTAK BANK"],
        "AXISBANK": ["AXIS BANK"],
        "MARUTI": ["MARUTI", "MARUTI SUZUKI"],
        "SUNPHARMA": ["SUN PHARMA"],
        "TITAN": ["TITAN"],
        "WIPRO": ["WIPRO"],
        "TATASTEEL": ["TATA STEEL"],
        "ADANIENT": ["ADANI ENTERPRISES", "ADANI"],
        "ADANIPORTS": ["ADANI PORTS"],
        "COALINDIA": ["COAL INDIA"],
        "NTPC": ["NTPC"],
        "ONGC": ["ONGC"],
        "POWERGRID": ["POWER GRID"]
    }

    def __init__(self):
        self._cached_news: List[Dict[str, Any]] = []
        self._last_fetch_time: Optional[datetime] = None
        self._cache_duration_seconds = 180  # 3 minutes cache

    def fetch_news(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Fetches and parses live RSS feeds with caching."""
        now = datetime.now()
        if not force_refresh and self._cached_news and self._last_fetch_time:
            if (now - self._last_fetch_time).total_seconds() < self._cache_duration_seconds:
                return self._cached_news

        all_items = []
        for feed in self.RSS_FEEDS:
            try:
                req = urllib.request.Request(
                    feed["url"],
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                )
                with urllib.request.urlopen(req, timeout=6) as resp:
                    xml_data = resp.read()
                    root = ET.fromstring(xml_data)
                    items = root.findall(".//item")
                    for item in items:
                        title = item.find("title").text if item.find("title") is not None else ""
                        link = item.find("link").text if item.find("link") is not None else "#"
                        pub_date = item.find("pubDate").text if item.find("pubDate") is not None else ""
                        desc = item.find("description").text if item.find("description") is not None else ""
                        
                        # Clean html from description
                        clean_desc = re.sub(r'<[^>]+>', '', desc).strip()[:180]
                        
                        # Sentiment & symbol analysis
                        sentiment, impact_score = self._analyze_sentiment(title + " " + clean_desc)
                        tagged_symbols = self._tag_symbols(title + " " + clean_desc)

                        all_items.append({
                            "title": title.strip(),
                            "link": link.strip(),
                            "source": feed["name"],
                            "published_at": pub_date.strip(),
                            "summary": clean_desc,
                            "sentiment": sentiment,
                            "impact_score": impact_score,
                            "tagged_symbols": tagged_symbols,
                            "is_breaking": abs(impact_score) >= 0.75
                        })
            except Exception as e:
                logger.warning(f"Error fetching RSS from {feed['name']}: {e}")

        # Deduplicate by title
        seen_titles = set()
        unique_items = []
        for item in all_items:
            t = item["title"]
            if t and t not in seen_titles:
                seen_titles.add(t)
                unique_items.append(item)

        # Sort: Breaking news and highest absolute impact first
        unique_items.sort(key=lambda x: abs(x["impact_score"]), reverse=True)

        self._cached_news = unique_items[:40]
        self._last_fetch_time = now
        return self._cached_news

    def _analyze_sentiment(self, text: str) -> (str, float):
        """Calculates polarity and impact score based on financial catalyst keywords."""
        upper = text.upper()
        bull_hits = sum(1 for kw in self.BULLISH_KEYWORDS if kw in upper)
        bear_hits = sum(1 for kw in self.BEARISH_KEYWORDS if kw in upper)

        if bull_hits > bear_hits:
            score = round(min(1.0, 0.4 + (bull_hits * 0.25)), 2)
            return "BULLISH", score
        elif bear_hits > bull_hits:
            score = round(max(-1.0, -0.4 - (bear_hits * 0.25)), 2)
            return "BEARISH", score
        else:
            return "NEUTRAL", 0.0

    def _tag_symbols(self, text: str) -> List[str]:
        """Tags NSE symbols mentioned in the headline."""
        upper = text.upper()
        matches = []
        for sym, aliases in self.KNOWN_TICKERS.items():
            for alias in aliases:
                if re.search(r'\b' + re.escape(alias) + r'\b', upper):
                    matches.append(sym)
                    break
        return matches

    def get_news_sentiment_for_symbol(self, symbol: str) -> Dict[str, Any]:
        """
        Retrieves news sentiment and headlines relevant to a specific NSE stock.
        Used by Agent 8 (News & Catalyst Scanner) to confirm trade direction.
        """
        clean_sym = symbol.replace(".NS", "").replace("^", "")
        all_news = self.fetch_news()
        
        matching = []
        for n in all_news:
            if clean_sym in n.get("tagged_symbols", []) or clean_sym in n.get("title", "").upper():
                matching.append(n)

        if not matching:
            # Fall back to macro market news sentiment
            macro_news = [n for n in all_news if "NIFTY" in n.get("title", "").upper() or "MARKET" in n.get("title", "").upper()]
            if macro_news:
                top_macro = macro_news[0]
                return {
                    "has_news": False,
                    "macro_sentiment": top_macro["sentiment"],
                    "macro_score": top_macro["impact_score"],
                    "headline": top_macro["title"],
                    "source": top_macro["source"]
                }
            return {"has_news": False, "sentiment": "NEUTRAL", "score": 0.0, "headline": None}

        top_story = matching[0]
        return {
            "has_news": True,
            "sentiment": top_story["sentiment"],
            "score": top_story["impact_score"],
            "headline": top_story["title"],
            "source": top_story["source"],
            "all_articles": matching[:3]
        }

    def get_macro_overview(self) -> Dict[str, Any]:
        """Returns overall market news tone (% bullish vs % bearish)."""
        news = self.fetch_news()
        if not news:
            return {"total_stories": 0, "bullish_pct": 50.0, "bearish_pct": 50.0, "dominant_sentiment": "BALANCED"}

        bull_count = sum(1 for n in news if n["sentiment"] == "BULLISH")
        bear_count = sum(1 for n in news if n["sentiment"] == "BEARISH")
        neutral_count = len(news) - (bull_count + bear_count)

        total_directional = max(1, bull_count + bear_count)
        bull_pct = round((bull_count / total_directional) * 100, 1)
        bear_pct = round((bear_count / total_directional) * 100, 1)

        if bull_pct >= 60.0:
            dominant = "BULLISH CATALYST"
        elif bear_pct >= 60.0:
            dominant = "BEARISH HEADWINDS"
        else:
            dominant = "MIXED SENTIMENT"

        return {
            "total_stories": len(news),
            "bullish_count": bull_count,
            "bearish_count": bear_count,
            "neutral_count": neutral_count,
            "bullish_pct": bull_pct,
            "bearish_pct": bear_pct,
            "dominant_sentiment": dominant,
            "latest_headline": news[0]["title"] if news else "",
            "breaking_count": sum(1 for n in news if n.get("is_breaking"))
        }

# Global singleton
market_news_service = MarketNewsFeed()
