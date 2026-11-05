import asyncio
import yfinance as yf
import ccxt
import httpx
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
import structlog
import numpy as np
import pandas as pd

from app.config import settings
from app.db.session import get_db
from app.db.models import ForexPrice, NewsArticle, NewsImpact, SentimentLabel

logger = structlog.get_logger()


class ForexDataService:
    def __init__(self):
        self.running = False
        self.price_task = None
        self.client = httpx.AsyncClient(timeout=10.0)
        self.exchange = ccxt.kraken({'enableRateLimit': True})
        self.price_cache = {}
        self.last_update = {}

        # OANDA setup (for live streaming)
        self.oanda_token = settings.OANDA_API_KEY
        self.oanda_account = settings.OANDA_ACCOUNT_ID
        self.oanda_env = settings.OANDA_ENVIRONMENT
        self.oanda_base_url = (
            "https://api-fxtrade.oanda.com" if self.oanda_env == "live"
            else "https://api-fxpractice.oanda.com"
        )

    async def start_price_stream(self):
        self.running = True
        self.price_task = asyncio.create_task(self._price_stream_loop())
        logger.info("Forex price stream started")

    async def stop(self):
        self.running = False
        if self.price_task:
            self.price_task.cancel()
            try:
                await self.price_task
            except asyncio.CancelledError:
                pass
        await self.client.aclose()
        logger.info("Forex price stream stopped")

    async def _price_stream_loop(self):
        while self.running:
            try:
                await self.fetch_and_store_prices()
            except Exception as e:
                logger.error("Error in price stream loop", error=str(e))

            await asyncio.sleep(5)  # Update every 5 seconds

    async def fetch_and_store_prices(self):
        """Fetch prices from multiple sources and store"""
        tasks = []

        # Try OANDA first for live data
        if self.oanda_token and self.oanda_account:
            tasks.append(self._fetch_oanda_prices())

        # Fallback to CCXT (Kraken, etc.)
        tasks.append(self._fetch_ccxt_prices())

        # Fallback to yfinance
        tasks.append(self._fetch_yfinance_prices())

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results - use first successful source
        for result in results:
            if isinstance(result, dict) and result:
                await self._store_prices(result)
                break

    async def _fetch_oanda_prices(self) -> Dict[str, Dict]:
        """Fetch prices from OANDA streaming API"""
        if not self.oanda_token or not self.oanda_account:
            return {}

        headers = {
            'Authorization': f'Bearer {self.oanda_token}',
            'Content-Type': 'application/json'
        }

        instruments = ','.join([f"{p[:3]}_{p[3:]}" for p in settings.FOREX_PAIRS])
        url = f"{self.oanda_base_url}/v3/accounts/{self.oanda_account}/pricing"
        params = {'instruments': instruments}

        try:
            response = await self.client.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

            prices = {}
            for price_data in data.get('prices', []):
                instrument = price_data['instrument'].replace('_', '')
                if instrument in settings.FOREX_PAIRS:
                    bid = float(price_data['bids'][0]['price'])
                    ask = float(price_data['asks'][0]['price'])
                    prices[instrument] = {
                        'bid': bid,
                        'ask': ask,
                        'mid': (bid + ask) / 2,
                        'spread': ask - bid,
                        'timestamp': datetime.utcnow(),
                    }

            return prices

        except Exception as e:
            logger.warning("OANDA fetch failed", error=str(e))
            return {}

    async def _fetch_ccxt_prices(self) -> Dict[str, Dict]:
        """Fetch prices from CCXT exchanges"""
        prices = {}

        try:
            # Load markets
            await self.exchange.load_markets()

            for pair in settings.FOREX_PAIRS:
                symbol = f"{pair[:3]}/{pair[3:]}"
                try:
                    ticker = await self.exchange.fetch_ticker(symbol)
                    if ticker and ticker.get('last'):
                        prices[pair] = {
                            'bid': ticker.get('bid', ticker['last']),
                            'ask': ticker.get('ask', ticker['last']),
                            'mid': ticker['last'],
                            'spread': ticker.get('ask', ticker['last']) - ticker.get('bid', ticker['last']),
                            'timestamp': datetime.utcnow(),
                        }
                except Exception:
                    continue

        except Exception as e:
            logger.warning("CCXT fetch failed", error=str(e))

        return prices

    async def _fetch_yfinance_prices(self) -> Dict[str, Dict]:
        """Fetch prices from Yahoo Finance"""
        prices = {}

        try:
            # yfinance uses different format
            yf_pairs = [f"{p[:3]}{p[3:]}=X" for p in settings.FOREX_PAIRS]
            tickers = yf.Tickers(' '.join(yf_pairs))

            for pair, yf_symbol in zip(settings.FOREX_PAIRS, yf_pairs):
                try:
                    ticker = tickers.tickers[yf_symbol]
                    info = ticker.fast_info
                    if info and 'last_price' in info and info['last_price']:
                        price = float(info['last_price'])
                        prices[pair] = {
                            'bid': price * 0.9999,
                            'ask': price * 1.0001,
                            'mid': price,
                            'spread': price * 0.0002,
                            'timestamp': datetime.utcnow(),
                        }
                except Exception:
                    continue

        except Exception as e:
            logger.warning("YFinance fetch failed", error=str(e))

        return prices

    async def _store_prices(self, prices: Dict[str, Dict]):
        """Store prices in database with technical indicators"""
        async for db in get_db():
            try:
                for pair, data in prices.items():
                    mid = data['mid']

                    # Get recent prices for indicators
                    recent = await self._get_recent_prices(db, pair, 100)

                    # Calculate indicators
                    indicators = self._calculate_indicators(recent + [mid])

                    price = ForexPrice(
                        pair=pair,
                        timestamp=data['timestamp'],
                        open=mid,  # For tick data, open=close=mid
                        high=max(recent[-1] if recent else mid, mid),
                        low=min(recent[-1] if recent else mid, mid),
                        close=mid,
                        volume=0,  # Not available from most forex sources
                        bid=data.get('bid'),
                        ask=data.get('ask'),
                        spread=data.get('spread'),
                        **indicators
                    )

                    db.add(price)

                await db.commit()

                # Update cache
                for pair, data in prices.items():
                    self.price_cache[pair] = data
                    self.last_update[pair] = datetime.utcnow()

            except Exception as e:
                await db.rollback()
                logger.error("Failed to store prices", error=str(e))

    async def _get_recent_prices(self, db: AsyncSession, pair: str, limit: int) -> List[float]:
        result = await db.execute(
            select(ForexPrice.close)
            .where(ForexPrice.pair == pair)
            .order_by(desc(ForexPrice.timestamp))
            .limit(limit)
        )
        prices = [row[0] for row in result.fetchall()]
        return list(reversed(prices))  # Oldest first

    def _calculate_indicators(self, prices: List[float]) -> Dict[str, Optional[float]]:
        """Calculate technical indicators"""
        if len(prices) < 2:
            return {k: None for k in [
                'sma_20', 'sma_50', 'ema_12', 'ema_26', 'rsi_14',
                'macd', 'macd_signal', 'bollinger_upper', 'bollinger_lower', 'atr_14'
            ]}

        df = pd.Series(prices)
        indicators = {}

        # SMAs
        indicators['sma_20'] = float(df.rolling(20).mean().iloc[-1]) if len(df) >= 20 else None
        indicators['sma_50'] = float(df.rolling(50).mean().iloc[-1]) if len(df) >= 50 else None

        # EMAs
        indicators['ema_12'] = float(df.ewm(span=12).mean().iloc[-1]) if len(df) >= 12 else None
        indicators['ema_26'] = float(df.ewm(span=26).mean().iloc[-1]) if len(df) >= 26 else None

        # RSI
        if len(df) >= 14:
            delta = df.diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            indicators['rsi_14'] = float(rsi.iloc[-1])
        else:
            indicators['rsi_14'] = None

        # MACD
        if len(df) >= 26:
            ema12 = df.ewm(span=12).mean()
            ema26 = df.ewm(span=26).mean()
            macd = ema12 - ema26
            signal = macd.ewm(span=9).mean()
            indicators['macd'] = float(macd.iloc[-1])
            indicators['macd_signal'] = float(signal.iloc[-1])
        else:
            indicators['macd'] = None
            indicators['macd_signal'] = None

        # Bollinger Bands
        if len(df) >= 20:
            sma20 = df.rolling(20).mean()
            std20 = df.rolling(20).std()
            indicators['bollinger_upper'] = float((sma20 + 2 * std20).iloc[-1])
            indicators['bollinger_lower'] = float((sma20 - 2 * std20).iloc[-1])
        else:
            indicators['bollinger_upper'] = None
            indicators['bollinger_lower'] = None

        # ATR
        if len(df) >= 14:
            high = df.rolling(14).max()
            low = df.rolling(14).min()
            atr = (high - low).rolling(14).mean()
            indicators['atr_14'] = float(atr.iloc[-1])
        else:
            indicators['atr_14'] = None

        return indicators

    async def get_current_prices(self) -> List[Dict]:
        """Get current prices for all pairs"""
        result = []
        for pair in settings.FOREX_PAIRS:
            if pair in self.price_cache:
                data = self.price_cache[pair]
                # Calculate 24h change
                change_data = await self._get_24h_change(pair)

                result.append({
                    'pair': pair,
                    'bid': data['bid'],
                    'ask': data['ask'],
                    'spread': data['spread'],
                    'timestamp': data['timestamp'].isoformat(),
                    'change_24h': change_data['change'],
                    'change_24h_percent': change_data['change_percent'],
                    'high_24h': change_data['high'],
                    'low_24h': change_data['low'],
                })
        return result

    async def _get_24h_change(self, pair: str) -> Dict:
        async for db in get_db():
            # Get price 24h ago
            cutoff = datetime.utcnow() - timedelta(hours=24)
            result = await db.execute(
                select(ForexPrice.close)
                .where(and_(ForexPrice.pair == pair, ForexPrice.timestamp <= cutoff))
                .order_by(desc(ForexPrice.timestamp))
                .limit(1)
            )
            old_price = result.scalar_one_or_none()

            current = self.price_cache.get(pair, {}).get('mid', 0)

            if old_price and current:
                change = current - old_price
                change_percent = (change / old_price) * 100
            else:
                change = 0
                change_percent = 0

            # Get 24h high/low
            result = await db.execute(
                select(ForexPrice.high, ForexPrice.low)
                .where(and_(ForexPrice.pair == pair, ForexPrice.timestamp >= cutoff))
            )
            rows = result.fetchall()
            high = max([r[0] for r in rows]) if rows else current
            low = min([r[1] for r in rows]) if rows else current

            return {
                'change': change,
                'change_percent': change_percent,
                'high': high,
                'low': low,
            }

    async def get_price_history(self, pair: str, hours: int = 24, interval: str = '1m') -> List[Dict]:
        """Get historical price data"""
        cutoff = datetime.utcnow() - timedelta(hours=hours)

        async for db in get_db():
            result = await db.execute(
                select(ForexPrice)
                .where(and_(ForexPrice.pair == pair, ForexPrice.timestamp >= cutoff))
                .order_by(ForexPrice.timestamp)
            )
            prices = result.scalars().all()

            return [
                {
                    'timestamp': p.timestamp.isoformat(),
                    'open': p.open,
                    'high': p.high,
                    'low': p.low,
                    'close': p.close,
                    'volume': p.volume,
                }
                for p in prices
            ]

    async def get_latest_price(self, pair: str) -> Optional[Dict]:
        """Get latest price for a pair"""
        if pair in self.price_cache:
            data = self.price_cache[pair]
            return {
                'pair': pair,
                'bid': data['bid'],
                'ask': data['ask'],
                'mid': data['mid'],
                'spread': data['spread'],
                'timestamp': data['timestamp'].isoformat(),
            }
        return None