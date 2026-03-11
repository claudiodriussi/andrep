#!/bin/sh
# Create the AndRep sample SQLite database.
# Run from the renderer-python/sample/ directory:
#   sh create_db.sh

DB="$(dirname "$0")/sample.db"

[ -f "$DB" ] && rm "$DB"
sqlite3 "$DB" < "$(dirname "$0")/create_db.sql"
echo "Database created: $DB"
