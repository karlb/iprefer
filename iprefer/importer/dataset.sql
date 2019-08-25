-- name: create-schema#
DROP TABLE IF EXISTS item;
CREATE TABLE item(
    name text NOT NULL,
    item_id text NOT NULL,
    rank float
);
CREATE INDEX rank_idx ON item(rank);

DROP TABLE IF EXISTS tags;
CREATE TABLE tags(
    item_id text NOT NULL,
    key text NOT NULL,
    value text NOT NULL,
    PRIMARY KEY (item_id, key, value)
);
