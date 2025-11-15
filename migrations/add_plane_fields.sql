-- Add Plane integration fields to users table
-- Run this migration if you have an existing database

ALTER TABLE users 
ADD COLUMN IF NOT EXISTS plane_user_id VARCHAR(255),
ADD COLUMN IF NOT EXISTS plane_api_token TEXT,
ADD COLUMN IF NOT EXISTS plane_email VARCHAR(255),
ADD COLUMN IF NOT EXISTS plane_workspace_slug VARCHAR(100),
ADD COLUMN IF NOT EXISTS plane_project_id VARCHAR(255);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_users_plane_user_id ON users(plane_user_id);

