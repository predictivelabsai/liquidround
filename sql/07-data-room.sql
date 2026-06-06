-- Data Room table for file uploads
CREATE TABLE IF NOT EXISTS liquidround.data_room (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    company_slug VARCHAR(255),
    filename VARCHAR(500) NOT NULL,
    content_type VARCHAR(255) DEFAULT 'application/octet-stream',
    size_bytes BIGINT DEFAULT 0,
    data BYTEA,
    uploaded_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_data_room_user ON liquidround.data_room(user_id);
CREATE INDEX IF NOT EXISTS idx_data_room_company ON liquidround.data_room(company_slug);
