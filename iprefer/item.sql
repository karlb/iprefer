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

-- name: save_preference!
-- Remember which of these two items is preferred by the user
INSERT OR REPLACE INTO user.prefers(user_id, prefers, "to")
VALUES(:user_id, :prefers, :to)
