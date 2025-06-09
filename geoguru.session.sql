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

UPDATE users
SET position = 'Сотрудник',
    department = NULL
WHERE id = 1;

ALTER TABLE users
  ADD COLUMN place_of_work TEXT,
  ADD COLUMN open_to_offers BOOLEAN DEFAULT TRUE;



-- 1. Таблица тестов
CREATE TABLE tests (
  id          SERIAL PRIMARY KEY,
  title       TEXT NOT NULL,
  description TEXT,
  created_by  INTEGER NOT NULL REFERENCES users(id),
  created_at  TIMESTAMP NOT NULL DEFAULT NOW()
);

-- 2. Вопросы в тесте
CREATE TABLE questions (
  id         SERIAL PRIMARY KEY,
  test_id    INTEGER NOT NULL REFERENCES tests(id) ON DELETE CASCADE,
  text       TEXT NOT NULL,
  position   INTEGER NOT NULL,  -- порядок внутри теста
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- 3. Варианты ответов
CREATE TABLE options (
  id           SERIAL PRIMARY KEY,
  question_id  INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
  text         TEXT NOT NULL,
  is_correct   BOOLEAN NOT NULL DEFAULT FALSE
);

-- 4. Результаты прохождения
CREATE TABLE test_results (
  id              SERIAL PRIMARY KEY,
  user_id         INTEGER NOT NULL REFERENCES users(id),
  test_id         INTEGER NOT NULL REFERENCES tests(id),
  correct_answers INTEGER NOT NULL,
  total_questions INTEGER NOT NULL,
  taken_at        TIMESTAMP NOT NULL DEFAULT NOW()
);

-- 5. (Опционально) “сырые” ответы пользователя
CREATE TABLE user_answers (
  id            SERIAL PRIMARY KEY,
  result_id     INTEGER NOT NULL REFERENCES test_results(id) ON DELETE CASCADE,
  question_id   INTEGER NOT NULL REFERENCES questions(id),
  chosen_option INTEGER NOT NULL REFERENCES options(id)
);




CREATE TABLE test_invitations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    test_id INTEGER REFERENCES tests(id),
    invited_at TIMESTAMP DEFAULT now(),
    accepted BOOLEAN DEFAULT FALSE,
    declined BOOLEAN DEFAULT FALSE
);




-- Удаляем ответы пользователей
DELETE FROM user_answers;

-- Удаляем результаты тестов
DELETE FROM test_results;

-- Удаляем приглашения на тесты
DELETE FROM test_invitations;

-- Удаляем варианты ответов
DELETE FROM options;

-- Удаляем вопросы
DELETE FROM questions;

-- Удаляем тесты
DELETE FROM tests;


-- Вставка тестов
INSERT INTO tests (id, title, description, created_by, created_at) VALUES
(1, 'Основы геологии', 'Базовый тест по основам геологических процессов.', 1, '2025-06-09 03:25:37.808974'),
(2, 'Минералогия', 'Проверка знаний по свойствам и классификации минералов.', 1, '2025-06-09 03:25:37.808989'),
(3, 'Основы экологии', 'Знание экологических принципов и понятий.', 2, '2025-06-09 03:25:37.808992'),
(4, 'Рациональное недропользование', 'Основы рационального использования ресурсов.', 2, '2025-06-09 03:25:37.808994'),
(5, 'Горные работы: безопасность', 'Введение в правила охраны труда при горных работах.', 3, '2025-06-09 03:25:37.808997'),
(6, 'Обогащение полезных ископаемых', 'Проверка понимания методов обогащения.', 3, '2025-06-09 03:25:37.808999'),
(7, 'Геофизические методы', 'Базовые принципы геофизических исследований.', 4, '2025-06-09 03:25:37.809001'),
(8, 'Сейсморазведка', 'Тест по методам и этапам сейсморазведки.', 4, '2025-06-09 03:25:37.809004');

-- Вставка вопросов и вариантов
-- Тест 1
INSERT INTO questions (id, test_id, text, position, created_at) VALUES
(1, 1, 'Что изучает геология?', 1, '2025-06-09 03:25:37.809006'),
(2, 1, 'Как называется самая твёрдая горная порода?', 2, '2025-06-09 03:25:37.809008');
INSERT INTO options (question_id, text, is_correct) VALUES
(1, 'Звёзды и планеты', FALSE),
(1, 'Живые организмы', FALSE),
(1, 'Строение Земли', TRUE),
(1, 'Химические реакции', FALSE),
(2, 'Базальт', FALSE),
(2, 'Известняк', FALSE),
(2, 'Гранит', FALSE),
(2, 'Алмаз', TRUE);

