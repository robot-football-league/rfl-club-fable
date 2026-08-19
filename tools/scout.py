"""Scout a match from its public logs (or our own practice runs).

    python3 tools/scout.py <match_dir> [--side A|B]

Reads match.json + telemetry.jsonl (and decisions.jsonl when present) and
prints the numbers that decided founding night's iteration:

  - score, goals, falls, event mix
  - territory (ball thirds) and nearest-to-ball share
  - PUSH EFFECTIVENESS: net ball x-advance while each robot is the nearest
    within contact range. This is the stat that caught Hare shoving the
    ball backwards (-5 m) on founding night.
  - radio transcript summary

--side flips the advance sign convention (A attacks +x, B attacks -x).
No engine imports; works on any match dir in ../rfl-league-data too.
"""

import argparse
import json
import math
from collections import Counter
from pathlib import Path


def load_jsonl(p):
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("match_dir")
    ap.add_argument("--side", default="A", choices=("A", "B"),
                    help="which team's perspective for +advance (default A)")
    args = ap.parse_args()
    d = Path(args.match_dir)

    m = json.loads((d / "match.json").read_text())
    teams = m.get("teams") or {}
    names = {k: (v.get("name", k) if isinstance(v, dict) else str(v))
             for k, v in teams.items()}
    players = {}
    for side in ("A", "B"):
        t = teams.get(side) or {}
        for j, pn in enumerate(t.get("players") or []):
            players[(side, j)] = pn

    def rname(i):
        side = "A" if i < 2 else "B"
        return players.get((side, i % 2), f"r{i}")

    print(f"{names.get('A','A')} {m['score'][0]} - {m['score'][1]} "
          f"{names.get('B','B')}   (halves: {m.get('halves')})")
    for g in m.get("goals", []):
        print(f"  goal {g['t']:6.1f}s  team {g['team']}  scorer "
              f"{rname(g.get('scorer', -1)) if g.get('scorer') is not None else '?'}")
    if m.get("dropped_balls"):
        print(f"  dropped balls: {m['dropped_balls']}")
    print("  events:", dict(Counter(e["kind"] for e in m.get("events", []))))
    print("  falls:", {rname(i): r.get("falls", 0)
                       for i, r in enumerate(m.get("robots", []))})

    tel = load_jsonl(d / "telemetry.jsonl")
    if tel:
        sgn = 1.0 if args.side == "A" else -1.0
        thirds = Counter()
        near = Counter()
        push = Counter()
        contact = Counter()
        for a, b in zip(tel, tel[1:]):
            bx, by = a["ball"]
            x = sgn * bx
            thirds["ours" if x < -2.33 else "mid" if x < 2.33 else "theirs"] += 1
            dists = [math.hypot(r[0] - bx, r[1] - by) for r in a["robots"]]
            i = dists.index(min(dists))
            near[i] += 1
            if dists[i] < 0.9:
                adv = (b["ball"][0] - bx) * (1.0 if i < 2 else -1.0)
                push[i] += adv          # + means toward the goal THEY attack
                contact[i] += 1
        print("  ball thirds (side %s view): %s" % (args.side, dict(thirds)))
        print("  nearest-ball share:",
              {rname(i): near[i] for i in sorted(near)})
        print("  push effectiveness (net m toward own target while in contact):")
        for i in sorted(contact):
            print(f"    {rname(i):14s} {push[i]:+6.2f} m over "
                  f"{contact[i]} contact ticks")

    comms = load_jsonl(d / "comms.jsonl")
    if comms:
        said = [c for c in comms if "text" in c]
        supp = len(comms) - len(said)
        print(f"  radio: {len(said)} delivered, {supp} suppressed")
        for c in said[:12]:
            print(f"    {c['t']:6.1f}s  {c.get('team','?'):20s} #{c.get('number')}"
                  f"  {c['text']}")
        if len(said) > 12:
            print(f"    ... and {len(said) - 12} more")


if __name__ == "__main__":
    main()
