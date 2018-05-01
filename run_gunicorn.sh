#!/bin/bash
cd "source"
if [[ "$DB_ADAPTER" == "mysql" ]]; then
    gunicorn --bind 0.0.0.0:5000 wsgi_mysql:app_mysql
elif [[ "$DB_ADAPTER" == "cassandra" ]]; then
    gunicorn --bind 0.0.0.0:5000 wsgi_cassandra:app_cassandra
elif [[ "$DB_ADAPTER" == "mongodb" ]]; then
    gunicorn --bind 0.0.0.0:5000 wsgi:app
else
    gunicorn --bind 0.0.0.0:5000 wsgi:app
fi