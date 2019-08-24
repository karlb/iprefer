export FLASK_APP='iprefer:create_app'
export FLASK_ENV=development
export OAUTHLIB_INSECURE_TRANSPORT=true
flask run --extra-files=iprefer/item.sql:iprefer/user.sql
