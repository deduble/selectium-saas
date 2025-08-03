-- Add missing columns to tasks table
-- This script adds the columns needed for the new Task model

BEGIN;

-- Add description column if it doesn't exist
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS description TEXT;

-- Add task_type column if it doesn't exist
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS task_type VARCHAR(50) NOT NULL DEFAULT 'simple_scraping';

-- Add estimated_compute_units column if it doesn't exist
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS estimated_compute_units INTEGER DEFAULT 1;

-- Add progress column if it doesn't exist
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS progress INTEGER DEFAULT 0;

-- Update existing records to have proper values
UPDATE tasks SET 
    task_type = 'simple_scraping' 
WHERE task_type IS NULL OR task_type = '';

UPDATE tasks SET 
    estimated_compute_units = 1 
WHERE estimated_compute_units IS NULL;

UPDATE tasks SET 
    progress = 0 
WHERE progress IS NULL;

COMMIT;

-- Verify the changes
SELECT column_name, data_type, is_nullable, column_default 
FROM information_schema.columns 
WHERE table_name = 'tasks' 
ORDER BY ordinal_position;