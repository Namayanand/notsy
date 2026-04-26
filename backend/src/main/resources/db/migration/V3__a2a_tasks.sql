-- A2A Tasks table for tracking agent delegations
CREATE TABLE IF NOT EXISTS a2a_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    skill VARCHAR(100),
    status VARCHAR(50) DEFAULT 'submitted',
    input_payload JSONB,
    output_payload JSONB,
    agent_name VARCHAR(100),
    agent_chain TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Index for efficient querying by user
CREATE INDEX IF NOT EXISTS idx_a2a_tasks_user_id ON a2a_tasks(user_id);
CREATE INDEX IF NOT EXISTS idx_a2a_tasks_created_at ON a2a_tasks(created_at);
CREATE INDEX IF NOT EXISTS idx_a2a_tasks_status ON a2a_tasks(status);