-- Focus To-Do (Chromium extension) export schema.
--
-- Mirrors the four IndexedDB object stores of the "PomodoroDB6" database:
--   os1 Project  -> projects
--   os2 Task     -> tasks
--   os3 Subtask  -> subtasks
--   os4 Pomodoro -> pomodoro_sessions
--
-- Conventions:
--   * Primary and foreign keys are the source ids verbatim (TEXT, mostly UUIDs,
--     but built-in smart lists use ids such as 'id-task-today').
--   * Source timestamps are epoch milliseconds; 0 means "unset" and is imported
--     as NULL.
--   * Durations are seconds.
--   * Source field names are kept in snake_case. Two were renamed to avoid
--     reserved words: "order" -> sort_order, "interval" -> interval_seconds.
--   * Re-runnable: every statement uses IF NOT EXISTS.

CREATE TABLE IF NOT EXISTS projects (
    id              TEXT PRIMARY KEY,
    name            TEXT        NOT NULL DEFAULT '',
    obj_type        TEXT,
    -- Self-reference is deferred so parents and children can be inserted in any order.
    parent_id       TEXT        REFERENCES projects (id) ON DELETE SET NULL
                                DEFERRABLE INITIALLY DEFERRED,
    color           TEXT,
    image_name      TEXT,
    is_default      BOOLEAN     NOT NULL DEFAULT FALSE,
    expanded        BOOLEAN     NOT NULL DEFAULT FALSE,
    ordering_rule   SMALLINT,
    type            INTEGER,
    sort_order      INTEGER,
    state           SMALLINT,
    sync            SMALLINT,
    creation_date   TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS tasks (
    id                  TEXT PRIMARY KEY,
    project_id          TEXT        REFERENCES projects (id) ON DELETE SET NULL,
    name                TEXT        NOT NULL DEFAULT '',
    obj_type            TEXT,
    remark              TEXT,
    tags                TEXT,
    priority            SMALLINT,
    sort_order          INTEGER,
    state               SMALLINT,
    sync                SMALLINT,
    is_finished         BOOLEAN     NOT NULL DEFAULT FALSE,
    is_expanded         BOOLEAN     NOT NULL DEFAULT FALSE,
    has_subtask         BOOLEAN     NOT NULL DEFAULT FALSE,
    estimate_pomo_num   INTEGER,
    actual_pomo_num     INTEGER,
    pomodoro_interval   INTEGER,
    creation_date       TIMESTAMPTZ,
    deadline            TIMESTAMPTZ,
    finished_date       TIMESTAMPTZ,
    reminder_date       TIMESTAMPTZ,
    reminders           TEXT,
    r_id                TEXT,
    r_cycle             SMALLINT,
    r_unit              TEXT,
    r_value             TEXT,
    r_first_deadline    TIMESTAMPTZ,
    r_start_date        TIMESTAMPTZ,
    r_end_date          TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS subtasks (
    id                  TEXT PRIMARY KEY,
    task_id             TEXT        REFERENCES tasks (id) ON DELETE CASCADE,
    name                TEXT        NOT NULL DEFAULT '',
    obj_type            TEXT,
    is_finished         BOOLEAN     NOT NULL DEFAULT FALSE,
    estimated_pomo_num  INTEGER,
    sort_order          INTEGER,
    state               SMALLINT,
    sync                SMALLINT,
    creation_date       TIMESTAMPTZ,
    finished_date       TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS pomodoro_sessions (
    id                  TEXT PRIMARY KEY,
    task_id             TEXT        REFERENCES tasks (id) ON DELETE SET NULL,
    subtask_id          TEXT        REFERENCES subtasks (id) ON DELETE SET NULL,
    obj_type            TEXT,
    interval_seconds    INTEGER,
    pomodoro_interval   INTEGER,
    is_manual           BOOLEAN     NOT NULL DEFAULT FALSE,
    state               SMALLINT,
    sync                SMALLINT,
    creation_date       TIMESTAMPTZ,
    end_date            TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_projects_parent_id ON projects (parent_id);
CREATE INDEX IF NOT EXISTS idx_tasks_project_id ON tasks (project_id);
CREATE INDEX IF NOT EXISTS idx_subtasks_task_id ON subtasks (task_id);
CREATE INDEX IF NOT EXISTS idx_pomodoro_sessions_task_id ON pomodoro_sessions (task_id);
CREATE INDEX IF NOT EXISTS idx_pomodoro_sessions_subtask_id ON pomodoro_sessions (subtask_id);
CREATE INDEX IF NOT EXISTS idx_pomodoro_sessions_end_date ON pomodoro_sessions (end_date);
