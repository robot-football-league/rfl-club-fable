"""Play a practice match: this team vs a mirror copy of itself.

    python practice.py                     # 60 s, logs only
    python practice.py --video out.mp4     # with the broadcast video
    python practice.py --time 120 --opponent ../some-other-team

Needs the rfl-engine package importable (pip install -e <engine clone>,
or run with the engine repo's venv).
"""

import argparse
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--time", type=float, default=60.0)
    ap.add_argument("--video", default=None)
    ap.add_argument("--opponent", default=None,
                    help="path to another team dir (default: mirror match)")
    ap.add_argument("--out", default="runs/practice")
    args = ap.parse_args()

    here = Path(__file__).resolve().parent
    other = Path(args.opponent).resolve() if args.opponent else here
    from gauntlet.rfl import run_rfl_match
    res = run_rfl_match(str(here), str(other), match_time_s=args.time,
                        video_path=args.video, log_dir=args.out)
    print(f"final score: {res.score[0]} - {res.score[1]}")
    print(f"logs: {args.out}/")


if __name__ == "__main__":
    main()
