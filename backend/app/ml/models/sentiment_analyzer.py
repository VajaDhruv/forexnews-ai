import asyncio
import torch
import numpy as np
from typing import Dict, List, Any, Optional
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from sentence_transformers import SentenceTransformer
import structlog
import os

from app.config import settings

logger = structlog.get_logger()


class SentimentAnalyzer:
    def __init__(self):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.tokenizer = None
        self.model = None
        self.embedding_model = None
        self.loaded = False

        # FinBERT labels
        self.labels = ['negative', 'neutral', 'positive']
        self.label_map = {
            'negative': 'bearish',
            'neutral': 'neutral',
            'positive': 'bullish'
        }

        # Forex-specific keywords for enhancement
        self.bullish_keywords = {
            'strong', 'growth', 'increase', 'rise', 'gain', 'bullish', 'optimistic',
            'positive', 'beat', 'exceed', 'above', 'higher', 'up', 'rally', 'surge',
            'boom', 'expansion', 'recovery', 'improve', 'better', 'stronger', 'robust',
            'hawkish', 'tighten', 'hike', 'raise', 'upgrade', 'outperform'
        }

        self.bearish_keywords = {
            'weak', 'decline', 'fall', 'drop', 'loss', 'bearish', 'pessimistic',
            'negative', 'miss', 'below', 'lower', 'down', 'crash', 'plunge', 'slump',
            'recession', 'contraction', 'deteriorate', 'worse', 'weaker', 'fragile',
            'dovish', 'ease', 'cut', 'lower', 'downgrade', 'underperform'
        }

        # Currency-specific keywords
        self.currency_keywords = {
            'USD': {'fed', 'fomc', 'dollar', 'greenback', 'usd', 'united states', 'america', 'powell', 'yellen'},
            'EUR': {'ecb', 'euro', 'eur', 'europe', 'european', 'lagarde', 'draghi', 'eurozone', 'eu'},
            'GBP': {'boe', 'pound', 'gbp', 'sterling', 'uk', 'britain', 'bailey', 'england'},
            'JPY': {'boj', 'yen', 'jpy', 'japan', 'kuroda', 'ueda', 'tokyo'},
            'CHF': {'snb', 'franc', 'chf', 'swiss', 'switzerland', 'jordan'},
            'AUD': {'rba', 'aussie', 'aud', 'australia', 'lowe', 'bullock', 'sydney'},
            'CAD': {'boc', 'loonie', 'cad', 'canada', 'macklem', 'ottawa'},
            'NZD': {'rbnz', 'kiwi', 'nzd', 'new zealand', 'orr', 'wellington'},
        }

    async def load_model(self):
        """Load FinBERT and embedding models"""
        if self.loaded:
            return

        logger.info("Loading sentiment models...", device=str(self.device))

        try:
            # Load FinBERT for financial sentiment
            model_name = settings.SENTIMENT_MODEL
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
            self.model.to(self.device)
            self.model.eval()

            # Load embedding model for similarity
            self.embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL, device=self.device)

            self.loaded = True
            logger.info("Sentiment models loaded successfully")

        except Exception as e:
            logger.error("Failed to load sentiment models", error=str(e))
            raise

    async def analyze(self, text: str, related_pairs: List[str] = None) -> Dict[str, Any]:
        """Analyze sentiment of text with forex context"""
        if not self.loaded:
            await self.load_model()

        if not text or not text.strip():
            return self._neutral_result()

        # Get FinBERT prediction
        finbert_result = await self._finbert_analyze(text)

        # Get keyword-based sentiment
        keyword_result = self._keyword_analyze(text, related_pairs)

        # Get currency-specific sentiment
        currency_result = self._currency_analyze(text, related_pairs)

        # Combine results with weights
        combined = self._combine_sentiments(finbert_result, keyword_result, currency_result)

        # Generate embedding
        embedding = await self.get_embedding(text)

        return {
            'score': combined['score'],  # -1 to 1
            'label': combined['label'],  # SentimentLabel enum value
            'confidence': combined['confidence'],
            'details': {
                'finbert': finbert_result,
                'keywords': keyword_result,
                'currency_specific': currency_result,
                'embedding': embedding.tolist() if embedding is not None else None,
            }
        }

    async def _finbert_analyze(self, text: str) -> Dict:
        """Run FinBERT inference"""
        # Truncate text to max length
        max_length = 512
        inputs = self.tokenizer(
            text,
            return_tensors='pt',
            truncation=True,
            max_length=max_length,
            padding=True
        )
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self.model(**inputs)
            probs = torch.softmax(outputs.logits, dim=-1)
            probs = probs.cpu().numpy()[0]

        # Map to -1 to 1 scale
        # negative=0, neutral=1, positive=2
        score = probs[2] - probs[0]  # positive - negative
        confidence = float(probs.max())
        label_idx = probs.argmax()
        label = self.labels[label_idx]

        return {
            'score': float(score),
            'label': self.label_map[label],
            'confidence': confidence,
            'probs': {self.labels[i]: float(probs[i]) for i in range(3)}
        }

    def _keyword_analyze(self, text: str, related_pairs: List[str] = None) -> Dict:
        """Keyword-based sentiment analysis"""
        text_lower = text.lower()
        words = set(text_lower.split())

        bullish_count = len(words & self.bullish_keywords)
        bearish_count = len(words & self.bearish_keywords)
        total = bullish_count + bearish_count

        if total == 0:
            return {'score': 0.0, 'label': 'neutral', 'confidence': 0.1}

        score = (bullish_count - bearish_count) / total
        confidence = min(total / 10, 1.0)  # More keywords = higher confidence

        if score > 0.2:
            label = 'bullish'
        elif score < -0.2:
            label = 'bearish'
        else:
            label = 'neutral'

        return {
            'score': score,
            'label': label,
            'confidence': confidence,
            'bullish_keywords': list(words & self.bullish_keywords),
            'bearish_keywords': list(words & self.bearish_keywords)
        }

    def _currency_analyze(self, text: str, related_pairs: List[str] = None) -> Dict:
        """Currency-specific sentiment analysis"""
        text_lower = text.lower()
        words = set(text_lower.split())

        results = {}

        if related_pairs:
            for pair in related_pairs:
                base = pair[:3]
                quote = pair[3:]

                base_keywords = self.currency_keywords.get(base, set())
                quote_keywords = self.currency_keywords.get(quote, set())

                base_mentions = len(words & base_keywords)
                quote_mentions = len(words & quote_keywords)

                if base_mentions > 0 or quote_mentions > 0:
                    # Determine sentiment for this pair
                    pair_bullish = len(words & self.bullish_keywords)
                    pair_bearish = len(words & self.bearish_keywords)
                    pair_total = pair_bullish + pair_bearish

                    if pair_total > 0:
                        pair_score = (pair_bullish - pair_bearish) / pair_total
                    else:
                        pair_score = 0

                    results[pair] = {
                        'score': pair_score,
                        'base_mentions': base_mentions,
                        'quote_mentions': quote_mentions,
                        'bullish': pair_bullish,
                        'bearish': pair_bearish
                    }

        return results

    def _combine_sentiments(self, finbert: Dict, keyword: Dict, currency: Dict) -> Dict:
        """Combine multiple sentiment signals"""
        # Weights for different signals
        w_finbert = 0.5
        w_keyword = 0.3
        w_currency = 0.2

        # Combined score
        score = (
            w_finbert * finbert['score'] +
            w_keyword * keyword['score']
        )

        # Add currency-specific adjustments
        if currency:
            currency_scores = [v['score'] for v in currency.values() if v['score'] != 0]
            if currency_scores:
                score = (1 - w_currency) * score + w_currency * np.mean(currency_scores)

        # Clamp score
        score = max(-1, min(1, score))

        # Determine label
        if score > 0.4:
            label = 'very_bullish'
        elif score > 0.1:
            label = 'bullish'
        elif score < -0.4:
            label = 'very_bearish'
        elif score < -0.1:
            label = 'bearish'
        else:
            label = 'neutral'

        # Combined confidence
        confidence = (
            w_finbert * finbert['confidence'] +
            w_keyword * keyword['confidence']
        )

        if currency:
            currency_conf = np.mean([v.get('confidence', 0.5) for v in currency.values()]) if currency else 0.5
            confidence = (1 - w_currency) * confidence + w_currency * currency_conf

        return {
            'score': float(score),
            'label': label,
            'confidence': float(confidence)
        }

    async def get_embedding(self, text: str) -> Optional[np.ndarray]:
        """Get sentence embedding"""
        if not self.loaded:
            await self.load_model()

        try:
            embedding = self.embedding_model.encode(text, convert_to_numpy=True)
            return embedding
        except Exception as e:
            logger.error("Failed to generate embedding", error=str(e))
            return None

    def _neutral_result(self) -> Dict:
        return {
            'score': 0.0,
            'label': 'neutral',
            'confidence': 0.0,
            'details': {
                'finbert': {'score': 0.0, 'label': 'neutral', 'confidence': 0.0},
                'keywords': {'score': 0.0, 'label': 'neutral', 'confidence': 0.0},
                'currency_specific': {},
                'embedding': None
            }
        }

    async def get_latest_sentiment(self) -> Dict:
        """Get latest aggregate sentiment for all pairs"""
        # This would query the database for recent sentiment
        # For now return empty structure
        return {
            'pairs': {},
            'overall': {'score': 0.0, 'label': 'neutral'},
            'timestamp': asyncio.get_event_loop().time()
        }

    async def find_similar_news(self, text: str, limit: int = 10) -> List[Dict]:
        """Find similar news using embeddings"""
        # This would search the database for similar embeddings
        # Placeholder for vector search implementation
        return []