-- name: better
-- record_class: Item
-- Get all items preferred to the given one
SELECT item.*
FROM item
    JOIN prefers ON (item.item_id = prefers.prefers)
WHERE prefers.user_id = :user_id
  AND prefers."to" = :item_id

-- name: worse
-- record_class: Item
-- Get all items which the user deems worse than the given item
SELECT item.*
FROM item
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
SELECT item.*
FROM item
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

-- name: save_preference!
-- Store which of these two items is preferred by the user
INSERT OR REPLACE INTO user.prefers(user_id, prefers, "to")
VALUES(:user_id, :prefers, :to)

-- name: get_graph
-- Get graph of preferences for rank calculation
SELECT prefers AS better, "to" AS worse
FROM prefers;

-- name: save_rank*!
-- Save the calculated rank for fast querying
UPDATE item
SET rank = :rank
WHERE item_id = :item_id;
