-- ═══════════════════════════════════════════════════════
--  Pastely — Schema (jalankan di Supabase SQL Editor)
--  Asumsi: tabel users sudah ada dengan id BIGINT
-- ═══════════════════════════════════════════════════════

-- Tambah kolom pin_hash ke tabel users jika belum ada
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'users' AND column_name = 'pin_hash'
  ) THEN
    ALTER TABLE users ADD COLUMN pin_hash TEXT;
  END IF;
END $$;

-- Buat tabel snippets dengan user_id BIGINT (sesuai users.id)
CREATE TABLE IF NOT EXISTS snippets (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  slug            VARCHAR(6) UNIQUE NOT NULL,
  title           TEXT,
  content         TEXT NOT NULL,
  paste_type      VARCHAR(10) NOT NULL CHECK (paste_type IN ('text', 'code', 'link')),
  language        VARCHAR(50),
  visibility      VARCHAR(10) NOT NULL DEFAULT 'public' CHECK (visibility IN ('public', 'unlisted', 'private')),
  password_hash   TEXT,
  expires_at      TIMESTAMPTZ,
  burn_after_read BOOLEAN DEFAULT false,
  view_count      INTEGER DEFAULT 0,
  user_id         BIGINT REFERENCES users(id) ON DELETE SET NULL,
  created_at      TIMESTAMPTZ DEFAULT now()
);

-- Index
CREATE INDEX IF NOT EXISTS idx_snippets_slug       ON snippets(slug);
CREATE INDEX IF NOT EXISTS idx_snippets_user_id    ON snippets(user_id);
CREATE INDEX IF NOT EXISTS idx_snippets_visibility ON snippets(visibility);
CREATE INDEX IF NOT EXISTS idx_snippets_created_at ON snippets(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_snippets_expires_at ON snippets(expires_at);

-- RLS snippets
ALTER TABLE snippets ENABLE ROW LEVEL SECURITY;

DO $$
DECLARE pol TEXT;
BEGIN
  FOR pol IN SELECT policyname FROM pg_policies WHERE tablename = 'snippets'
  LOOP EXECUTE 'DROP POLICY IF EXISTS "' || pol || '" ON snippets'; END LOOP;
END $$;

CREATE POLICY "snippets_select_all" ON snippets FOR SELECT USING (true);
CREATE POLICY "snippets_insert_all" ON snippets FOR INSERT WITH CHECK (true);
CREATE POLICY "snippets_update_all" ON snippets FOR UPDATE USING (true);
CREATE POLICY "snippets_delete_all" ON snippets FOR DELETE USING (true);
