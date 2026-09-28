#!/bin/sh
# Runs the backend test suite against a throwaway MySQL 8.0 container (the same image production
# uses) instead of the default in-memory SQLite, to catch MySQL-specific behavior. The container
# lives in tmpfs and is removed on exit. Extra args are passed to pytest:
#
#   scripts/test-mysql.sh                       # whole suite
#   scripts/test-mysql.sh tests/integration -v  # just the integration tests
set -eu

cd "$(dirname "$0")/../backend"

NAME="media-database-test-mysql-$$"
PORT="${TEST_MYSQL_PORT:-13306}"
PASSWORD="test"

cleanup() { docker rm -f "$NAME" >/dev/null 2>&1 || true; }
trap cleanup EXIT INT TERM

docker run -d --name "$NAME" -p "127.0.0.1:${PORT}:3306" --tmpfs /var/lib/mysql \
  -e MYSQL_ROOT_PASSWORD="$PASSWORD" -e MYSQL_DATABASE=media_database_test \
  mysql:8.0 >/dev/null

printf 'waiting for MySQL'
i=0
until docker exec "$NAME" mysql -uroot -p"$PASSWORD" -e 'SELECT 1' media_database_test >/dev/null 2>&1; do
  i=$((i + 1))
  [ "$i" -lt 90 ] || { echo " timed out"; docker logs "$NAME" | tail -20; exit 1; }
  printf '.'
  sleep 1
done
echo " ready"

TEST_DATABASE_URL="mysql+pymysql://root:${PASSWORD}@127.0.0.1:${PORT}/media_database_test" \
  .venv/bin/pytest "${@:-tests/}"
