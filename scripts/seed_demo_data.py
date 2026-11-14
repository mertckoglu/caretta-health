"""Generate the demo mission dataset and (optionally) load it into the database.

Examples
--------
Write the reproducible sample CSV shipped in the repo::

    python scripts/seed_demo_data.py --csv data/sample_mission_30d.csv --start 2026-10-16 --single

Load a 4-person crew mission ending today into the SQLite DB used by the app/API::

    python scripts/seed_demo_data.py --db --reset

Load the shipped CSV into the DB, shifted so that its last day is today::

    python scripts/seed_demo_data.py --from-csv data/sample_mission_30d.csv --db --reset
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402

from app.api import db  # noqa: E402
from app.core.simulate import simulate_crew, simulate_mission  # noqa: E402
from app.core.thresholds import ENVIRONMENTS  # noqa: E402


def shift_to_today(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["ts"] = pd.to_datetime(df["ts"])
    delta = pd.Timestamp(date.today()) - df["ts"].max().normalize()
    df["ts"] = df["ts"] + delta
    return df


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--days", type=int, default=30)
    p.add_argument("--environment", default="iss", choices=sorted(ENVIRONMENTS))
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--start", type=date.fromisoformat, help="first mission day (default: ends today)")
    p.add_argument("--single", action="store_true", help="only the commander (CDR) instead of a 4-person crew")
    p.add_argument("--csv", type=Path, help="write the generated data to this CSV")
    p.add_argument("--from-csv", type=Path, help="load an existing CSV instead of simulating")
    p.add_argument("--db", action="store_true", help="insert into the SQLite DB (CARETTA_DB or data/caretta.db)")
    p.add_argument("--reset", action="store_true", help="delete existing readings of the same crew first")
    args = p.parse_args(argv)

    if args.from_csv:
        df = shift_to_today(pd.read_csv(args.from_csv))
    elif args.single:
        df = simulate_mission(args.days, "CDR", args.environment, args.seed, args.start)
    else:
        df = simulate_crew(days=args.days, environment=args.environment, seed=args.seed, start=args.start)

    if args.csv:
        args.csv.parent.mkdir(parents=True, exist_ok=True)
        out = df.copy()
        out["ts"] = pd.to_datetime(out["ts"]).dt.strftime("%Y-%m-%dT%H:%M:%S")
        out[["ts", "astronaut_id", "environment", "indicator", "value"]].to_csv(args.csv, index=False)
        print(f"wrote {len(out)} rows to {args.csv}")

    if args.db:
        conn = db.connect()
        if args.reset:
            for (a, env), _ in df.groupby(["astronaut_id", "environment"]):
                db.delete_astronaut(conn, a, env)
        n = db.insert_dataframe(conn, df)
        print(f"inserted {n} readings into {db.db_path()}")

    if not args.csv and not args.db:
        print(df.head(20).to_string(index=False))
        print("… (use --csv and/or --db to save)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
