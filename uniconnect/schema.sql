CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    university TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,

    course TEXT,
    year_of_study TEXT,
    location TEXT,
    bio TEXT,
    profile_picture TEXT
);

CREATE TABLE IF NOT EXISTS interests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS user_interests (
    user_id INTEGER NOT NULL,
    interest_id INTEGER NOT NULL,

    PRIMARY KEY (user_id, interest_id),

    FOREIGN KEY (user_id) REFERENCES users (id),
    FOREIGN KEY (interest_id) REFERENCES interests (id)
);

INSERT OR IGNORE INTO interests (name) VALUES
    ('Football'),
    ('Cricket'),
    ('Basketball'),
    ('Tennis'),
    ('Gym'),
    ('Running'),
    ('Gaming'),
    ('Music'),
    ('Movies'),
    ('Reading'),
    ('Travel'),
    ('Photography'),
    ('Coding'),
    ('Artificial Intelligence'),
    ('Web Development'),
    ('Cybersecurity'),
    ('Art'),
    ('Cooking'),
    ('Volunteering'),
    ('Entrepreneurship');

CREATE TABLE IF NOT EXISTS friend_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    sender_id INTEGER NOT NULL,
    receiver_id INTEGER NOT NULL,

    status TEXT NOT NULL DEFAULT 'pending',

    FOREIGN KEY (sender_id) REFERENCES users (id),
    FOREIGN KEY (receiver_id) REFERENCES users (id),

    UNIQUE (sender_id, receiver_id)
);

CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users (id)
);