CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    university TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL

    course TEXT,
    year_of_study TEXT,
    location TEXT,
    bio TEXT,
    profile_picture TEXT
);