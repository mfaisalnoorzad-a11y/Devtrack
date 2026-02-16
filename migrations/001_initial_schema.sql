CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    github_username TEXT UNIQUE NOT NULL,
    github_token TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_synced_at TIMESTAMPTZ
);

CREATE TABLE repositories (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    repo_name TEXT NOT NULL,
    repo_url TEXT NOT NULL,
    language TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE commits (
    id SERIAL PRIMARY KEY,
    repository_id INTEGER REFERENCES repositories(id) ON DELETE CASCADE,
    commit_sha TEXT UNIQUE NOT NULL,
    message TEXT NOT NULL,
    author_date TIMESTAMPTZ NOT NULL,
    files_changed INTEGER DEFAULT 0,
    additions INTEGER DEFAULT 0,
    deletions INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE summaries (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    timeframe TEXT NOT NULL CHECK (timeframe IN ('week', 'month')),
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    summary_text TEXT NOT NULL,
    generated_at TIMESTAMPTZ DEFAULT NOW()
);