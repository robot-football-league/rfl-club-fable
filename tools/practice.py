"""Play a practice match for AFC Fable.

Lives in tools/ (scrutineering-exempt) because its imports are outside the
match-code allowlist; the club root must stay lint-clean.

    ../rfl-engine/.venv/bin/python tools/practice.py --time 90
    ../rfl-engine/.venv/bin/python tools/practice.py --video out.mp4
    ../rfl-engine/.venv/bin/python tools/practice.py --opponent tools/sparring/chaser

Needs the rfl-engine package importable (run with the engine repo's venv).
Our players are code, so practice costs $0 in model tokens.
"""

import argparse
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--time", type=float, default=60.0)
    ap.add_argument("--video", default=None)
    ap.add_argument("--opponent", default=None,
                    help="path to another team dir (default: mirror match)")
    ap.add_argument("--halves", type=int, default=1)
    ap.add_argument("--out", default="runs/practice")
    args = ap.parse_args()

    club = Path(__file__).resolve().parents[1]      # the club repo root
    other = Path(args.opponent).resolve() if args.opponent else club
    from gauntlet.rfl import run_rfl_match
    res = run_rfl_match(str(club), str(other), match_time_s=args.time,
                        halves=args.halves,
                        video_path=args.video, log_dir=args.out)
    print(f"final score: {res.score[0]} - {res.score[1]}")
    print(f"logs: {args.out}/")


if __name__ == "__main__":
    main()
