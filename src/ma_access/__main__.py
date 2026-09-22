import argparse
from pathlib import Path

from .analysis import analyze
from .pipeline import build
from .sources import fetch


def main():
    parser = argparse.ArgumentParser(description="Massachusetts county primary-care investigation screen")
    parser.add_argument("command", choices=["fetch", "run", "dashboard", "memo"])
    parser.add_argument(
        "--root", type=Path, default=Path("."), help="Repository root with data/source_register.json"
    )
    args = parser.parse_args()
    root = args.root
    if args.command == "fetch":
        fetch(root)
        print("Pinned source downloads and Massachusetts slices verified")
        return
    if args.command in ["run", "dashboard"]:
        rows, features = build(root)
        result = analyze(rows, root / "analysis")
        if args.command == "dashboard":
            from .dashboard import create

            create(root, rows, features)
        print("Baseline investigation shortlist: " + ", ".join(result["baseline_shortlist"]))
    if args.command == "memo":
        from .memo import create_memo

        create_memo(root)
        print("Two-page decision memo written to docs/decision_memo.pdf")


if __name__ == "__main__":
    main()
