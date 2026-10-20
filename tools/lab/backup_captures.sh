#!/bin/sh
# backup_captures.sh — copy the gitignored lab/captures/ and lab/inbox/ to iCloud Drive.
#
# Usage: tools/lab/backup_captures.sh [--dry-run]
#
# The destination is one config value (below), overridable with $LAB_BACKUP_DIR.
# $LAB_REPO overrides the repo root that holds lab/ (for tests).
# This is a one-way, additive copy: it never deletes anything at the destination
# (no --delete), so a file removed locally is kept in the backup. Files changed
# locally overwrite their backup copy.
#
# Exit codes: 0 done, 1 iCloud root or source missing, 2 usage error, other = rsync's.

# ---- config -----------------------------------------------------------------
ICLOUD_ROOT="${HOME}/Library/Mobile Documents/com~apple~CloudDocs"
BACKUP_DIR="${LAB_BACKUP_DIR:-${ICLOUD_ROOT}/motion-play-lab}"
# -----------------------------------------------------------------------------

set -u

DRY=""
case "${1:-}" in
  "") ;;
  --dry-run|-n) DRY="--dry-run" ;;
  -h|--help) sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
  *) echo "backup: unknown argument: $1 (only --dry-run)" >&2; exit 2 ;;
esac
[ $# -le 1 ] || { echo "backup: too many arguments" >&2; exit 2; }

REPO="${LAB_REPO:-$(cd "$(dirname "$0")/../.." && pwd)}" || exit 1

# The iCloud root must exist unless the destination was overridden elsewhere.
case "$BACKUP_DIR" in
  "$ICLOUD_ROOT"/*)
    if [ ! -d "$ICLOUD_ROOT" ]; then
      echo "backup: iCloud Drive root not found: $ICLOUD_ROOT" >&2
      echo "backup: turn on iCloud Drive (System Settings → Apple Account → iCloud → iCloud Drive)," >&2
      echo "backup: or set LAB_BACKUP_DIR to another folder. Nothing was copied." >&2
      exit 1
    fi ;;
  *)
    parent="$(dirname "$BACKUP_DIR")"
    if [ ! -d "$parent" ]; then
      echo "backup: destination parent not found: $parent. Nothing was copied." >&2
      exit 1
    fi ;;
esac

status=0
for sub in captures inbox; do
  src="$REPO/lab/$sub"
  if [ ! -d "$src" ]; then
    echo "backup: skip lab/$sub/ (not present)"
    continue
  fi
  dst="$BACKUP_DIR/$sub"
  if [ -z "$DRY" ]; then mkdir -p "$dst" || exit 1; fi
  echo "backup: lab/$sub/ -> $dst/${DRY:+ (dry run)}"
  # -a keeps times/permissions; -i lists each file sent. Trailing slashes copy contents.
  rsync -a -i $DRY "$src/" "$dst/" || status=$?
done

if [ "$status" -ne 0 ]; then
  echo "backup: rsync failed (exit $status)" >&2
  exit "$status"
fi
echo "backup: ${DRY:+dry run }done -> $BACKUP_DIR"
