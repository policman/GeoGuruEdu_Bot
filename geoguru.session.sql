ALTER TABLE events
ALTER COLUMN photos TYPE TEXT USING photos[1];

ALTER TABLE events RENAME COLUMN photos TO photo;

CREATE TABLE favorite_materials (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    title TEXT NOT NULL,
    url TEXT,
    authors TEXT,
    year TEXT,
    annotation TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);


DELETE FROM event_participants WHERE event_id IN (SELECT id FROM events);
DELETE FROM invitations       WHERE event_id IN (SELECT id FROM events);
DELETE FROM events;



CREATE TABLE participant_messages (
  id            SERIAL PRIMARY KEY,
  event_id      INT        NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  from_user_id  INT        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  to_user_id    INT        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  message_text  TEXT       NOT NULL CHECK (length(message_text) <= 300),
  created_at    TIMESTAMP  NOT NULL DEFAULT NOW(),
  is_answered   BOOLEAN    NOT NULL DEFAULT FALSE,
  answer_text   TEXT,
  answered_at   TIMESTAMP
);
