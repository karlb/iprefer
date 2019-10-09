-- name: better
-- record_class: Item
-- Get all items preferred to the given one
SELECT item.*
FROM item_with_tags AS item
    JOIN prefers ON (item.item_id = prefers.prefers)
WHERE prefers.user_id = :user_id
  AND prefers."to" = :item_id

-- name: worse
-- record_class: Item
-- Get all items which the user deems worse than the given item
SELECT item.*
FROM item_with_tags AS item
    JOIN prefers ON (item.item_id = prefers."to")
WHERE prefers.user_id = :user_id
  AND prefers.prefers = :item_id

-- name: all_items
-- record_class: Item
SELECT item.*
FROM item
ORDER BY coalesce(rank, 'inf')

-- name: start_page_items
-- record_class: Item
SELECT *
FROM item_with_tags
ORDER BY coalesce(rank, 'inf')
LIMIT 16;

-- name: tag_items
-- record_class: Item
SELECT item.*
FROM item
    JOIN tags USING (item_id)
WHERE key = :key
  AND value = :value
ORDER BY coalesce(rank, 'inf')
LIMIT 16;

-- name: search_items
-- record_class: Item
SELECT item.*
FROM item
WHERE name LIKE '%' || :term || '%'
ORDER BY coalesce(rank, 'inf')
LIMIT 16;

-- name: tags
SELECT key, json_group_array(value)
FROM tags
WHERE item_id = :item_id
GROUP BY key;

-- name: tag
-- record_class: scalar
SELECT value
FROM tags
WHERE item_id = :item_id
  AND key = :key;

-- name: alternatives
-- record_class: Item
-- Get recommended alternatives to given item
SELECT item_with_tags.*
FROM item_with_tags
    JOIN (
        SELECT alternative.item_id, count(*) similarity
        FROM tags main_item
            JOIN tags alternative USING (key, value)
        WHERE main_item.item_id = :item_id
          AND key IN ('addr:suburb', 'addr:street', 'amenity', 'cuisine')
          AND alternative.item_id != main_item.item_id
        GROUP BY 1
    ) USING (item_id)
ORDER BY 1/coalesce(rank, 0.3) * similarity DESC
LIMIT 10;

-- name: save_preference!
-- Store which of these two items is preferred by the user
INSERT OR REPLACE INTO prefers(user_id, prefers, "to")
VALUES(:user_id, :prefers, :to)

-- name: remove_prefer!
DELETE FROM prefers
WHERE user_id = :user_id
  AND (
    (prefers, "to") = (:item_id, :remove_item_id)
    OR
    ("to", prefers) = (:item_id, :remove_item_id)
)

-- name: get_graph
-- Get graph of preferences for rank calculation
SELECT
    CASE WHEN net_count > 0 THEN prefers ELSE "to" END AS prefers,
    CASE WHEN net_count > 0 THEN "to" ELSE prefers END AS "to",
    abs(net_count) AS net_count
FROM (
    SELECT prefers, "to", sum(cnt) AS net_count
    FROM (
        SELECT
            CASE WHEN prefers < "to" THEN prefers ELSE "to" END AS prefers,
            CASE WHEN prefers < "to" THEN "to" ELSE prefers END AS "to",
            CASE WHEN prefers < "to" THEN 1 ELSE -1 END AS cnt
        FROM prefers
    )
    GROUP BY 1, 2
)
WHERE net_count != 0;

-- name: save_rank*!
-- Save the calculated rank for fast querying
UPDATE item
SET rank = :rank
WHERE item_id = :item_id;
