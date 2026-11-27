#!/usr/bin/env python3
"""pfiles-expand.py -- expand the p-files for ONE edition into its own directory.

Step 2 in CI ("Expansion -- committed output must match") did this with a
shell loop that expanded in place and then compared `git diff`. That only
works for one edition at a time: expanding 20.0 in place overwrites the 18.0
files, and the next edition is compared against the wrong content.

This script therefore expands into a SEPARATE directory (--out) and compares
it against the working tree. Two editions can then run one after another
without touching each other.

Usage:
    .github/pfiles-expand.py --repo . --version 20.0 --out /tmp/x20
    .github/pfiles-expand.py --repo . --version 20.0 --out /tmp/x20 --quiet
    .github/pfiles-expand.py --repo . --version 20.0 --out /tmp/x20 --json

Output: one line per deviation on stdout (or JSON with --json).
Diagnostics on stderr.

Exitkoder:
    0  all committed output matches the p-files for that edition
    1  deviation (output is stale) -- the list names the files
    2  invalid usage
    5  environment error (preprocess missing, directory not writable)
"""

import argparse
import filecmp
import json
import os
import shutil
import subprocess
import sys

# Same extensions as the hook expands. .kpf/.xul are in the hook's list but
# are not used in Vertel's repos; they are skipped here because preprocess
# does not support them, and a file we cannot expand is an error we cannot
# fix.
EXTENSIONS = [".py", ".xml", ".js", ".csv", ".sh", ".html", ".htm"]

EXCLUDED_DIRS = {".git", "__pycache__", ".tox", ".venv", "venv", "node_modules",
                 ".idea", ".mypy_cache", ".pytest_cache"}


def die(msg, code):
    print("pfiles-expand: %s" % msg, file=sys.stderr)
    sys.exit(code)


def pfiles(repo):
    """Every p-file in the repo, as relative paths."""
    found = []
    for root, dirs, files in os.walk(repo):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        for name in files:
            if any(name.endswith(".p" + ext) for ext in EXTENSIONS):
                found.append(os.path.relpath(os.path.join(root, name), repo))
    return sorted(found)


def output_name(pfile):
    """a/b.p.py -> a/b.py. '.p' sits before the extension."""
    for ext in EXTENSIONS:
        if pfile.endswith(".p" + ext):
            return pfile[: -len(".p" + ext)] + ext
    return pfile  # cannot happen; pfiles() filters


def main():
    ap = argparse.ArgumentParser(description="Expand p-files for one edition.")
    ap.add_argument("--repo", default=".", help="repo att expandera ur")
    ap.add_argument("--version", required=True, help="edition, e.g. 20.0")
    ap.add_argument("--out", required=True, help="katalog att expandera till")
    ap.add_argument("--quiet", action="store_true", help="bara avvikelser")
    ap.add_argument("--json", action="store_true", help="JSON-utdata")
    ap.add_argument("--allow-missing-preprocess", action="store_true",
                    help="skip with exit 0 instead of an environment error")
    args = ap.parse_args()

    preprocess = shutil.which(os.environ.get("PFILES_PREPROCESS", "preprocess"))
    if not preprocess:
        if args.allow_missing_preprocess:
            print("pfiles-expand: preprocess not in PATH -- skipping", file=sys.stderr)
            return 0
        die("preprocess not in PATH (environment error, not a module error)", 5)

    repo = os.path.abspath(args.repo)
    sources = pfiles(repo)
    if not args.quiet:
        print("pfiles-expand: %d p-files, edition %s" % (len(sources), args.version), file=sys.stderr)

    stale, errors = [], []

    # Copy the whole module directories first. The expansion below only
    # writes the files that HAVE a p-file -- modules consisting solely of
    # generated output (or of hand-written files with no p-source) would
    # otherwise never reach the output directory, and CI would silently skip
    # them. That is exactly what happened: 4 of 21 modules were tested.
    copied = 0
    for root, dirs, files in os.walk(repo):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        # A module directory is any directory holding a manifest, in either
        # format. Copy it and skip everything beneath it -- a module can
        # contain subdirectories that look like modules but are not.
        if "__manifest__.py" in files or "__manifest__.p.py" in files:
            dest = os.path.join(args.out, os.path.relpath(root, repo))
            shutil.copytree(root, dest, dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            copied += 1
            dirs[:] = []

    for src in sources:
        rel_out = output_name(src)
        outpath = os.path.join(args.out, rel_out)
        os.makedirs(os.path.dirname(outpath) or args.out, exist_ok=True)
        proc = subprocess.run(
            [preprocess, "-f", "-D", "VERSION=%s" % args.version, "-o", outpath,
             os.path.join(repo, src)],
            capture_output=True, text=True,
        )
        if proc.returncode != 0:
            errors.append({"file": src, "stderr": proc.stderr.strip()[:800]})
            continue
        committed = os.path.join(repo, rel_out)
        if not os.path.exists(committed):
            # A p-file without committed output is the coverage check's
            # business, not the expansion's. Here we only compare what
            # exists.
            continue
        if not filecmp.cmp(committed, outpath, shallow=False):
            stale.append(rel_out)

    if args.json:
        print(json.dumps({"version": args.version, "checked": len(sources),
                          "stale": stale, "errors": errors}, ensure_ascii=False))
    else:
        for rel_out in stale:
            print("STALE %s" % rel_out)
        for err in errors:
            print("EXPANSION_ERROR %s" % err["file"])

    if errors:
        if not args.json:
            for err in errors:
                print("--- %s ---\n%s" % (err["file"], err["stderr"]), file=sys.stderr)
        return 1
    return 1 if stale else 0


if __name__ == "__main__":
    sys.exit(main())
