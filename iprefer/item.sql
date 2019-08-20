-- name: better
-- record_class: Item
-- Get all items preferred to the given one
SELECT item.*
FROM item
    JOIN prefers ON (item.item_id = prefers.prefers)
WHERE prefers.user_id = :user_id
  AND prefers."to" = :item_id

-- name: all_items
-- record_class: Item
SELECT item.*
FROM item
