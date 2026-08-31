-- Allow articles to exist without full text.
-- access_level: full | excerpt | metadata

ALTER TABLE articles
    ALTER COLUMN body DROP NOT NULL;

ALTER TABLE articles
    ADD COLUMN IF NOT EXISTS access_level VARCHAR(20) NOT NULL DEFAULT 'full';

ALTER TABLE articles
    ADD COLUMN IF NOT EXISTS lede TEXT;

CREATE TABLE IF NOT EXISTS journalist_identities (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    journalist_id   UUID REFERENCES journalists(id) NOT NULL,
    outlet_slug     VARCHAR(255) NOT NULL,
    author_slug     VARCHAR(255),
    author_url      VARCHAR(1000),
    feed_url        VARCHAR(1000),
    guardian_tag    VARCHAR(255),
    start_date      DATE,
    end_date        DATE,
    source          VARCHAR(100),
    created_at      TIMESTAMP DEFAULT NOW(),
    UNIQUE (journalist_id, outlet_slug, author_slug)
);

CREATE INDEX IF NOT EXISTS idx_identities_journalist ON journalist_identities(journalist_id);
CREATE INDEX IF NOT EXISTS idx_articles_access ON articles(access_level);
