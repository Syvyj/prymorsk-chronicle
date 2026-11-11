-- reader corrections (worker.js /api/fix); applied by hand after review
CREATE TABLE IF NOT EXISTS fixes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created TEXT NOT NULL DEFAULT (datetime('now')),
  article TEXT NOT NULL,          -- article id (n) or ''
  page TEXT NOT NULL,             -- the address the reader was on
  fragment TEXT NOT NULL,         -- the text they selected (may be empty)
  fix TEXT NOT NULL,              -- how it should read
  comment TEXT NOT NULL DEFAULT '',
  visitor TEXT NOT NULL,          -- daily hash of the address, only to limit floods; no IP is kept
  status TEXT NOT NULL DEFAULT 'new'  -- new / applied / rejected
);
CREATE INDEX IF NOT EXISTS fixes_visitor ON fixes (visitor, created);

-- article views (worker.js /api/view): only the article id and the day; nothing about the reader
CREATE TABLE IF NOT EXISTS views (
  article TEXT NOT NULL,
  day TEXT NOT NULL,              -- YYYY-MM-DD (UTC)
  n INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (article, day)
);

-- memories and dreams for the map (worker.js /api/memory); shown on timeline/memories.html only once approved
CREATE TABLE IF NOT EXISTS memories (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created TEXT NOT NULL DEFAULT (datetime('now')),
  kind TEXT NOT NULL,             -- memory / dream
  village TEXT NOT NULL,          -- as the map names it
  text TEXT NOT NULL,
  name TEXT NOT NULL DEFAULT '',  -- already shortened by the page («Ірина Д.»); the worker shortens again
  year INTEGER,                   -- memories only, optional
  visitor TEXT NOT NULL,          -- daily hash of the address, only to limit floods; no IP is kept
  status TEXT NOT NULL DEFAULT 'new'  -- new / approved / rejected
);
CREATE INDEX IF NOT EXISTS memories_status ON memories (status, created);
