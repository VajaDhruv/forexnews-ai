import asyncio
import feedparser
import httpx
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.dialects.postgresql import insert
import structlog

from app.config import settings
from app.db.session import get_db
from app.db.models import NewsArticle, NewsSource, NewsImpact, SentimentLabel
from app.ml.models.sentiment_analyzer import SentimentAnalyzer

logger = structlog.get_logger()


class NewsIngestionService:
    def __init__(self, sentiment_analyzer: SentimentAnalyzer):
        self.sentiment_analyzer = sentiment_analyzer
        self.running = False
        self.ingestion_task = None
        self.client = httpx.AsyncClient(timeout=30.0)
        self.seen_urls = set()

        # Source-specific parsers
        self.parsers = {
            NewsSource.FOREX_FACTORY: self._parse_forex_factory,
            NewsSource.INVESTING_COM: self._parse_investing_com,
            NewsSource.DAILYFX: self._parse_dailyfx,
            NewsSource.BLOOMBERG: self._parse_generic_rss,
            NewsSource.REUTERS: self._parse_generic_rss,
            NewsSource.CNBC: self._parse_generic_rss,
            NewsSource.MARKETWATCH: self._parse_generic_rss,
            NewsSource.YAHOO_FINANCE: self._parse_generic_rss,
        }

    async def start_ingestion_loop(self):
        self.running = True
        self.ingestion_task = asyncio.create_task(self._ingestion_loop())
        logger.info("News ingestion loop started")

    async def stop(self):
        self.running = False
        if self.ingestion_task:
            self.ingestion_task.cancel()
            try:
                await self.ingestion_task
            except asyncio.CancelledError:
                pass
        await self.client.aclose()
        logger.info("News ingestion loop stopped")

    async def _ingestion_loop(self):
        while self.running:
            try:
                await self.ingest_all_sources()
            except Exception as e:
                logger.error("Error in ingestion loop", error=str(e))

            # Wait before next cycle
            await asyncio.sleep(60)  # Check every minute

    async def ingest_all_sources(self):
        tasks = []
        for source_url in settings.NEWS_SOURCES:
            source = self._identify_source(source_url)
            tasks.append(self.ingest_source(source, source_url))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Failed to ingest source {settings.NEWS_SOURCES[i]}", error=str(result))

    async def ingest_source(self, source: NewsSource, url: str) -> int:
        try:
            parser = self.parsers.get(source, self._parse_generic_rss)
            articles = await parser(url, source)

            saved_count = 0
            for article_data in articles:
                if await self._save_article(article_data):
                    saved_count += 1

            logger.info(f"Ingested {saved_count} new articles from {source.value}")
            return saved_count

        except Exception as e:
            logger.error(f"Failed to ingest from {source.value}", url=url, error=str(e))
            raise

    async def _parse_forex_factory(self, url: str, source: NewsSource) -> List[Dict]:
        """Parse Forex Factory calendar XML"""
        response = await self.client.get(url)
        feed = feedparser.parse(response.text)

        articles = []
        for entry in feed.entries:
            # Extract currency and impact from title
            title = entry.get('title', '')
            currency, impact = self._extract_ff_info(title)

            article = {
                'title': title,
                'content': entry.get('summary', ''),
                'summary': entry.get('summary', '')[:500],
                'url': entry.get('link', ''),
                'source': source,
                'published_at': self._parse_date(entry.get('published', '')),
                'related_pairs': self._get_pairs_for_currency(currency),
                'impact_level': impact,
                'categories': ['economic_calendar'],
            }
            articles.append(article)
        return articles

    async def _parse_investing_com(self, url: str, source: NewsSource) -> List[Dict]:
        response = await self.client.get(url)
        feed = feedparser.parse(response.text)

        articles = []
        for entry in feed.entries:
            article = {
                'title': entry.get('title', ''),
                'content': entry.get('summary', ''),
                'summary': entry.get('summary', '')[:500],
                'url': entry.get('link', ''),
                'source': source,
                'published_at': self._parse_date(entry.get('published', '')),
                'related_pairs': self._extract_pairs_from_text(entry.get('title', '') + ' ' + entry.get('summary', '')),
                'impact_level': self._estimate_impact(entry.get('title', '') + ' ' + entry.get('summary', '')),
                'categories': self._extract_categories(entry.get('title', '') + ' ' + entry.get('summary', '')),
            }
            articles.append(article)
        return articles

    async def _parse_dailyfx(self, url: str, source: NewsSource) -> List[Dict]:
        response = await self.client.get(url)
        feed = feedparser.parse(response.text)

        articles = []
        for entry in feed.entries:
            article = {
                'title': entry.get('title', ''),
                'content': entry.get('summary', ''),
                'summary': entry.get('summary', '')[:500],
                'url': entry.get('link', ''),
                'source': source,
                'published_at': self._parse_date(entry.get('published', '')),
                'related_pairs': self._extract_pairs_from_text(entry.get('title', '') + ' ' + entry.get('summary', '')),
                'impact_level': self._estimate_impact(entry.get('title', '') + ' ' + entry.get('summary', '')),
                'categories': self._extract_categories(entry.get('title', '') + ' ' + entry.get('summary', '')),
            }
            articles.append(article)
        return articles

    async def _parse_generic_rss(self, url: str, source: NewsSource) -> List[Dict]:
        response = await self.client.get(url)
        feed = feedparser.parse(response.text)

        articles = []
        for entry in feed.entries:
            text = entry.get('title', '') + ' ' + entry.get('summary', '')
            article = {
                'title': entry.get('title', ''),
                'content': entry.get('summary', ''),
                'summary': entry.get('summary', '')[:500],
                'url': entry.get('link', ''),
                'source': source,
                'published_at': self._parse_date(entry.get('published', '')),
                'related_pairs': self._extract_pairs_from_text(text),
                'impact_level': self._estimate_impact(text),
                'categories': self._extract_categories(text),
            }
            articles.append(article)
        return articles

    def _identify_source(self, url: str) -> NewsSource:
        url_lower = url.lower()
        if 'forexfactory' in url_lower:
            return NewsSource.FOREX_FACTORY
        elif 'investing.com' in url_lower:
            return NewsSource.INVESTING_COM
        elif 'dailyfx' in url_lower:
            return NewsSource.DAILYFX
        elif 'bloomberg' in url_lower:
            return NewsSource.BLOOMBERG
        elif 'reuters' in url_lower:
            return NewsSource.REUTERS
        elif 'cnbc' in url_lower:
            return NewsSource.CNBC
        elif 'marketwatch' in url_lower:
            return NewsSource.MARKETWATCH
        elif 'yahoo' in url_lower:
            return NewsSource.YAHOO_FINANCE
        return NewsSource.CUSTOM

    def _extract_ff_info(self, title: str) -> tuple:
        """Extract currency and impact from Forex Factory title"""
        currency = 'USD'
        impact = NewsImpact.LOW

        title_lower = title.lower()

        # Currency detection
        currency_map = {
            'eur': 'EUR', 'gbp': 'GBP', 'jpy': 'JPY', 'chf': 'CHF',
            'aud': 'AUD', 'cad': 'CAD', 'nzd': 'NZD', 'usd': 'USD'
        }
        for key, val in currency_map.items():
            if key in title_lower:
                currency = val
                break

        # Impact detection
        if 'high' in title_lower or 'red' in title_lower:
            impact = NewsImpact.HIGH
        elif 'medium' in title_lower or 'orange' in title_lower:
            impact = NewsImpact.MEDIUM
        elif 'low' in title_lower or 'yellow' in title_lower:
            impact = NewsImpact.LOW

        return currency, impact

    def _get_pairs_for_currency(self, currency: str) -> List[str]:
        """Get all major pairs for a currency"""
        base_pairs = {
            'EUR': ['EURUSD', 'EURGBP', 'EURJPY', 'EURAUD', 'EURCAD', 'EURCHF'],
            'GBP': ['GBPUSD', 'EURGBP', 'GBPJPY', 'GBPAUD', 'GBPCAD', 'GBPCHF'],
            'JPY': ['USDJPY', 'EURJPY', 'GBPJPY', 'AUDJPY', 'CADJPY', 'CHFJPY'],
            'CHF': ['USDCHF', 'EURCHF', 'GBPCHF', 'AUDCHF', 'CADCHF', 'NZDCHF'],
            'AUD': ['AUDUSD', 'EURAUD', 'GBPAUD', 'AUDJPY', 'AUDCAD', 'AUDNZD', 'AUDCHF'],
            'CAD': ['USDCAD', 'EURCAD', 'GBPCAD', 'CADJPY', 'AUDCAD', 'NZDCAD', 'CADCHF'],
            'NZD': ['NZDUSD', 'EURNZD', 'GBPNZD', 'NZDJPY', 'AUDNZD', 'NZDCAD', 'NZDCHF'],
            'USD': ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'USDCAD', 'NZDUSD'],
        }
        return base_pairs.get(currency, [])

    def _extract_pairs_from_text(self, text: str) -> List[str]:
        """Extract forex pairs from text"""
        pairs = []
        text_upper = text.upper()

        for pair in settings.FOREX_PAIRS:
            if pair in text_upper:
                pairs.append(pair)

        # Also check for slash format
        for pair in settings.FOREX_PAIRS:
            slash_pair = pair[:3] + '/' + pair[3:]
            if slash_pair in text_upper:
                if pair not in pairs:
                    pairs.append(pair)

        return pairs[:10]  # Limit to 10 pairs

    def _estimate_impact(self, text: str) -> NewsImpact:
        """Estimate news impact based on keywords"""
        text_lower = text.lower()

        high_keywords = [
            'fed', 'ecb', 'boj', 'boe', 'rba', 'boc', 'rbnz', 'snb',
            'interest rate', 'rate decision', 'fomc', 'monetary policy',
            'nfp', 'non-farm', 'cpi', 'inflation', 'gdp', 'unemployment',
            'central bank', 'quantitative easing', 'tapering', 'hike', 'cut'
        ]

        medium_keywords = [
            'pmi', 'manufacturing', 'services', 'retail sales', 'industrial production',
            'trade balance', 'current account', 'consumer confidence', 'business confidence',
            'employment', 'wages', 'earnings', 'housing', 'building permits'
        ]

        for kw in high_keywords:
            if kw in text_lower:
                return NewsImpact.HIGH

        for kw in medium_keywords:
            if kw in text_lower:
                return NewsImpact.MEDIUM

        return NewsImpact.LOW

    def _extract_categories(self, text: str) -> List[str]:
        """Extract categories from text"""
        categories = []
        text_lower = text.lower()

        category_keywords = {
            'central_bank': ['fed', 'ecb', 'boj', 'boe', 'rba', 'boc', 'rbnz', 'snb', 'central bank', 'fomc'],
            'economic_data': ['gdp', 'cpi', 'ppi', 'pmi', 'unemployment', 'employment', 'retail', 'industrial'],
            'employment': ['nfp', 'non-farm', 'unemployment', 'jobless', 'employment', 'jobs', 'payroll'],
            'inflation': ['inflation', 'cpi', 'ppi', 'pce', 'price index'],
            'trade': ['trade balance', 'exports', 'imports', 'current account', 'trade deficit'],
            'geopolitical': ['war', 'conflict', 'sanctions', 'election', 'political', 'government'],
            'commodity': ['oil', 'gold', 'crude', 'brent', 'wti', 'commodity'],
            'earnings': ['earnings', 'profit', 'revenue', 'eps', 'quarterly results'],
        }

        for cat, keywords in category_keywords.items():
            if any(kw in text_lower for kw in keywords):
                categories.append(cat)

        return categories if categories else ['general']

    def _parse_date(self, date_str: str) -> datetime:
        """Parse various date formats"""
        if not date_str:
            return datetime.utcnow()

        formats = [
            '%a, %d %b %Y %H:%M:%S %Z',
            '%a, %d %b %Y %H:%M:%S %z',
            '%Y-%m-%dT%H:%M:%S%z',
            '%Y-%m-%dT%H:%M:%S.%f%z',
            '%Y-%m-%d %H:%M:%S',
            '%d %b %Y %H:%M:%S',
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        # Try feedparser's parsed date
        try:
            import time
            parsed = feedparser.parse(date_str)
            if parsed.entries and hasattr(parsed.entries[0], 'published_parsed'):
                return datetime(*parsed.entries[0].published_parsed[:6])
        except:
            pass

        return datetime.utcnow()

    async def _save_article(self, article_data: Dict) -> bool:
        """Save article to database with deduplication"""
        url = article_data['url']
        url_hash = hashlib.md5(url.encode()).hexdigest()

        if url_hash in self.seen_urls:
            return False

        async for db in get_db():
            try:
                # Check if exists
                result = await db.execute(
                    select(NewsArticle).where(NewsArticle.url == url)
                )
                if result.scalar_one_or_none():
                    self.seen_urls.add(url_hash)
                    return False

                # Analyze sentiment
                text = article_data['title'] + ' ' + (article_data.get('content') or '')
                sentiment = await self.sentiment_analyzer.analyze(text, article_data.get('related_pairs', []))

                article = NewsArticle(
                    title=article_data['title'],
                    content=article_data.get('content'),
                    summary=article_data.get('summary'),
                    url=url,
                    source=article_data['source'],
                    published_at=article_data['published_at'],
                    related_pairs=article_data.get('related_pairs', []),
                    impact_level=article_data.get('impact_level', NewsImpact.LOW),
                    categories=article_data.get('categories', []),
                    sentiment_score=sentiment['score'],
                    sentiment_label=sentiment['label'],
                    sentiment_confidence=sentiment['confidence'],
                    sentiment_details=sentiment['details'],
                )

                db.add(article)
                await db.commit()

                self.seen_urls.add(url_hash)
                return True

            except Exception as e:
                await db.rollback()
                logger.error("Failed to save article", url=url, error=str(e))
                return False

    async def get_latest_news(self, limit: int = 50, filters: Dict = None) -> List[Dict]:
        async for db in get_db():
            query = select(NewsArticle).order_by(NewsArticle.published_at.desc()).limit(limit)

            if filters:
                if filters.get('pairs'):
                    query = query.where(NewsArticle.related_pairs.overlap(filters['pairs']))
                if filters.get('impact_level'):
                    query = query.where(NewsArticle.impact_level.in_(filters['impact_level']))
                if filters.get('sentiment_label'):
                    query = query.where(NewsArticle.sentiment_label.in_(filters['sentiment_label']))
                if filters.get('start_date'):
                    query = query.where(NewsArticle.published_at >= filters['start_date'])
                if filters.get('end_date'):
                    query = query.where(NewsArticle.published_at <= filters['end_date'])

            result = await db.execute(query)
            articles = result.scalars().all()

            return [
                {
                    'id': str(a.id),
                    'title': a.title,
                    'summary': a.summary,
                    'url': a.url,
                    'source': a.source.value,
                    'published_at': a.published_at.isoformat(),
                    'related_pairs': a.related_pairs,
                    'impact_level': a.impact_level.value,
                    'categories': a.categories,
                    'sentiment_score': a.sentiment_score,
                    'sentiment_label': a.sentiment_label.value if a.sentiment_label else None,
                    'sentiment_confidence': a.sentiment_confidence,
                }
                for a in articles
            ]