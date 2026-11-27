#!/usr/bin/env python3
"""pfiles-editions.py -- read .pfiles-ci and emit the editions CI needs.

The workflow needs two things: which editions to run, and which of them
actually have a branch. This script answers both and distinguishes "the
edition is switched off" from "the edition is requested but the branch is
missing" -- the latter is a configuration error, not a broken module.

Usage:
    pfiles-editions.py --repo . --format json
    pfiles-editions.py --repo . --format github-matrix
    pfiles-editions.py --repo . --check        # validation only

Output (--format json):
    {"editions": ["18.0", "19.0", "20.0"], "missing_branches": [], "source": ".pfiles-ci"}

--format github-matrix writes what an actions matrix expects:
    {"edition": ["18.0", "19.0", "20.0"]}

Exit codes:
    0  the configuration is readable and every requested branch exists
    2  invalid usage
    5  configuration error (unknown edition, branch missing, broken syntax)

The script asks git for branches. In CI the checkout is shallow, so the
workflow fetches the branches first (fetch-depth: 0); if they are still
missing the workflow reports that as an environment error, not this script.
"""

import argparse
import json
import os
import re
import subprocess
import sys

# Same set as EDITION_PROFILES in pfiles-check.py. An edition missing there
# would run the coverage check without the format check -- exactly the silent
# half-check we want to avoid.
KNOWN_EDITIONS = ["18.0", "19.0", "20.0"]

DEFAULT_SOURCE = ".pfiles-ci"

# The repositories the modules depend on, from 'deps:' in .pfiles-ci. Filled
# in by parse_config() and emitted in the JSON output so the workflow can
# clone them.
DEPENDENCIES = []
EDITION_RE = re.compile(r"^\d{2}\.0$")


def fail(msg, code=5):
    print("pfiles-editions: %s" % msg, file=sys.stderr)
    sys.exit(code)


def parse_config(path):
    """Return the list of editions from .pfiles-ci, or None if the file is absent."""
    if not os.path.exists(path):
        return None
    editions = []
    deps = []
    with open(path, encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, 1):
            line = raw.split("#", 1)[0].strip()
            if not line:
                continue
            if ":" not in line:
                fail("%s:%d: expected 'key: value', got %r" % (path, lineno, line))
            key, value = line.split(":", 1)
            key, value = key.strip(), value.strip()
            if key == "deps":
                # The repositories the modules depend on. Cloned by the
                # workflow before the modules are tested -- otherwise they are
                # "uninstallable" for a false reason, because the neighbour
                # simply is not on the addons path.
                deps.extend(p for p in re.split(r"[\s,]+", value) if p)
                continue
            if key != "editions":
                # pfiles-ci: 1 is a format marker, not an edition.
                continue
            parts = [p for p in re.split(r"[\s,]+", value) if p]
            if not parts:
                fail("%s:%d: 'editions:' is empty" % (path, lineno))
            for part in parts:
                if not EDITION_RE.match(part):
                    fail(
                        "%s:%d: %r is not an edition (expected e.g. 18.0)"
                        % (path, lineno, part)
                    )
                editions.append(part)
    if not editions:
        fail("%s: ingen 'editions:'-rad hittades" % path)
    DEPENDENCIES[:] = deps
    # Keep the order but drop duplicates.
    seen, unique = set(), []
    for e in editions:
        if e not in seen:
            seen.add(e)
            unique.append(e)
    return unique


def branches(repo):
    """Local and remote-tracking branch names, without the 'origin/' prefix."""
    try:
        out = subprocess.run(
            ["git", "-C", repo, "for-each-ref", "--format=%(refname:short)", "refs/heads", "refs/remotes"],
            capture_output=True, text=True, check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        fail("could not read branches from %s: %s" % (repo, exc))
    names = set()
    for line in out.splitlines():
        line = line.strip()
        if not line or line.endswith("/HEAD"):
            continue
        names.add(line.rsplit("/", 1)[-1])
    return names


def main():
    ap = argparse.ArgumentParser(description="Read .pfiles-ci and emit the editions.")
    ap.add_argument("--repo", default=".", help="repository to read the configuration from")
    ap.add_argument("--source", default=DEFAULT_SOURCE, help="konfigurationsfil (default .pfiles-ci)")
    ap.add_argument("--format", choices=["json", "github-matrix", "lines"], default="json")
    ap.add_argument("--check", action="store_true", help="validera och avsluta (inget matrisutdata)")
    ap.add_argument(
        "--allow-missing-branches",
        action="store_true",
        help="report missing branches but exit 0 (for local runs)",
    )
    args = ap.parse_args()

    path = os.path.join(args.repo, args.source)
    configured = parse_config(path)
    source = args.source if configured is not None else "<default>"

    have = branches(args.repo)

    if configured is None:
        # No configuration file: derive from the edition branches that
        # actually exist in the repo. A repo with only 18.0 then runs 18.0
        # without anyone writing a configuration (spec: "Repo with fewer
        # editions"). Assuming every known edition instead would fail every
        # such repo on a branch that never existed.
        configured = [e for e in KNOWN_EDITIONS if e in have]
        if not configured:
            fail(
                "no .pfiles-ci and no edition branch (18.0/19.0/20.0) found "
                "in %s -- cannot determine which editions to run" % args.repo
            )

    unknown = [e for e in configured if e not in KNOWN_EDITIONS]
    if unknown:
        fail(
            "edition %s is not known to pfiles-check.py (known: %s)"
            % (", ".join(unknown), ", ".join(KNOWN_EDITIONS))
        )

    missing = [e for e in configured if e not in have]

    result = {"editions": configured, "missing_branches": missing,
              "deps": DEPENDENCIES, "source": source}

    if args.format == "github-matrix":
        print(json.dumps({"edition": configured}))
    elif args.format == "lines":
        for edition in configured:
            print(edition)
    else:
        print(json.dumps(result, ensure_ascii=False))

    if missing and not args.allow_missing_branches:
        fail(
            "edition %s is configured in %s but the branch does not exist -- "
            "remove the edition from %s or create the branch. "
            "This is a configuration error, not a broken module."
            % (", ".join(missing), source, source)
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
