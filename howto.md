# How-to

## Postgres database

- `psql DATABASE_URL` to connect to the database
- `\dt` to see all tables
- `\d chat_history` to see the table schema

## Environment variables

- Run `heroku config:get TOKEN_NAME` to get environment variables
- To test locally put them in .env in the format `TOKEN_NAME=value`

## Heroku

- `heroku logs --tail` to see logs
- `heroku ps` to see dynos
- `heroku ps:scale worker=1` to start up the worker dyno
- `heroku ps:scale worker=0` to stop the worker dyno
