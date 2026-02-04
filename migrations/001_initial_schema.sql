-- Resume RAG Initial Schema
-- PostgreSQL 16+

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Enum types
CREATE TYPE location_type AS ENUM ('remote', 'hybrid', 'onsite');
CREATE TYPE company_size AS ENUM ('startup', 'small', 'medium', 'large', 'enterprise');
CREATE TYPE job_source AS ENUM ('linkedin', 'indeed', 'dice', 'wellfound', 'glassdoor', 'other');
CREATE TYPE match_quality AS ENUM ('excellent', 'good', 'fair', 'poor');
CREATE TYPE scrape_status AS ENUM ('pending', 'in_progress', 'completed', 'failed');
CREATE TYPE application_status AS ENUM (
    'saved', 'applied', 'phone_screen', 'technical',
    'onsite', 'offer', 'rejected', 'withdrawn', 'accepted'
);

-- Companies table
CREATE TABLE companies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    domain VARCHAR(255),
    industry VARCHAR(100),
    size company_size,
    description TEXT,
    logo_url VARCHAR(512),
    careers_url VARCHAR(512),
    linkedin_url VARCHAR(512),
    glassdoor_rating DECIMAL(2,1),
    employee_count INTEGER,
    founded_year INTEGER,
    headquarters VARCHAR(255),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT companies_name_unique UNIQUE (name, domain)
);

-- Jobs table
CREATE TABLE jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    external_id VARCHAR(255),
    company_id UUID REFERENCES companies(id) ON DELETE SET NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    location VARCHAR(255),
    location_type location_type DEFAULT 'onsite',
    salary_min INTEGER,
    salary_max INTEGER,
    salary_currency VARCHAR(3) DEFAULT 'USD',
    experience_years_min INTEGER,
    experience_years_max INTEGER,
    employment_type VARCHAR(50) DEFAULT 'full-time',
    source job_source NOT NULL,
    source_url VARCHAR(1024),
    posted_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE,

    -- Skills and requirements (extracted)
    required_skills TEXT[],
    preferred_skills TEXT[],
    technologies TEXT[],

    -- Match data (computed)
    match_score DECIMAL(5,2),
    match_quality match_quality,
    match_reasons TEXT[],

    -- Scraping metadata
    scrape_status scrape_status DEFAULT 'completed',
    raw_html TEXT,

    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT jobs_external_source_unique UNIQUE (external_id, source)
);

-- Resumes table
CREATE TABLE resumes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    file_path VARCHAR(512),
    file_type VARCHAR(50),
    content TEXT NOT NULL,

    -- Extracted data
    skills TEXT[],
    experience_years INTEGER,
    education TEXT[],
    certifications TEXT[],
    summary TEXT,

    -- Embedding reference (stored in Qdrant)
    embedding_id VARCHAR(255),

    is_primary BOOLEAN DEFAULT FALSE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Applications table (job tracking)
CREATE TABLE applications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID REFERENCES jobs(id) ON DELETE CASCADE,
    resume_id UUID REFERENCES resumes(id) ON DELETE SET NULL,
    status application_status DEFAULT 'saved',
    priority INTEGER DEFAULT 0,

    -- Dates
    applied_at TIMESTAMPTZ,
    last_contact_at TIMESTAMPTZ,
    next_action_at TIMESTAMPTZ,

    -- Notes and tracking
    notes TEXT,
    contact_name VARCHAR(255),
    contact_email VARCHAR(255),
    contact_phone VARCHAR(50),

    -- Cover letter (generated)
    cover_letter TEXT,
    cover_letter_generated_at TIMESTAMPTZ,

    -- Interview tracking
    interview_count INTEGER DEFAULT 0,

    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Application timeline (status changes)
CREATE TABLE application_timeline (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    application_id UUID REFERENCES applications(id) ON DELETE CASCADE,
    from_status application_status,
    to_status application_status NOT NULL,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Saved searches
CREATE TABLE saved_searches (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    query TEXT,
    filters JSONB DEFAULT '{}',
    sources job_source[],
    notify_new BOOLEAN DEFAULT FALSE,
    last_run_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Chat sessions
CREATE TABLE chat_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    mode VARCHAR(50) DEFAULT 'general',
    title VARCHAR(255),
    job_context_id UUID REFERENCES jobs(id) ON DELETE SET NULL,
    message_count INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Chat messages
CREATE TABLE chat_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    citations JSONB DEFAULT '[]',
    tokens_used INTEGER,
    latency_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Settings table (key-value store)
CREATE TABLE settings (
    key VARCHAR(255) PRIMARY KEY,
    value JSONB NOT NULL,
    category VARCHAR(100),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Scrape jobs queue
CREATE TABLE scrape_queue (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source job_source NOT NULL,
    search_query TEXT,
    search_params JSONB DEFAULT '{}',
    status scrape_status DEFAULT 'pending',
    jobs_found INTEGER DEFAULT 0,
    jobs_saved INTEGER DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_jobs_company ON jobs(company_id);
CREATE INDEX idx_jobs_source ON jobs(source);
CREATE INDEX idx_jobs_posted ON jobs(posted_at DESC);
CREATE INDEX idx_jobs_match_score ON jobs(match_score DESC) WHERE is_active = TRUE;
CREATE INDEX idx_jobs_active ON jobs(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_jobs_title_trgm ON jobs USING gin(title gin_trgm_ops);
CREATE INDEX idx_jobs_skills ON jobs USING gin(required_skills);
CREATE INDEX idx_jobs_technologies ON jobs USING gin(technologies);

CREATE INDEX idx_applications_job ON applications(job_id);
CREATE INDEX idx_applications_status ON applications(status);
CREATE INDEX idx_applications_priority ON applications(priority DESC, created_at DESC);

CREATE INDEX idx_timeline_application ON application_timeline(application_id);
CREATE INDEX idx_timeline_created ON application_timeline(created_at DESC);

CREATE INDEX idx_chat_sessions_mode ON chat_sessions(mode);
CREATE INDEX idx_chat_messages_session ON chat_messages(session_id);

CREATE INDEX idx_companies_name_trgm ON companies USING gin(name gin_trgm_ops);

-- Updated at trigger function
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply updated_at triggers
CREATE TRIGGER jobs_updated_at BEFORE UPDATE ON jobs FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER companies_updated_at BEFORE UPDATE ON companies FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER resumes_updated_at BEFORE UPDATE ON resumes FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER applications_updated_at BEFORE UPDATE ON applications FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER chat_sessions_updated_at BEFORE UPDATE ON chat_sessions FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER saved_searches_updated_at BEFORE UPDATE ON saved_searches FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Insert default settings
INSERT INTO settings (key, value, category) VALUES
    ('llm_provider', '"anthropic"', 'llm'),
    ('llm_model', '"claude-sonnet-4-20250514"', 'llm'),
    ('embedding_model', '"all-MiniLM-L6-v2"', 'ml'),
    ('search_top_k', '10', 'search'),
    ('search_vector_weight', '0.7', 'search'),
    ('rerank_enabled', 'true', 'search');
