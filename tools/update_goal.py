#!/usr/bin/env python3
import argparse
import json
import os


def main():
    parser = argparse.ArgumentParser(description="Update WVAB navigation goal file")
    parser.add_argument("--x", type=float, required=True)
    parser.add_argument("--y", type=float, required=True)
    parser.add_argument("--frame", default="local", choices=["local", "world"])
    parser.add_argument("--path", default="config/goal.json")
    args = parser.parse_args()

    payload = {
        "goal": {"x": float(args.x), "y": float(args.y)},
        "frame": args.frame,
    }

    path = args.path
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"Goal updated: {path} -> ({args.x}, {args.y}) [{args.frame}]")


if __name__ == "__main__":
    main()
