-- 创建用户类型枚举
CREATE TYPE user_type AS ENUM ('admin', 'user');
-- 创建用户表
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL UNIQUE,
    nickname VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    type user_type NOT NULL DEFAULT 'user'
);
-- 创建会话表
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 为user_id添加索引以提高查询效率
CREATE INDEX idx_conversations_user_id ON conversations(user_id);

-- 创建自动更新时间的触发器函数
CREATE OR REPLACE FUNCTION update_updated_time() RETURNS TRIGGER AS $$ BEGIN NEW.updated_at = CURRENT_TIMESTAMP;
RETURN NEW;
END;
$$ LANGUAGE plpgsql;
-- 为用户表添加触发器
CREATE TRIGGER trigger_update_users_updated_time BEFORE
UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_time();
-- 为会话表添加触发器
CREATE TRIGGER trigger_update_conversations_updated_time BEFORE
UPDATE ON conversations FOR EACH ROW EXECUTE FUNCTION update_updated_time();
