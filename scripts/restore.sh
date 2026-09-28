#!/bin/sh
# Restores a backup produced by backup-loop.sh into the production database.
#
#   scripts/restore.sh backups/media_database-20260928T030000Z.sql.gz
#
# This REPLACES the current contents of the media_database schema. Run from the repo root.
set -eu

if [ $# -ne 1 ] || [ ! -f "$1" ]; then
  echo "usage: $0 <backup .sql.gz file>" >&2
  exit 1
fi

COMPOSE="${COMPOSE:-docker compose -f docker-compose.prod.yml}"

printf 'This will overwrite the production database with %s. Type "restore" to continue: ' "$1"
read -r answer
[ "$answer" = "restore" ] || { echo "aborted"; exit 1; }

gunzip -c "$1" | $COMPOSE exec -T db sh -c 'MYSQL_PWD="$MYSQL_PASSWORD" mysql -u media_database media_database'
echo "restored $1"
