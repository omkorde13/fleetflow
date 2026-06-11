-- FleetFlow Database Initialization
-- This runs once when the PostgreSQL container is first created

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable trigram search (for driver/user search)
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Create application user with limited permissions (optional hardening)
-- The main app uses POSTGRES_USER from env, this is just a setup confirmation
DO $$
BEGIN
    RAISE NOTICE 'FleetFlow DB initialized at %', NOW();
END $$;
