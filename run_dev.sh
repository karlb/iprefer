export FLASK_APP='iprefer:create_app'
export FLASK_ENV=development
export FLASK_RUN_EXTRA_FILES=iprefer/item.sql,iprefer/user.sql
export OAUTHLIB_INSECURE_TRANSPORT=true
flask run
