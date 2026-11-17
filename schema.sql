-- Majedwali ya msingi. Yanaweza kuendeshwa mara nyingi bila madhara.

CREATE TABLE IF NOT EXISTS users (
    id            BIGSERIAL PRIMARY KEY,
    username      TEXT UNIQUE NOT NULL,
    display_name  TEXT NOT NULL DEFAULT '',
    email         TEXT UNIQUE,
    phone         TEXT UNIQUE,
    google_id     TEXT UNIQUE,
    password_hash TEXT,
    avatar_url    TEXT,
    birth_date    DATE,
    is_verified   BOOLEAN NOT NULL DEFAULT FALSE,
    is_admin      BOOLEAN NOT NULL DEFAULT FALSE,
    is_banned     BOOLEAN NOT NULL DEFAULT FALSE,
    age_confirmed_at TIMESTAMPTZ,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- Kwa database iliyotengenezwa hatua ya 1
ALTER TABLE users ADD COLUMN IF NOT EXISTS age_confirmed_at TIMESTAMPTZ;

-- Salio la coin la kila mtumiaji
CREATE TABLE IF NOT EXISTS wallets (
    user_id    BIGINT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    balance    BIGINT NOT NULL DEFAULT 0 CHECK (balance >= 0),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Kila mabadiliko ya coin yanaandikwa hapa (hayafutwi)
CREATE TABLE IF NOT EXISTS transactions (
    id         BIGSERIAL PRIMARY KEY,
    user_id    BIGINT NOT NULL REFERENCES users(id),
    kind       TEXT NOT NULL,          -- buy | withdraw | tip_purchase | tip_sale | market | bonus
    amount     BIGINT NOT NULL,        -- chanya = ameongezewa, hasi = amekatwa
    note       TEXT,
    status     TEXT NOT NULL DEFAULT 'done',   -- pending | done | failed
    idem_key   TEXT,                           -- kinazuia ombi moja kutekelezwa mara mbili
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- Kwa database iliyotengenezwa kabla ya hatua ya 3
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS idem_key TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS ux_tx_idem ON transactions(idem_key);
CREATE INDEX IF NOT EXISTS idx_tx_user ON transactions(user_id, created_at DESC);

-- Jamvi la mikeka
CREATE TABLE IF NOT EXISTS tips (
    id          BIGSERIAL PRIMARY KEY,
    user_id     BIGINT NOT NULL REFERENCES users(id),
    title       TEXT NOT NULL,                   -- mchezo, mfano "Simba vs Yanga"
    league      TEXT NOT NULL DEFAULT '',
    pick        TEXT NOT NULL DEFAULT '',        -- mkeka wenyewe (unafichwa kama umefungwa)
    body        TEXT,                            -- maelezo ya ziada (yanafichwa pamoja na mkeka)
    odds        NUMERIC(8,2),
    price       BIGINT NOT NULL DEFAULT 0,       -- 0 = bure
    status      TEXT NOT NULL DEFAULT 'open',    -- open | won | lost | void
    image_url   TEXT,
    starts_at   TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- Kwa database iliyotengenezwa kabla ya hatua ya 4
ALTER TABLE tips ADD COLUMN IF NOT EXISTS league TEXT NOT NULL DEFAULT '';
ALTER TABLE tips ADD COLUMN IF NOT EXISTS pick TEXT NOT NULL DEFAULT '';
CREATE INDEX IF NOT EXISTS idx_tips_created ON tips(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_tips_user ON tips(user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS tip_likes (
    tip_id     BIGINT NOT NULL REFERENCES tips(id) ON DELETE CASCADE,
    user_id    BIGINT NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (tip_id, user_id)
);

CREATE TABLE IF NOT EXISTS tip_purchases (
    tip_id     BIGINT NOT NULL REFERENCES tips(id) ON DELETE CASCADE,
    user_id    BIGINT NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (tip_id, user_id)
);

CREATE TABLE IF NOT EXISTS comments (
    id         BIGSERIAL PRIMARY KEY,
    tip_id     BIGINT NOT NULL REFERENCES tips(id) ON DELETE CASCADE,
    user_id    BIGINT NOT NULL REFERENCES users(id),
    body       TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_comments_tip ON comments(tip_id, created_at);

-- Market
CREATE TABLE IF NOT EXISTS products (
    id          BIGSERIAL PRIMARY KEY,
    seller_id   BIGINT NOT NULL REFERENCES users(id),
    title       TEXT NOT NULL,
    description TEXT,
    category    TEXT NOT NULL,
    price       BIGINT NOT NULL CHECK (price >= 0),
    location    TEXT,
    status      TEXT NOT NULL DEFAULT 'active',  -- active | sold | hidden
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_products_cat ON products(category, created_at DESC);

CREATE TABLE IF NOT EXISTS product_images (
    id         BIGSERIAL PRIMARY KEY,
    product_id BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    url        TEXT NOT NULL,
    position   INT NOT NULL DEFAULT 0
);
