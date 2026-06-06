-- ═══════════════════════════════════════════════════════
--  Pastely — Schema Tambahan: Social Features
--  Jalankan di Supabase SQL Editor
-- ═══════════════════════════════════════════════════════

-- ── Tabel likes (bookmark paste) ──
CREATE TABLE IF NOT EXISTS paste_likes (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id    BIGINT NOT NULL REFERENCES pastely_users(id) ON DELETE CASCADE,
  paste_id   UUID NOT NULL REFERENCES snippets(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(user_id, paste_id)
);
CREATE INDEX IF NOT EXISTS idx_likes_paste_id ON paste_likes(paste_id);
CREATE INDEX IF NOT EXISTS idx_likes_user_id  ON paste_likes(user_id);
ALTER TABLE paste_likes ENABLE ROW LEVEL SECURITY;
CREATE POLICY "likes_all" ON paste_likes FOR ALL USING (true) WITH CHECK (true);

-- ── Tabel komentar ──
CREATE TABLE IF NOT EXISTS paste_comments (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  paste_id   UUID NOT NULL REFERENCES snippets(id) ON DELETE CASCADE,
  user_id    BIGINT NOT NULL REFERENCES pastely_users(id) ON DELETE CASCADE,
  content    TEXT NOT NULL CHECK (char_length(content) BETWEEN 1 AND 1000),
  created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_comments_paste_id  ON paste_comments(paste_id);
CREATE INDEX IF NOT EXISTS idx_comments_created_at ON paste_comments(created_at DESC);
ALTER TABLE paste_comments ENABLE ROW LEVEL SECURITY;
CREATE POLICY "comments_all" ON paste_comments FOR ALL USING (true) WITH CHECK (true);

-- ── Tabel follow user ──
CREATE TABLE IF NOT EXISTS user_follows (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  follower_id BIGINT NOT NULL REFERENCES pastely_users(id) ON DELETE CASCADE,
  following_id BIGINT NOT NULL REFERENCES pastely_users(id) ON DELETE CASCADE,
  created_at  TIMESTAMPTZ DEFAULT now(),
  UNIQUE(follower_id, following_id),
  CHECK (follower_id != following_id)
);
CREATE INDEX IF NOT EXISTS idx_follows_follower  ON user_follows(follower_id);
CREATE INDEX IF NOT EXISTS idx_follows_following ON user_follows(following_id);
ALTER TABLE user_follows ENABLE ROW LEVEL SECURITY;
CREATE POLICY "follows_all" ON user_follows FOR ALL USING (true) WITH CHECK (true);

-- ── Tambah kolom like_count ke snippets (cache) ──
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'snippets' AND column_name = 'like_count'
  ) THEN
    ALTER TABLE snippets ADD COLUMN like_count INTEGER DEFAULT 0;
  END IF;
END $$;
