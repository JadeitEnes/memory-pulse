CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_extension WHERE extname = 'timescaledb'
    ) THEN
        RAISE NOTICE 'TimescaleDB extension loaded successfully';
    ELSE
        RAISE WARNING 'TimescaleDB extension not available';
    END IF;
END $$;