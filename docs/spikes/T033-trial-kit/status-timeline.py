#!/usr/bin/env python3
"""Print each change in a run's captured `autopilot status --json` files, one line per change.

Usage: status-timeline.py <kit>/runs/<name>/evidence/status
Throwaway analysis helper for T033; not part of taskrail.
"""

import glob
import json
import os
import sys

previous = None
for path in sorted(glob.glob(os.path.join(sys.argv[1], "*.json"))):
    try:
        data = json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError) as error:
        print(os.path.basename(path), "unreadable:", error)
        continue
    cells = []
    for run in data.get("runs", []):
        for task in run.get("tasks", []):
            cell = f'{task["id"]}:{task["state"]}' + (f'@{task["gate"]}' if task.get("gate") else "")
            if task.get("silent"):
                cell += "!silent"
            if task.get("escalation"):
                cell += "!" + "+".join(task["escalation"])
            cells.append(cell)
        handoff = run.get("handoff", {})
        cells.append(f'[{run["id"]} in_review={handoff.get("in_review")} next={handoff.get("next")} '
                     f'merged={run.get("done_merged")} complete={run.get("complete")}]')
    if data.get("overlaps"):
        cells.append("overlaps=" + ",".join(sorted(data["overlaps"])))
    line = " ".join(cells)
    if line != previous:
        print(os.path.basename(path)[:16], line)
        previous = line
