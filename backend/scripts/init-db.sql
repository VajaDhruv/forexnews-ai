-- Database initialization script for ForexNews AI
-- This script runs on first database creation

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable pg_trgm for text search
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Create indexes for better performance (will be created by SQLAlchemy, but here for reference)
-- These are created automatically by the models, but we can add custom ones here

-- Create a function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create a view for latest prices per pair
CREATE OR REPLACE VIEW latest_prices AS
SELECT DISTINCT ON (pair)
    pair,
    timestamp,
    bid,
    ask,
    (bid + ask) / 2 as mid,
    spread,
    high,
    low,
    close
FROM forex_prices
ORDER BY pair, timestamp DESC;

-- Create a view for active predictions
CREATE OR REPLACE VIEW active_predictions AS
SELECT
    p.*,
    n.title as news_title,
    n.source as news_source,
    n.published_at as news_published_at
FROM predictions p
JOIN news_articles n ON p.news_id = n.id
WHERE p.resolved_at IS NULL
  AND p.expires_at > NOW()
ORDER BY p.predicted_at DESC;

-- Create a view for prediction performance summary
CREATE OR REPLACE VIEW prediction_performance_summary AS
SELECT
    pair,
    horizon_minutes,
    direction,
    COUNT(*) as total_predictions,
    COUNT(CASE WHEN outcome = 'correct' THEN 1 END) as correct_predictions,
    COUNT(CASE WHEN outcome = 'incorrect' THEN 1 END) as incorrect_predictions,
    COUNT(CASE WHEN outcome = 'partial' THEN 1 END) as partial_predictions,
    AVG(confidence) as avg_confidence,
    AVG(profit_loss_pips) as avg_profit_loss_pips,
    SUM(profit_loss_pips) as total_profit_loss_pips,
    CASE
        WHEN COUNT(CASE WHEN outcome IN ('correct', 'incorrect') THEN 1 END) > 0
        THEN COUNT(CASE WHEN outcome = 'correct' THEN 1 END)::float /
             COUNT(CASE WHEN outcome IN ('correct', 'incorrect') THEN 1 END)::float
        ELSE NULL
    END as accuracy
FROM predictions
WHERE resolved_at IS NOT NULL
GROUP BY pair, horizon_minutes, direction
ORDER BY pair, horizon_minutes, direction;

-- Create a view for daily news sentiment
CREATE OR REPLACE VIEW daily_news_sentiment AS
SELECT
    DATE(published_at) as date,
    pair,
    COUNT(*) as article_count,
    AVG(sentiment_score) as avg_sentiment,
    COUNT(CASE WHEN sentiment_label IN ('bullish', 'very_bullish') THEN 1 END) as bullish_count,
    COUNT(CASE WHEN sentiment_label IN ('bearish', 'very_bearish') THEN 1 END) as bearish_count,
    COUNT(CASE WHEN sentiment_label = 'neutral' THEN 1 END) as neutral_count
FROM news_articles na,
LATERAL unnest(related_pairs) as pair
WHERE sentiment_score IS NOT NULL
  AND published_at > NOW() - INTERVAL '30 days'
GROUP BY DATE(published_at), pair
ORDER BY date DESC, pair;

-- Grant permissions (adjust as needed)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;
-- GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO postgres;