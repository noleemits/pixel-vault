-- PixelVault Supabase (PostgreSQL) Schema
-- Run this in the Supabase SQL editor or via psql against your project database.
-- Requires pg_crypto extension (enabled by default in Supabase) for gen_random_uuid().

-- ---------------------------------------------------------------------------
-- Extensions
-- ---------------------------------------------------------------------------
create extension if not exists "pgcrypto";


-- ---------------------------------------------------------------------------
-- accounts
-- ---------------------------------------------------------------------------
create table if not exists accounts (
    id                  uuid primary key default gen_random_uuid(),
    email               text not null unique,
    name                text not null,
    plan                text not null default 'free',
    generations_used    int  not null default 0,
    generations_limit   int  not null default 3,
    sync_limit          int  not null default 50,
    stripe_customer_id  text,
    created_at          timestamptz not null default now()
);


-- ---------------------------------------------------------------------------
-- api_keys
-- ---------------------------------------------------------------------------
create table if not exists api_keys (
    id          uuid primary key default gen_random_uuid(),
    account_id  uuid not null references accounts(id) on delete cascade,
    key_hash    text not null unique,
    name        text not null,
    created_at  timestamptz not null default now(),
    last_used   timestamptz
);


-- ---------------------------------------------------------------------------
-- sites
-- ---------------------------------------------------------------------------
create table if not exists sites (
    id          uuid primary key default gen_random_uuid(),
    account_id  uuid not null references accounts(id) on delete cascade,
    name        text not null,
    url         text not null,
    api_key_id  uuid references api_keys(id) on delete set null,
    industry    text,
    serve_from  text not null default 'cdn',
    created_at  timestamptz not null default now()
);


-- ---------------------------------------------------------------------------
-- prompts
-- ---------------------------------------------------------------------------
create table if not exists prompts (
    id          serial primary key,
    industry    text not null,
    name        text not null,
    prompt_text text not null,
    use_case    text,
    ratios      text,
    created_at  timestamptz not null default now()
);


-- ---------------------------------------------------------------------------
-- batches
-- ---------------------------------------------------------------------------
create table if not exists batches (
    id           serial primary key,
    prompt_id    int  not null references prompts(id) on delete restrict,
    account_id   uuid references accounts(id) on delete set null,
    image_count  int  not null default 1,
    ratio        text not null,
    status       text not null default 'pending',
    model_used   text,
    created_at   timestamptz not null default now(),
    completed_at timestamptz
);


-- ---------------------------------------------------------------------------
-- images
-- ---------------------------------------------------------------------------
create table if not exists images (
    id                uuid primary key default gen_random_uuid(),
    canonical_name    text unique,
    filename          text not null,
    filepath          text not null,
    storage_key_web   text,
    cdn_url           text,
    industry          text not null,
    style             text not null,
    ratio             text not null,
    width             int,
    height            int,
    file_size         int,
    prompt_id         int  not null references prompts(id) on delete restrict,
    batch_id          int  not null references batches(id) on delete restrict,
    account_id        uuid references accounts(id) on delete set null,
    model_used        text,
    router_reason     text,
    cost_actual       float,
    status            text not null default 'pending',
    quality_score     float,
    usage_count       int  not null default 0,
    last_accessed     timestamptz,
    is_official       bool not null default false,
    is_community      bool not null default false,
    created_at        timestamptz not null default now()
);

create index if not exists idx_images_industry_style_ratio on images(industry, style, ratio);
create index if not exists idx_images_usage_count          on images(usage_count);


-- ---------------------------------------------------------------------------
-- image_deployments
-- ---------------------------------------------------------------------------
create table if not exists image_deployments (
    id              uuid primary key default gen_random_uuid(),
    image_id        uuid not null references images(id) on delete cascade,
    account_id      uuid not null references accounts(id) on delete cascade,
    site_id         uuid not null references sites(id) on delete cascade,
    local_filename  text,
    local_path      text,
    post_id         int,
    post_title      text,
    post_keywords   text[],
    serve_from      text not null default 'cdn',
    inserted_at     timestamptz not null default now(),
    is_active       bool not null default true
);

create index if not exists idx_image_deployments_image_account  on image_deployments(image_id, account_id);
create index if not exists idx_image_deployments_account_active on image_deployments(account_id, is_active);
