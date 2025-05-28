-- Генерация событий для пользователей 1, 2, 3, 4
INSERT INTO events (title, description, start_date, end_date, organizers, price, author_id, is_draft)
SELECT
    CONCAT('Событие ', u.id, '.', s.num) AS title,
    CONCAT('Описание для события ', u.id, '.', s.num) AS description,
    CASE
        WHEN s.num <= 2 THEN CURRENT_DATE - (s.num * INTERVAL '10 days')            -- архивные
        ELSE CURRENT_DATE + INTERVAL '60 days' + (s.num * INTERVAL '2 days')       -- будущие
    END AS start_date,
    CASE
        WHEN s.num <= 2 THEN CURRENT_DATE - (s.num * INTERVAL '10 days') + INTERVAL '1 day'
        ELSE CURRENT_DATE + INTERVAL '60 days' + (s.num * INTERVAL '2 days') + INTERVAL '1 day'
    END AS end_date,
    CONCAT('Организатор ', u.id) AS organizers,
    0 AS price,
    u.id AS author_id,
    FALSE AS is_draft
FROM (SELECT 1 AS id UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4) AS u
CROSS JOIN generate_series(1, 5) AS s(num);



ALTER TABLE invitations
ADD COLUMN approved_by_author BOOLEAN;
