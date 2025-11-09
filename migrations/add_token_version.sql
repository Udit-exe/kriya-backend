-- Migration: Add token_version column to users table
-- This enables JWT revocation without storing tokens in database

-- Add token_version column with default value 0
ALTER TABLE users ADD COLUMN IF NOT EXISTS token_version INTEGER NOT NULL DEFAULT 0;

-- Add comment to explain the column
COMMENT ON COLUMN users.token_version IS 'Incremented on logout to invalidate all JWTs';

-- Optional: Drop the tokens table if you no longer need it
-- WARNING: This will delete all token records!
-- Uncomment the line below if you want to remove the tokens table:
-- DROP TABLE IF EXISTS tokens CASCADE;

-- Note: The tokens table is now optional and can be used for audit logging only

