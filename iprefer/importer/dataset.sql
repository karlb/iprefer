-- name: create-schema#
DROP TABLE IF EXISTS item;
CREATE TABLE item(
    item_id text PRIMARY KEY,
    name text NOT NULL,
    description text,
    alt_names text,
    lat float,
    lon float,
    rank float,
    importance float
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
ATTACH DATABASE 'wikilinks.sqlite3' AS wikilinks;
UPDATE item SET importance = (SELECT rank FROM wikilinks WHERE qid = item_id);

DROP TABLE IF EXISTS item_with_tags;
CREATE TABLE item_with_tags AS
SELECT * FROM item_with_tags_view;
CREATE INDEX item_with_tags_item_idx ON item_with_tags(item_id);

DROP TABLE IF EXISTS item_fts;
CREATE VIRTUAL TABLE item_fts USING fts4(
    item_id,
    name,
    detail,
    notindexed=item_id
);
INSERT INTO item_fts SELECT item_id, name, '' FROM item;
