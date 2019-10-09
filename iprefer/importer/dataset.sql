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

DROP VIEW IF EXISTS item_with_tags;
CREATE VIEW item_with_tags AS
SELECT item.*, json_group_object(key, json(vals)) AS tags
FROM item
    JOIN (
        SELECT item_id, key, json_group_array(value) AS vals
        FROM tags
        GROUP BY item_id, key
    ) USING (item_id)
GROUP BY item_id;
