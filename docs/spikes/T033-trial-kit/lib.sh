# Sourced by the kit's scripts once `prepare.sh` has copied them into <kit>/bin.
# Throwaway trial tooling for T033; not part of taskrail.
KIT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
TASKRAIL_SRC="$KIT/taskrail"

run_dir() {
  case "${1:-}" in
    ''|*/*|.*) echo "invalid run name: '${1:-}' (use e.g. claude or opencode)" >&2; exit 2 ;;
  esac
  printf '%s\n' "$KIT/runs/$1"
}

utc() { date -u +%Y%m%dT%H%M%SZ; }
