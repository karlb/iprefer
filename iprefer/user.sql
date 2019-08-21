-- name: add_user!
INSERT INTO user(name, google_id)
VALUES (:name, :google_id)
ON CONFLICT DO NOTHING;


-- name: get_user^
-- record_class: User
SELECT *
FROM user
WHERE google_id = :google_id;
