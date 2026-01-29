-- Phase 8: Turbo Loris Migration
-- Run this against the loris database after updating the backend code

-- Add turbo fields to questions table
ALTER TABLE questions ADD COLUMN IF NOT EXISTS turbo_mode BOOLEAN DEFAULT FALSE;
ALTER TABLE questions ADD COLUMN IF NOT EXISTS turbo_threshold FLOAT;
ALTER TABLE questions ADD COLUMN IF NOT EXISTS turbo_confidence FLOAT;

-- Add TURBO_ANSWERED to questionstatus enum
-- Note: PostgreSQL enums require a special ALTER command
DO $$
BEGIN
    -- Check if the value already exists
    IF NOT EXISTS (
        SELECT 1 FROM pg_enum
        WHERE enumlabel = 'turbo_answered'
        AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'questionstatus')
    ) THEN
        ALTER TYPE questionstatus ADD VALUE 'turbo_answered';
    END IF;
END$$;

-- Create turbo_attributions table
CREATE TABLE IF NOT EXISTS turbo_attributions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question_id UUID NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    source_type VARCHAR(50) NOT NULL,
    source_id UUID NOT NULL,
    attributed_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    display_name VARCHAR(255) NOT NULL,
    contribution_type VARCHAR(50) NOT NULL,
    confidence_score FLOAT NOT NULL,
    semantic_similarity FLOAT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_turbo_attr_question ON turbo_attributions(question_id);
CREATE INDEX IF NOT EXISTS idx_turbo_attr_source ON turbo_attributions(source_type, source_id);
