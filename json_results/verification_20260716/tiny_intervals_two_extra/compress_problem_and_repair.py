#!/usr/bin/env python3
"""Deterministically gzip one problem JSON and repair its solution metadata."""

import argparse
import gzip
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("problem_json", type=Path)
    parser.add_argument("solution_json", type=Path)
    args = parser.parse_args()

    compressed_path = args.problem_json.with_suffix(args.problem_json.suffix + ".gz")
    if args.problem_json.exists():
        with args.problem_json.open("rb") as source, compressed_path.open("wb") as target:
            with gzip.GzipFile(fileobj=target, mode="wb", filename="", mtime=0) as archive:
                while chunk := source.read(1024 * 1024):
                    archive.write(chunk)
        args.problem_json.unlink()
    elif not compressed_path.exists():
        raise FileNotFoundError(args.problem_json)

    with args.solution_json.open() as source:
        solution = json.load(source)
    solution["parameters"]["problem_json_path"] = str(compressed_path.resolve())
    with args.solution_json.open("w") as target:
        json.dump(solution, target, indent=2, sort_keys=True)
        target.write("\n")


if __name__ == "__main__":
    main()
