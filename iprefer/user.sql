-- name: add_user!
INSERT OR IGNORE INTO user(name, google_id)
VALUES (:name, :google_id);


-- name: get_user^
-- record_class: User
SELECT *
FROM user
WHERE google_id = :google_id;
