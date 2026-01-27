-- Initialize PostgreSQL database with required extensions for Loris

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable vector operations for embeddings (pgvector)
CREATE EXTENSION IF NOT EXISTS vector;

-- Note: Additional tables and indexes will be created by Alembic migrations
