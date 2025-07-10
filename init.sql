-- ELO Accountability Engine Database Schema

-- Users table - stores ELO ratings and user data
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    current_elo INTEGER DEFAULT 1000,
    k_factor INTEGER DEFAULT 40,
    total_challenges INTEGER DEFAULT 0,
    completed_challenges INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, guild_id)
);

-- Challenge categories defined per guild
CREATE TABLE IF NOT EXISTS categories (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(guild_id, name)
);

-- Sprints (weekly competition cycles)
CREATE TABLE IF NOT EXISTS sprints (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    start_date TIMESTAMP NOT NULL,
    end_date TIMESTAMP NOT NULL,
    status VARCHAR(20) DEFAULT 'active', -- active, ended, archived
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Challenges issued by users
CREATE TABLE IF NOT EXISTS challenges (
    id SERIAL PRIMARY KEY,
    challenge_id VARCHAR(20) UNIQUE NOT NULL, -- e.g., CHL-101
    user_id BIGINT NOT NULL,
    guild_id BIGINT NOT NULL,
    sprint_id INTEGER REFERENCES sprints(id),
    category_id INTEGER REFERENCES categories(id),
    title TEXT NOT NULL,
    description TEXT,
    difficulty_elo INTEGER NOT NULL,
    status VARCHAR(20) DEFAULT 'active', -- active, pending_review, completed, failed, rejected
    proof_link TEXT,
    proof_description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    reviewed_at TIMESTAMP
);

-- Peer review votes for challenges
CREATE TABLE IF NOT EXISTS approvals (
    id SERIAL PRIMARY KEY,
    challenge_id INTEGER REFERENCES challenges(id),
    voter_id BIGINT NOT NULL,
    guild_id BIGINT NOT NULL,
    vote_type VARCHAR(10) NOT NULL, -- approve, reject
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(challenge_id, voter_id)
);

-- ELO history for tracking rating changes
CREATE TABLE IF NOT EXISTS elo_history (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    guild_id BIGINT NOT NULL,
    challenge_id INTEGER REFERENCES challenges(id),
    elo_before INTEGER NOT NULL,
    elo_after INTEGER NOT NULL,
    elo_change INTEGER NOT NULL,
    reason VARCHAR(50) NOT NULL, -- challenge_completed, challenge_failed
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Guild configuration settings
CREATE TABLE IF NOT EXISTS guild_config (
    guild_id BIGINT PRIMARY KEY,
    k_factor_new INTEGER DEFAULT 40,
    k_factor_stable INTEGER DEFAULT 20,
    approvals_needed INTEGER DEFAULT 2,
    review_channel_id BIGINT,
    sprint_duration_days INTEGER DEFAULT 7,
    auto_start_sprints BOOLEAN DEFAULT TRUE,
    stable_user_threshold INTEGER DEFAULT 10, -- challenges needed to be considered stable
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_users_guild ON users(guild_id);
CREATE INDEX IF NOT EXISTS idx_challenges_user ON challenges(user_id);
CREATE INDEX IF NOT EXISTS idx_challenges_guild ON challenges(guild_id);
CREATE INDEX IF NOT EXISTS idx_challenges_sprint ON challenges(sprint_id);
CREATE INDEX IF NOT EXISTS idx_challenges_status ON challenges(status);
CREATE INDEX IF NOT EXISTS idx_approvals_challenge ON approvals(challenge_id);
CREATE INDEX IF NOT EXISTS idx_elo_history_user ON elo_history(user_id);
CREATE INDEX IF NOT EXISTS idx_sprints_guild ON sprints(guild_id);

-- Insert default categories for new guilds
INSERT INTO categories (guild_id, name, description) VALUES 
    (0, 'Backend', 'Server-side development, databases, APIs'),
    (0, 'Frontend', 'User interface, web development, mobile apps'),
    (0, 'DevOps', 'Infrastructure, deployment, monitoring'),
    (0, 'Learning', 'Acquiring new skills, studying, research'),
    (0, 'Refactoring', 'Code improvement, optimization, cleanup'),
    (0, 'Testing', 'Writing tests, debugging, quality assurance')
ON CONFLICT (guild_id, name) DO NOTHING;