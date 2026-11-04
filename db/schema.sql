-- Klipr Phase 0 — Postgres schema
-- Spec data model, Oct 25 2026. Every row carries user_id (+ brand_id where it applies).
-- RLS ON at creation on every table. App sets, per session:
--   SET app.current_user_id = '<uuid>';  SET app.is_admin = 'true'|'false';
-- Policies below use those settings. Production OAuth (Supabase Auth / provider of
-- Matt's choice) must map its authenticated user into these settings — see app/auth.py.
-- This file is the authoritative schema for BOTH klipr (prod) and klipr_staging.
-- It is NOT a claim that Supabase, R2, or Redis are already running on the VPS.
-- VM proof uses local Postgres 16; VPS deploy script applies this same file.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Helper: current app user / admin flag, safe when not set.
CREATE OR REPLACE FUNCTION app_user_id() RETURNS uuid LANGUAGE sql STABLE AS $$
  SELECT NULLIF(current_setting('app.current_user_id', true), '')::uuid;
$$;
CREATE OR REPLACE FUNCTION app_is_admin() RETURNS boolean LANGUAGE sql STABLE AS $$
  SELECT COALESCE(current_setting('app.is_admin', true) = 'true', false);
$$;

CREATE TABLE IF NOT EXISTS users (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  oauth_identity text NOT NULL UNIQUE,
  role text NOT NULL DEFAULT 'user' CHECK (role IN ('admin','user')),
  plan text NOT NULL DEFAULT 'free',
  credit_balance integer NOT NULL DEFAULT 0,
  data_opt_ins jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS brands (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name text NOT NULL,
  sources jsonb NOT NULL DEFAULT '{}'::jsonb,
  brand_kit jsonb NOT NULL DEFAULT '{}'::jsonb,
  voice_guide jsonb NOT NULL DEFAULT '{}'::jsonb,
  business_facts jsonb NOT NULL DEFAULT '{}'::jsonb,
  default_avatar_id uuid, default_voice_id uuid,
  default_scenes jsonb NOT NULL DEFAULT '[]'::jsonb,
  default_cta text,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS social_connections (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  brand_id uuid REFERENCES brands(id) ON DELETE CASCADE,
  platform text NOT NULL, oauth_token_ref text, verified_owner boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS memories (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  brand_id uuid REFERENCES brands(id) ON DELETE CASCADE,
  fact text NOT NULL, source_thread text, editable boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS style_profile_rules (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  brand_id uuid REFERENCES brands(id) ON DELETE CASCADE,
  rule_text text NOT NULL, source_feedback_ids uuid[] NOT NULL DEFAULT '{}',
  pinned boolean NOT NULL DEFAULT false, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS threads (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  brand_id uuid REFERENCES brands(id) ON DELETE CASCADE,
  messages jsonb NOT NULL DEFAULT '[]'::jsonb,
  status text NOT NULL DEFAULT 'in_progress' CHECK (status IN ('in_progress','finished')),
  linked_project_id uuid, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS briefs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  thread_id uuid REFERENCES threads(id) ON DELETE SET NULL,
  fields jsonb NOT NULL DEFAULT '{}'::jsonb,
  version integer NOT NULL DEFAULT 1, approved_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS consent_records (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  selfie_video_ref text, spoken_phrase_audio_ref text, liveness_result jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS avatars (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  consent_record_id uuid REFERENCES consent_records(id) ON DELETE SET NULL,
  source_video_ref text, provider_model_id text, preview_ref text,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS voices (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  avatar_id uuid REFERENCES avatars(id) ON DELETE SET NULL,
  consent_record_id uuid REFERENCES consent_records(id) ON DELETE SET NULL,
  voicebox_model_id text, sample_clip_ref text,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS scenes (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES users(id) ON DELETE CASCADE,
  category text, stills_or_clips jsonb NOT NULL DEFAULT '[]'::jsonb,
  linked_ambiance text, tags text[] NOT NULL DEFAULT '{}',
  visibility text NOT NULL DEFAULT 'private' CHECK (visibility IN ('private','community')),
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS assets (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  brand_id uuid REFERENCES brands(id) ON DELETE CASCADE,
  type text NOT NULL, storage_path text NOT NULL, description text,
  shot_tags jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS audio_tracks (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES users(id) ON DELETE CASCADE,
  type text, mood text, bpm integer, license text,
  storage_path text, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS templates (
  id text PRIMARY KEY,
  user_id uuid REFERENCES users(id) ON DELETE CASCADE,
  content_type text NOT NULL, version integer NOT NULL DEFAULT 1,
  remix_of_id text REFERENCES templates(id) ON DELETE SET NULL,
  recipe jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS reference_videos (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  template_id text NOT NULL REFERENCES templates(id) ON DELETE CASCADE,
  source text, trait_breakdown jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS projects (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  brand_id uuid REFERENCES brands(id) ON DELETE CASCADE,
  brief_id uuid REFERENCES briefs(id) ON DELETE SET NULL,
  template_id text REFERENCES templates(id) ON DELETE SET NULL,
  input_assets uuid[] NOT NULL DEFAULT '{}',
  edl jsonb NOT NULL DEFAULT '{}'::jsonb,
  render_status text NOT NULL DEFAULT 'draft',
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS renders (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  project_id uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  aspect_ratio text NOT NULL DEFAULT '9:16', file_path text,
  credits_spent integer NOT NULL DEFAULT 0, cost_cents integer NOT NULL DEFAULT 0,
  time_to_render_sec integer, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS feedback (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  target_type text NOT NULL, target_id uuid,
  loop text NOT NULL CHECK (loop IN ('style','quality','app')),
  rating integer, tags text[] NOT NULL DEFAULT '{}', notes text, video_timestamp numeric,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS posts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  project_id uuid REFERENCES projects(id) ON DELETE SET NULL,
  visibility text NOT NULL DEFAULT 'private' CHECK (visibility IN ('private','community')),
  likes integer NOT NULL DEFAULT 0, upvotes integer NOT NULL DEFAULT 0,
  comments jsonb NOT NULL DEFAULT '[]'::jsonb, remix_count integer NOT NULL DEFAULT 0,
  contest_id uuid, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS subscriptions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  followed_user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS contests (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  theme text, rules text, starts_at timestamptz, ends_at timestamptz,
  prize text, winners jsonb NOT NULL DEFAULT '[]'::jsonb
);
CREATE TABLE IF NOT EXISTS credit_ledger (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  amount integer NOT NULL, reason text NOT NULL, job_id uuid,
  created_at timestamptz NOT NULL DEFAULT now()
);
-- Job queue (Phase 0): every analyze/b-roll/avatar/render step is a job.
CREATE TABLE IF NOT EXISTS jobs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  brand_id uuid REFERENCES brands(id) ON DELETE CASCADE,
  project_id uuid REFERENCES projects(id) ON DELETE SET NULL,
  kind text NOT NULL, payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  status text NOT NULL DEFAULT 'queued' CHECK (status IN ('queued','running','done','failed')),
  attempts integer NOT NULL DEFAULT 0, max_attempts integer NOT NULL DEFAULT 3,
  credit_cost integer NOT NULL DEFAULT 0, error text,
  created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now()
);
-- Backfill brand default FKs now that avatars/voices exist (no-op if already set).
-- RLS: enable on every table, then policies.
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE brands ENABLE ROW LEVEL SECURITY;
ALTER TABLE social_connections ENABLE ROW LEVEL SECURITY;
ALTER TABLE memories ENABLE ROW LEVEL SECURITY;
ALTER TABLE style_profile_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE threads ENABLE ROW LEVEL SECURITY;
ALTER TABLE briefs ENABLE ROW LEVEL SECURITY;
ALTER TABLE consent_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE avatars ENABLE ROW LEVEL SECURITY;
ALTER TABLE voices ENABLE ROW LEVEL SECURITY;
ALTER TABLE scenes ENABLE ROW LEVEL SECURITY;
ALTER TABLE assets ENABLE ROW LEVEL SECURITY;
ALTER TABLE audio_tracks ENABLE ROW LEVEL SECURITY;
ALTER TABLE templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE reference_videos ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE renders ENABLE ROW LEVEL SECURITY;
ALTER TABLE feedback ENABLE ROW LEVEL SECURITY;
ALTER TABLE posts ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE contests ENABLE ROW LEVEL SECURITY;
ALTER TABLE credit_ledger ENABLE ROW LEVEL SECURITY;
ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;

-- Policies: admin sees all; owner sees own rows. Tables without user_id are handled below.
-- Drop-if-exists first so re-applying this file is idempotent for policies.
DO $$ DECLARE t text; BEGIN
  FOR t IN SELECT unnest(ARRAY['brands','social_connections','memories','style_profile_rules','threads','briefs','consent_records','avatars','voices','assets','projects','renders','feedback','posts','subscriptions','credit_ledger','jobs']) LOOP
    EXECUTE format('DROP POLICY IF EXISTS owner_or_admin ON %I', t);
    EXECUTE format('CREATE POLICY owner_or_admin ON %I USING (app_is_admin() OR user_id = app_user_id()) WITH CHECK (app_is_admin() OR user_id = app_user_id())', t);
  END LOOP;
END $$;
-- users table: a user can also read their own row (user_id is id here, handled above
-- would fail because users has no user_id column) — replace with id-based policy.
DROP POLICY IF EXISTS owner_or_admin ON users;
CREATE POLICY owner_or_admin ON users USING (app_is_admin() OR id = app_user_id()) WITH CHECK (app_is_admin() OR id = app_user_id());
-- scenes: owner, admin, or community-visible rows are readable by any authenticated user.
DROP POLICY IF EXISTS owner_or_admin ON scenes;
CREATE POLICY owner_or_admin ON scenes USING (app_is_admin() OR user_id = app_user_id() OR visibility = 'community') WITH CHECK (app_is_admin() OR user_id = app_user_id());
-- audio_tracks: system tracks have NULL user_id and are readable by all authenticated users.
DROP POLICY IF EXISTS owner_or_admin ON audio_tracks;
CREATE POLICY owner_or_admin ON audio_tracks USING (app_is_admin() OR user_id IS NULL OR user_id = app_user_id()) WITH CHECK (app_is_admin() OR user_id IS NULL OR user_id = app_user_id());
-- templates: system templates have NULL user_id; user templates are owner/admin only for write, readable if system/community.
DROP POLICY IF EXISTS owner_or_admin ON templates;
CREATE POLICY owner_or_admin ON templates USING (app_is_admin() OR user_id IS NULL OR user_id = app_user_id()) WITH CHECK (app_is_admin() OR user_id IS NULL OR user_id = app_user_id());
-- reference_videos: admin-only (spec: admin only library).
DROP POLICY IF EXISTS owner_or_admin ON reference_videos;
CREATE POLICY owner_or_admin ON reference_videos USING (app_is_admin()) WITH CHECK (app_is_admin());
-- posts: community posts readable by authenticated users; private only owner/admin.
DROP POLICY IF EXISTS owner_or_admin ON posts;
CREATE POLICY owner_or_admin ON posts USING (app_is_admin() OR user_id = app_user_id() OR visibility = 'community') WITH CHECK (app_is_admin() OR user_id = app_user_id());
-- contests: readable by all authenticated users, writable by admin only.
DROP POLICY IF EXISTS owner_or_admin ON contests;
CREATE POLICY owner_or_admin ON contests USING (true) WITH CHECK (app_is_admin());