-- Тест 2
INSERT INTO questions (id, test_id, text, position, created_at) VALUES
(3, 2, 'Какой минерал содержит кальций?', 1, '2025-06-09 03:25:37.809012'),
(4, 2, 'Что такое твердость по Моосу?', 2, '2025-06-09 03:25:37.809016');
INSERT INTO options (question_id, text, is_correct) VALUES
(3, 'Кварц', FALSE),
(3, 'Галит', FALSE),
(3, 'Кальцит', TRUE),
(3, 'Графит', FALSE),
(4, 'Способ измерения плотности', FALSE),
(4, 'Шкала радиоактивности', FALSE),
(4, 'Шкала твёрдости минералов', TRUE),
(4, 'Оценка магнитных свойств', FALSE);

-- Тест 3
INSERT INTO questions (id, test_id, text, position, created_at) VALUES
(5, 3, 'Что такое биосфера?', 1, '2025-06-09 03:25:37.809020'),
(6, 3, 'Какой газ считается парниковым?', 2, '2025-06-09 03:25:37.809024');
INSERT INTO options (question_id, text, is_correct) VALUES
(5, 'Водная оболочка Земли', FALSE),
(5, 'Атмосфера', FALSE),
(5, 'Совокупность всех живых организмов', TRUE),
(5, 'Грунт', FALSE),
(6, 'Кислород', FALSE),
(6, 'Азот', FALSE),
(6, 'Углекислый газ', TRUE),
(6, 'Неон', FALSE);

-- Тест 4
INSERT INTO questions (id, test_id, text, position, created_at) VALUES
(7, 4, 'Что означает термин «устойчивое развитие»?', 1, '2025-06-09 03:25:37.809029'),
(8, 4, 'Какой способ добычи менее разрушителен для экосистемы?', 2, '2025-06-09 03:25:37.809033');
INSERT INTO options (question_id, text, is_correct) VALUES
(7, 'Быстрое освоение ресурсов', FALSE),
(7, 'Развитие без ущерба будущим поколениям', TRUE),
(7, 'Рост потребления', FALSE),
(7, 'Сокращение производства', FALSE),
(8, 'Открытая выемка', FALSE),
(8, 'Карьерный способ', FALSE),
(8, 'Подземная добыча', TRUE),
(8, 'Гидроразрыв', FALSE);

-- Тест 5
INSERT INTO questions (id, test_id, text, position, created_at) VALUES
(9, 5, 'Что обязательно при спуске в шахту?', 1, '2025-06-09 03:25:37.809037'),
(10, 5, 'Какой элемент экипировки защищает дыхание?', 2, '2025-06-09 03:25:37.809041');
INSERT INTO options (question_id, text, is_correct) VALUES
(9, 'Телефон', FALSE),
(9, 'Каска', TRUE),
(9, 'Еда', FALSE),
(9, 'Ручка', FALSE),
(10, 'Фонарик', FALSE),
(10, 'Респиратор', TRUE),
(10, 'Ботинки', FALSE),
(10, 'Очки', FALSE);

-- Тест 6
INSERT INTO questions (id, test_id, text, position, created_at) VALUES
(11, 6, 'Что такое флотация?', 1, '2025-06-09 03:25:37.809045'),
(12, 6, 'Какой метод применяют для разделения по магнитным свойствам?', 2, '2025-06-09 03:25:37.809050');
INSERT INTO options (question_id, text, is_correct) VALUES
(11, 'Физико-химический метод обогащения', TRUE),
(11, 'Процесс фильтрации', FALSE),
(11, 'Химическая очистка', FALSE),
(11, 'Промывание водой', FALSE),
(12, 'Сепарация', TRUE),
(12, 'Гравитационный метод', FALSE),
(12, 'Сушка', FALSE),
(12, 'Сортировка по размеру', FALSE);

-- Тест 7
INSERT INTO questions (id, test_id, text, position, created_at) VALUES
(13, 7, 'Какой метод исследования основан на гравитации?', 1, '2025-06-09 03:25:37.809053'),
(14, 7, 'Что измеряет магниторазведка?', 2, '2025-06-09 03:25:37.809058');
INSERT INTO options (question_id, text, is_correct) VALUES
(13, 'Гравиразведка', TRUE),
(13, 'Сейсморазведка', FALSE),
(13, 'Радиолокация', FALSE),
(13, 'Георадар', FALSE),
(14, 'Электропроводность', FALSE),
(14, 'Плотность', FALSE),
(14, 'Магнитное поле', TRUE),
(14, 'Температуру', FALSE);

-- Тест 8
INSERT INTO questions (id, test_id, text, position, created_at) VALUES
(15, 8, 'Что такое отражённая волна в сейсморазведке?', 1, '2025-06-09 03:25:37.809060'),
(16, 8, 'Что используют для возбуждения сейсмических волн?', 2, '2025-06-09 03:25:37.809063');
INSERT INTO options (question_id, text, is_correct) VALUES
(15, 'Волна от солнца', FALSE),
(15, 'Волна, вернувшаяся от границы слоёв', TRUE),
(15, 'Радиоволна', FALSE),
(15, 'Шум', FALSE),
(16, 'Бензин', FALSE),
(16, 'Взрывчатку или виброисточник', TRUE),
(16, 'Звук', FALSE),
(16, 'Лазер', FALSE);






DELETE FROM participant_messages;