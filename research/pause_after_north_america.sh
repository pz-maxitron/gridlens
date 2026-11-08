#!/bin/bash
# Watches for the moment batch A's driver starts the first country past
# North America (Guatemala, Central America) and kills the driver +
# continuation wrapper immediately -- so the pipeline pauses right after
# North America (US, Canada, Mexico) finishes, for a quality review
# before continuing to the rest of the world.
#
# Usage: bash pause_after_north_america.sh <driver_pid> <continuation_pid>
set -u
DRIVER_PID="${1:?Usage: pause_after_north_america.sh <driver_pid> <continuation_pid>}"
CONT_PID="${2:?Usage: pause_after_north_america.sh <driver_pid> <continuation_pid>}"
cd ~/code/plexos-catalogue-web || exit 1

echo "=== Watching for Guatemala (first Central America country) to start at $(date) ==="
while true; do
  if ! kill -0 "$DRIVER_PID" 2>/dev/null; then
    echo "=== Driver already exited on its own before Guatemala started -- nothing to pause at $(date) ==="
    exit 0
  fi
  if ls research/logs/tools/MTS1-A_Guatemala_*.log >/dev/null 2>&1; then
    echo "=== Guatemala session detected starting at $(date) -- pausing now ==="
    pkill -P "$DRIVER_PID" 2>&1
    kill "$DRIVER_PID" 2>&1
    pkill -P "$CONT_PID" 2>&1
    kill "$CONT_PID" 2>&1
    echo "=== Pipeline paused after North America at $(date). Resume later with: bash research/run_tool_search.sh MTS1-A ==="
    exit 0
  fi
  sleep 5
done
