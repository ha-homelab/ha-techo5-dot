#!/bin/sh
# Run only through deploy_daemon.py with an existing SSH administrator key.
set -eu
BB=/bin/busybox.static
JOB=$1
MODE=$2
. "$JOB/params"
if [ "$#" -ge 4 ]; then
  [ "$OLD" = "$3" ] && [ "$NEW" = "$4" ]
fi
TARGET=/usr/local/bin/echod
HOLD=/run/techo5/hold
LOCK=/run/techo5/myshka-maintenance
hash() { "$BB" sha256sum "$1" | "$BB" cut -d ' ' -f 1; }
state() { printf '%s\n' "$1" > "$JOB/state.tmp"; "$BB" mv "$JOB/state.tmp" "$JOB/state"; }
owned_hold() { [ -f "$HOLD" ] && [ "$("$BB" cat "$HOLD")" = "$JOB" ]; }
release_hold() { if owned_hold; then "$BB" rm "$HOLD"; fi; }
process() {
  PIDS=$("$BB" pidof echod || true)
  set -- $PIDS
  [ "$#" = 1 ] || return 1
  PID=$1
  [ "$(hash /proc/$PID/exe)" = "$NEW" ]
}
finish_lock() {
  if [ -f "$LOCK/owner" ] && [ "$("$BB" cat "$LOCK/owner")" = "$JOB" ]; then
    "$BB" rm "$LOCK/owner"
    "$BB" rmdir "$LOCK"
  fi
}
rollback() {
  CURRENT=$(hash "$TARGET")
  if [ "$CURRENT" != "$NEW" ] && [ "$CURRENT" != "$OLD" ]; then
    state rollback_refused_unexpected_binary
    release_hold
    finish_lock
    return 1
  fi
  [ "$(hash "$JOB/echod.previous")" = "$OLD" ] || { state rollback_invalid_backup; return 1; }
  if [ "$CURRENT" = "$NEW" ]; then
    "$BB" cp "$JOB/echod.previous" "$TARGET.rollback-$ID"
    "$BB" chmod 755 "$TARGET.rollback-$ID"
    [ "$(hash "$TARGET.rollback-$ID")" = "$OLD" ] || return 1
    "$BB" mv "$TARGET.rollback-$ID" "$TARGET"
    "$BB" sync
  fi
  release_hold
  if process; then state rollback_staged_restart_required; else state rollback_file_restored; fi
  "$BB" rm -f "$JOB/echod.next"
  # A user may have started a call. Never kill a process during timed rollback.
  finish_lock
}
case "$MODE" in
  apply)
    [ ! -e "$HOLD" ]
    [ -f "$TARGET" ] && [ ! -L "$TARGET" ]
    [ "$(hash "$TARGET")" = "$OLD" ]
    [ "$(hash "$JOB/echod.next")" = "$NEW" ]
    ! "$BB" awk '$2=="/usr/local/bin/echod" { found=1 } END { exit !found }' /proc/mounts
    PIDS=$("$BB" pidof echod)
    set -- $PIDS
    [ "$#" = 1 ]
    PREVIOUS_PID=$1
    [ "$(hash /proc/$PREVIOUS_PID/exe)" = "$OLD" ]
    "$BB" mkdir "$LOCK"
    printf '%s\n' "$JOB" > "$LOCK/owner"
    trap 'release_hold; finish_lock' EXIT HUP INT TERM
    "$BB" cp "$TARGET" "$JOB/echod.previous"
    [ "$(hash "$JOB/echod.previous")" = "$OLD" ]
    "$BB" cp "$JOB/echod.next" "$TARGET.next-$ID"
    "$BB" chmod 755 "$TARGET.next-$ID"
    [ "$(hash "$TARGET.next-$ID")" = "$NEW" ]
    "$BB" sync
    ( set -C; printf '%s\n' "$JOB" > "$HOLD" )
    "$BB" date +%s > "$JOB/started"
    "$BB" nohup "$BB" sh "$JOB/maintenance.sh" "$JOB" watch </dev/null >"$JOB/watchdog.log" 2>&1 &
    WATCH=$!
    "$BB" kill -0 "$WATCH"
    trap 'release_hold' EXIT HUP INT TERM
    [ "$(hash "$TARGET")" = "$OLD" ]
    state replacing
    "$BB" mv "$TARGET.next-$ID" "$TARGET"
    "$BB" sync
    [ "$(hash /proc/$PREVIOUS_PID/exe)" = "$OLD" ]
    "$BB" kill -TERM "$PREVIOUS_PID"
    N=0
    while [ -e "/proc/$PREVIOUS_PID/exe" ] && [ "$N" -lt 15 ]; do
      "$BB" sleep 1; N=$((N+1))
    done
    [ ! -e "/proc/$PREVIOUS_PID/exe" ]
    release_hold
    state awaiting_health_ack
    trap - EXIT HUP INT TERM
    ;;
  watch)
    "$BB" sleep 180
    if [ -f "$JOB/ack" ] && [ "$("$BB" cat "$JOB/ack")" = "$NEW" ]; then
      state confirmed
      finish_lock
    else
      rollback
    fi
    ;;
  ack)
    [ "$(hash "$TARGET")" = "$NEW" ]
    process
    [ ! -e "$HOLD" ]
    NOW=$("$BB" date +%s)
    START=$("$BB" cat "$JOB/started")
    [ "$((NOW-START))" -lt 160 ]
    [ "$("$BB" cat "$JOB/state")" = awaiting_health_ack ]
    printf '%s\n' "$NEW" > "$JOB/ack.tmp"
    "$BB" mv "$JOB/ack.tmp" "$JOB/ack"
    state confirmed
    "$BB" rm -f "$JOB/echod.next"
    ;;
  status)
    "$BB" cat "$JOB/state"
    printf 'installed_sha256=%s\n' "$(hash "$TARGET")"
    if process; then printf 'running_expected=true\n'; else printf 'running_expected=false\n'; fi
    ;;
  *) exit 2 ;;
esac
