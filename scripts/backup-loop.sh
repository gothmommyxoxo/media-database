#!/bin/sh
# Runs inside the `backup` service (docker-compose.prod.yml): takes a mysqldump once at startup and
# then every 24h into /backups (a host directory — Section 11.4's off-container storage), pruning
# dumps older than BACKUP_RETENTION_DAYS. Copy ./backups somewhere off the host too; a backup on the
# same disk as the database doesn't survive losing that disk.
set -eu

RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"

dump() {
  stamp="$(date -u +%Y%m%dT%H%M%SZ)"
  target="/backups/media_database-${stamp}.sql.gz"
  # Write to a temp name and rename on success, so a failed dump never looks like a good backup.
  if MYSQL_PWD="$MYSQL_PASSWORD" mysqldump -h db -u media_database \
      --single-transaction --no-tablespaces --routines --triggers media_database \
      | gzip > "${target}.partial"; then
    mv "${target}.partial" "$target"
    echo "backup: wrote $target"
  else
    rm -f "${target}.partial"
    echo "backup: FAILED at $stamp" >&2
  fi
  find /backups -name 'media_database-*.sql.gz' -mtime "+${RETENTION_DAYS}" -delete
}

while true; do
  dump
  sleep 86400
done
