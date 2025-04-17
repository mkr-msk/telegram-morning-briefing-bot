CREATE TABLE users (
  chat_id BIGINT PRIMARY KEY,
  notify_time TIME NOT NULL,
  modules JSONB NOT NULL DEFAULT '[]'
);