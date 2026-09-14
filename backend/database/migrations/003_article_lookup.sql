-- Article lookup for the browser extension.
-- Article-level scores are optional. A missing row is not a zero.

CREATE INDEX IF NOT EXISTS idx_articles_url ON articles (url);

CREATE TABLE IF NOT EXISTS article_scores (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    article_id            UUID REFERENCES articles(id),
    url                   VARCHAR(1000) UNIQUE,
    methodology_version   VARCHAR(20) NOT NULL,
    pillar_1_score        DECIMAL(5,2),
    pillar_2_score        DECIMAL(5,2),
    composite_score       DECIMAL(5,2),
    dimensions            JSONB,
    note                  TEXT,
    scored_at             TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_article_scores_article ON article_scores (article_id);
