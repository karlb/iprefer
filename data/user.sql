CREATE TABLE user(
    user_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    google_id INT NOT NULL,
);

CREATE TABLE prefers(
    user_id INTEGER REFERENCES user(user_id),
    prefers INTEGER NOT NULL,
    "to" INTEGER NOT NULL,
    updated TIMESTAMPT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, prefers, "to")
);
-- The same item can't be both better and worse
CREATE UNIQUE INDEX prevent_contradiction_idx
    ON prefers(user_id, min(prefers, "to"), max(prefers, "to"));
