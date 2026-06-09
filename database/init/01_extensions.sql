-- JAIOS PostgreSQL extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "citext";

-- Separate schema for n8n (created by n8n service, pre-provision DB)
CREATE DATABASE jaios_n8n;
