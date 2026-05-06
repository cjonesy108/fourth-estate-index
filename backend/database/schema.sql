-- Fourth Estate Index — Database Schema
-- Version 1.0

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ─────────────────────────────────────────────
-- Core tables
-- ─────────────────────────────────────────────

CREATE TABLE journalists (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    full_name       VARCHAR(255) NOT NULL,
    slug            VARCHAR(255) UNIQUE NOT NULL,
    primary_outlet  VARCHAR(255),
    beat            VARCHAR(255),
    x_handle        VARCHAR(100),
    guardian_tag    VARCHAR(255),  -- e.g. profile/firstname-lastname
    data_status     VARCHAR(50) DEFAULT 'collecting',  -- collecting | insufficient | scored
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

CREATE TABLE publications (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(255) NOT NULL,
    domain          VARCHAR(255) UNIQUE NOT NULL,
    corrections_url VARCHAR(500),
    api_source      VARCHAR(50),  -- guardian | factiva | lexisnexis | scraper
    created_at      TIMESTAMP DEFAULT NOW()
);

-- ─────────────────────────────────────────────
-- Content tables
-- ─────────────────────────────────────────────

CREATE TABLE articles (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    journalist_id   UUID REFERENCES journalists(id),
    publication_id  UUID REFERENCES publications(id),
    headline        VARCHAR(1000) NOT NULL,
    subheadline     VARCHAR(1000),
    body            TEXT NOT NULL,
    url             VARCHAR(1000),
    published_at    TIMESTAMP NOT NULL,
    section         VARCHAR(255),
    word_count      INTEGER,
    source_api      VARCHAR(50),
    guardian_id     VARCHAR(500) UNIQUE,  -- guardian's internal content id
    ingested_at     TIMESTAMP DEFAULT NOW()
);

CREATE TABLE social_posts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    journalist_id   UUID REFERENCES journalists(id),
    platform        VARCHAR(50) NOT NULL,
    post_id         VARCHAR(255) UNIQUE,
    content         TEXT NOT NULL,
    is_reply        BOOLEAN DEFAULT FALSE,
    is_quote        BOOLEAN DEFAULT FALSE,
    posted_at       TIMESTAMP NOT NULL,
    ingested_at     TIMESTAMP DEFAULT NOW()
);

CREATE TABLE corrections (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    journalist_id           UUID REFERENCES journalists(id),
    article_id              UUID REFERENCES articles(id),
    publication_id          UUID REFERENCES publications(id),
    correction_text         TEXT NOT NULL,
    correction_type         VARCHAR(50),  -- factual | clarification | attribution | omission
    original_published_at   TIMESTAMP,
    corrected_at            TIMESTAMP,
    days_to_correction      INTEGER,
    correction_url          VARCHAR(1000),
    ingested_at             TIMESTAMP DEFAULT NOW()
);

-- ─────────────────────────────────────────────
-- Financial disclosure
-- ─────────────────────────────────────────────

CREATE TABLE fec_records (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    journalist_id       UUID REFERENCES journalists(id),
    contributor_name    VARCHAR(255),
    recipient_name      VARCHAR(255),
    recipient_type      VARCHAR(50),  -- candidate | pac | party
    amount              DECIMAL(10,2),
    contribution_date   DATE,
    fec_record_id       VARCHAR(255) UNIQUE,
    confidence          VARCHAR(20) DEFAULT 'manual',  -- auto | manual
    verified_at         TIMESTAMP DEFAULT NOW()
);

-- ─────────────────────────────────────────────
-- Analysis & scoring
-- ─────────────────────────────────────────────

CREATE TABLE analysis_results (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    journalist_id       UUID REFERENCES journalists(id),
    analysis_type       VARCHAR(100) NOT NULL,
    methodology_version VARCHAR(20) NOT NULL,
    corpus_size         INTEGER NOT NULL,
    corpus_start_date   TIMESTAMP,
    corpus_end_date     TIMESTAMP,
    raw_output          JSONB NOT NULL,
    model_id            VARCHAR(100),  -- claude model used
    prompt_version      VARCHAR(20),
    scored_at           TIMESTAMP DEFAULT NOW()
);

CREATE TABLE pillar_scores (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    journalist_id       UUID REFERENCES journalists(id),
    methodology_version VARCHAR(20) NOT NULL,
    pillar_1_score      DECIMAL(5,2),  -- seek truth and report it
    pillar_2_score      DECIMAL(5,2),  -- minimize harm
    pillar_3_score      DECIMAL(5,2),  -- act independently
    pillar_4_score      DECIMAL(5,2),  -- be accountable and transparent
    composite_score     DECIMAL(5,2),
    corpus_size         INTEGER,
    -- per-dimension sufficiency flags
    dimensions_scored   JSONB,         -- {"headline_fidelity": true, "attribution": false, ...}
    scored_at           TIMESTAMP DEFAULT NOW(),
    published_at        TIMESTAMP
);

CREATE TABLE citations (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_result_id  UUID REFERENCES analysis_results(id),
    article_id          UUID REFERENCES articles(id),
    social_post_id      UUID REFERENCES social_posts(id),
    cited_text          TEXT NOT NULL,
    dimension           VARCHAR(100) NOT NULL,
    flag_type           VARCHAR(100),
    flag_value          DECIMAL(5,2),
    created_at          TIMESTAMP DEFAULT NOW(),
    -- integrity check: cited_text must exist verbatim in article or post body
    CONSTRAINT citation_has_source CHECK (
        article_id IS NOT NULL OR social_post_id IS NOT NULL
    )
);

-- ─────────────────────────────────────────────
-- Appeals & context
-- ─────────────────────────────────────────────

CREATE TABLE appeals (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    journalist_id   UUID REFERENCES journalists(id),
    dimension       VARCHAR(100),
    submission_text TEXT NOT NULL,
    submitted_at    TIMESTAMP DEFAULT NOW(),
    reviewed_at     TIMESTAMP,
    outcome         VARCHAR(50),  -- error_confirmed | error_rejected | context_noted
    outcome_notes   TEXT,
    published       BOOLEAN DEFAULT FALSE
);

-- ─────────────────────────────────────────────
-- Methodology versioning
-- ─────────────────────────────────────────────

CREATE TABLE methodology_versions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version         VARCHAR(20) UNIQUE NOT NULL,
    published_at    TIMESTAMP NOT NULL,
    changelog       TEXT,
    scoring_matrix  JSONB NOT NULL,
    prompts         JSONB NOT NULL
);

-- ─────────────────────────────────────────────
-- Indexes
-- ─────────────────────────────────────────────

CREATE INDEX idx_articles_journalist ON articles(journalist_id);
CREATE INDEX idx_articles_published  ON articles(published_at);
CREATE INDEX idx_social_journalist   ON social_posts(journalist_id);
CREATE INDEX idx_citations_analysis  ON citations(analysis_result_id);
CREATE INDEX idx_pillar_journalist   ON pillar_scores(journalist_id);
CREATE INDEX idx_fec_journalist      ON fec_records(journalist_id);
