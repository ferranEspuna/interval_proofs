#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import subprocess
import zipfile
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LATEX_DIR = PROJECT_ROOT / "latex"
PDF_DIR = PROJECT_ROOT / "pdf"
BUILD_DIR = PROJECT_ROOT / "build"
DIST_DIR = PROJECT_ROOT / "dist"
GENERATED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "build",
    "dist",
    "pdf",
}


@dataclass(frozen=True)
class LatexTarget:
    name: str
    tex_file: str
    output_pdf: str

    @property
    def tex_path(self) -> Path:
        return PROJECT_ROOT / self.tex_file

    @property
    def output_path(self) -> Path:
        return PROJECT_ROOT / self.output_pdf

    @property
    def stem(self) -> str:
        return self.tex_path.stem


def discover_targets() -> dict[str, LatexTarget]:
    targets = {}
    for tex_path in sorted(LATEX_DIR.glob("*.tex")):
        name = tex_path.stem
        targets[name] = LatexTarget(
            name,
            str(tex_path.relative_to(PROJECT_ROOT)),
            str((PDF_DIR / f"{name}.pdf").relative_to(PROJECT_ROOT)),
        )
    return targets


TARGETS = discover_targets()


def run(command: list[str], cwd: Path | None = None) -> None:
    print("+ " + " ".join(str(part) for part in command))
    subprocess.run(command, cwd=cwd, check=True)


def ensure_tool(name: str) -> None:
    if shutil.which(name) is None:
        raise SystemExit(
            f"Required executable '{name}' was not found. Install a TeX distribution "
            "with latexmk and pdflatex available on PATH."
        )


def clean() -> None:
    for path in (BUILD_DIR, DIST_DIR, PDF_DIR):
        if path.exists():
            shutil.rmtree(path)


def prepare_build_dir(target: LatexTarget) -> Path:
    target_build_dir = BUILD_DIR / "latex" / target.name
    target_build_dir.mkdir(parents=True, exist_ok=True)
    tex_root = target.tex_path.parent
    for source_dir in (path for path in tex_root.rglob("*") if path.is_dir()):
        rel = source_dir.relative_to(tex_root)
        if any(part in GENERATED_DIRS for part in rel.parts):
            continue
        (target_build_dir / rel).mkdir(parents=True, exist_ok=True)
    return target_build_dir


def build_target(target: LatexTarget) -> Path:
    ensure_tool("latexmk")
    target_build_dir = prepare_build_dir(target)
    target.output_path.parent.mkdir(parents=True, exist_ok=True)

    run(
        [
            "latexmk",
            "-pdf",
            "-interaction=nonstopmode",
            "-halt-on-error",
            "-file-line-error",
            f"-outdir={target_build_dir}",
            target.tex_path.name,
        ],
        cwd=target.tex_path.parent,
    )

    built_pdf = target_build_dir / f"{target.stem}.pdf"
    shutil.copy2(built_pdf, target.output_path)
    print(f"Wrote {target.output_path.relative_to(PROJECT_ROOT)}")
    return target.output_path


def should_package(path: Path) -> bool:
    rel = path.relative_to(PROJECT_ROOT)
    excluded_dirs = GENERATED_DIRS
    return not any(part in excluded_dirs for part in rel.parts)


def package_release(pdf_paths: list[Path]) -> Path:
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = DIST_DIR / f"{PROJECT_ROOT.name}-release.zip"
    if zip_path.exists():
        zip_path.unlink()

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for pdf_path in pdf_paths:
            archive.write(pdf_path, Path("pdfs") / pdf_path.name)

        for path in PROJECT_ROOT.rglob("*"):
            if not path.is_file() or not should_package(path):
                continue
            rel = path.relative_to(PROJECT_ROOT)
            archive.write(path, Path("source") / rel)

    print(f"Wrote {zip_path.relative_to(PROJECT_ROOT)}")
    return zip_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build LaTeX PDFs.")
    parser.add_argument(
        "--target",
        choices=sorted(TARGETS),
        action="append",
        help="Build one target. May be passed multiple times. Defaults to all targets.",
    )
    parser.add_argument(
        "--package",
        action="store_true",
        help="Create dist/<repo>-release.zip with PDFs and buildable source.",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove generated outputs before building.",
    )
    parser.add_argument(
        "--clean-only",
        action="store_true",
        help="Remove generated outputs and exit.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.clean or args.clean_only:
        clean()
    if args.clean_only:
        return

    if not TARGETS:
        raise SystemExit("No LaTeX files found in latex/.")

    target_names = args.target or list(TARGETS)
    pdf_paths = [build_target(TARGETS[name]) for name in target_names]

    if args.package:
        package_release(pdf_paths)


if __name__ == "__main__":
    main()
