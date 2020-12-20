-- name: create-schema#
DROP TABLE IF EXISTS item;
CREATE TABLE item(
    item_id text PRIMARY KEY,
    name text NOT NULL,
    lat float,
    lon float,
    rank float
) WITHOUT ROWID;
CREATE INDEX rank_idx ON item(rank);

DROP TABLE IF EXISTS tag;
CREATE TABLE tag(
    -- Non readable identifier of tag
    tag_id text PRIMARY KEY,
    -- Type of tag (e.g. "author")
    key text NOT NULL,
    -- Human readable tag value (e.g. "Ernest Hemingway" for the "author" key)
    label text  -- NOT NULL after data load
) WITHOUT ROWID;

DROP TABLE IF EXISTS item_to_tag;
CREATE TABLE item_to_tag(
    item_id text NOT NULL,
    tag_id text NOT NULL,
    PRIMARY KEY (item_id, tag_id)
) WITHOUT ROWID;
CREATE INDEX item_to_tag_item_idx ON item_to_tag(item_id);
CREATE INDEX item_to_tag_tag_idx ON item_to_tag(tag_id);

DROP VIEW IF EXISTS item_with_tags_view;
CREATE VIEW item_with_tags_view AS
SELECT item.*, json_group_object(key, json(labels)) AS tags
FROM item
    LEFT JOIN (
        SELECT item_id, key, json_group_array(label) AS labels
        FROM tag
             JOIN item_to_tag USING (tag_id)
        GROUP BY item_id, key
    ) USING (item_id)
GROUP BY item_id;

-- name: refresh_views#
DROP TABLE IF EXISTS item_with_tags;
CREATE TABLE item_with_tags AS
SELECT * FROM item_with_tags_view;
CREATE INDEX item_with_tags_item_idx ON item_with_tags(item_id);
