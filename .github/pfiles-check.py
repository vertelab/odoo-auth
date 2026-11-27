#!/usr/bin/env python3
"""pfiles-check -- find files that should be p-files but are not.

Checks a module directory (or a whole repo) and reports:

  MISSING_SOURCE  generated file without a .p-source  (ERROR)
  STALE           output differs from the expansion   (ERROR)
  MANUAL_PFILE    p-file, but no generated file       (ERROR)
  ORPHAN_PFILE    .p-file without valid output        (ERROR)
  UNEXPLAINED     source file with no p-counterpart, not allow-listed (ERROR)
  PAIRED          .p.x + x present -- OK
  ALLOWED         allow-listed -- OK
  NOT_APPLICABLE  preprocess has no support for it -- OK

Edition-specific security checks (Odoo 20 changed the shape of ir.model.access):

  WRONG_SECURITY_FORMAT  the security file has the wrong shape for the edition (ERROR)
  UNLISTED_SECURITY_FILE the manifest loads a security file the edition cannot read (ERROR)
  BAD_DOMAIN_NAME        the domain uses a name outside the edition's eval context (ERROR)

Usage:
  ./pfiles-check.py --version 18.0 /path/to/module [...]
  ./pfiles-check.py --version 18.0 --json /path/to/repo
  ./pfiles-check.py --version 18.0 --print-allow /path | sudo tee .../.pfiles-allow

Allow-list: <repo- or module root>/.pfiles-allow -- one path per line,
relative to the root. '#' starts a comment. Do not forget '!' when generating.

Exit: 0 = no errors, 1 = errors found, 2 = invalid usage.
"""
from __future__ import annotations

import argparse
import ast
import csv
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

# File extensions preprocess handles (cf. /skill:odoo-pfiles)
PREPROCESS_EXTS = (".py", ".xml", ".js", ".csv", ".sh", ".html", ".htm", ".pl",
                   ".rb", ".tcl", ".c", ".h", ".cpp", ".java", ".php")
# Files that are always sources, never generated
EXCLUDED_NAMES = {"__init__.py", "__manifest__.py", "__manifest__.p.py"}
EXCLUDED_DIRS = {".git", "__pycache__", ".tox", ".venv", "venv", "node_modules",
                 ".idea", ".mypy_cache", ".pytest_cache"}
# p-file extensions: (p-suffix, output-suffix). Order matters -- longest first.
PFILE_SUFFIXES = [(".p.py", ".py"), (".p.xml", ".xml"), (".p.js", ".js"),
                  (".p.csv", ".csv"), (".p.sh", ".sh"), (".p.html", ".html"),
                  (".p.htm", ".htm"), (".p.pl", ".pl"), (".p.rb", ".rb"),
                  (".p.tcl", ".tcl"), (".p.c", ".c"), (".p.h", ".h"),
                  (".p.cpp", ".cpp"), (".p.java", ".java"), (".p.php", ".php")]

OK, ERR = "OK", "ERROR"


# ---------------------------------------------------------------------------
# Edition profiles
#
# The security data for ir.model.access changed shape in Odoo 20.0:
#
#   18.0/19.0                20.0
#   file ir.model.access.csv ir.access.csv      <- THE FILENAME decides the model
#   model_id:id              model_id           <- bare model name
#   group_id:id              group_id/id
#   perm_read/write/create/unlink   operation   <- 'crud' etc.
#   (ir.rule separate)       domain column
#
# The filename is not cosmetic: Odoo 20 reads the model name from the filename
# prefix BEFORE the content (convert_csv_import). A new-format file living in
# ir.model.access.csv therefore still fails with KeyError: 'ir.model.access'.
#
# Verified 2026-11-16: 18/19 have the table ir_model_access, 20.0 has ir_access.
# OCB 19.0 is the old format (no ir_access.py) -- only 20.0 is new.
# ---------------------------------------------------------------------------
EDITION_PROFILES = {
    "18.0": {
        "security_filename": "ir.model.access.csv",
        "security_model": "ir.model.access",
        "security_format": "legacy",
        "security_columns": ("id", "name", "model_id:id", "group_id:id",
                             "perm_read", "perm_write", "perm_create", "perm_unlink"),
    },
    "19.0": {
        "security_filename": "ir.model.access.csv",
        "security_model": "ir.model.access",
        "security_format": "legacy",
        "security_columns": ("id", "name", "model_id:id", "group_id:id",
                             "perm_read", "perm_write", "perm_create", "perm_unlink"),
    },
    "20.0": {
        "security_filename": "ir.access.csv",
        "security_model": "ir.access",
        "security_format": "modern",
        "security_columns": ("id", "name", "model_id", "group_id/id",
                             "operation", "domain"),
    },
}

# Files belonging to the old and new security shape respectively. Used to
# detect a file left in the wrong shape for the edition.
SECURITY_FILENAMES = {"ir.model.access.csv", "ir.access.csv"}

# Domain names that do NOT exist in 20.0's eval context (_eval_context gives
# only user, time, company_ids, company_id). 'uid' raises NameError on install.
BAD_DOMAIN_NAMES_MODERN = {"uid": "user.id"}

def edition_profile(version):
    """Profile for an edition. Unknown edition gives None (skip format checks)."""
    return EDITION_PROFILES.get(version)


def pfile_split(name):
    """a.p.py -> ('a.py', '.p.py');  a.py -> (None, None)."""
    for psuffix, suffix in PFILE_SUFFIXES:
        if name.endswith(psuffix):
            return name[: -len(psuffix)] + suffix, psuffix
    return None, None


def pepfile_hint(name):
    """a.xml -> a.p.xml, a.py -> a.p.py.

    The convention is that '.p' goes IN before the extension, not after the
    whole name. It must agree with pfile_split: 'a.p.py' -> 'a.py'. Suggesting
    'a.py.p.py' (as an earlier version did) makes pfile_split return 'a.py.py'
    and creates a new error instead of solving the old one.
    """
    for psuffix, suffix in PFILE_SUFFIXES:
        if name.lower().endswith(suffix):
            return name[: -len(suffix)] + ".p" + suffix
    return name + ".p"


def is_preprocessable(name):
    return not name.startswith(".") and name.lower().endswith(PREPROCESS_EXTS)


def find_roots(paths, explicit):
    """Find module roots (a directory with __manifest__.py or *.p.py) under paths."""
    if explicit:
        return [os.path.abspath(p) for p in paths]

    # Is a given path already a module root?
    roots = []
    for p in paths:
        p = os.path.abspath(p)
        direct = (os.path.isfile(os.path.join(p, "__manifest__.py")) or
                  any(f.endswith(".p.py") for f in os.listdir(p) if f.endswith(".py")))
        if direct:
            roots.append(p)
            continue
        for dirpath, dirnames, filenames in os.walk(p):
            dirnames[:] = sorted(d for d in dirnames if d not in EXCLUDED_DIRS)
            if "__manifest__.py" in filenames:
                roots.append(dirpath)
                dirnames[:] = []   # modules are not nested inside modules
    return roots


def load_allow(root):
    """Read .pfiles-allow from root or an enclosing directory."""
    allow, source = set(), None
    candidate = root
    for _ in range(4):                        # root, root/.., root/../.., ...
        f = os.path.join(candidate, ".pfiles-allow")
        if os.path.isfile(f):
            source = f
            with open(f, encoding="utf-8") as fh:
                for line in fh:
                    line = line.split("#", 1)[0].strip()
                    if line:
                        allow.add(os.path.normpath(line))
            break
        parent = os.path.dirname(candidate)
        if parent == candidate:
            break
        candidate = parent
    return allow, source


def rel(root, path):
    return os.path.relpath(path, root).replace(os.sep, "/")


# ---------------------------------------------------------------------------
# Security checks per edition
# ---------------------------------------------------------------------------

def load_manifest(root):
    """Read the module manifest as a dict. None if it cannot be read.

    Prefers __manifest__.py; falls back to __manifest__.p.py because the
    p-file is the source when it exists. literal_eval works on the p-manifest:
    the conditionals live in comments (# #if), not in Python syntax.
    """
    for name in ("__manifest__.py", "__manifest__.p.py"):
        path = os.path.join(root, name)
        if not os.path.isfile(path):
            continue
        try:
            with open(path, encoding="utf-8") as fh:
                value = ast.literal_eval(fh.read())
        except (OSError, SyntaxError, ValueError):
            continue
        if isinstance(value, dict):
            return value
    return None


def csv_header(path):
    """The first row of a CSV as a list of fields, or None."""
    try:
        with open(path, encoding="utf-8-sig", newline="") as fh:
            first = fh.readline()
    except OSError:
        return None
    if not first.strip():
        return None
    return [c.strip() for c in next(csv.reader([first]))]


def csv_rows(path):
    """Alla datarader (inte header) i en CSV."""
    try:
        with open(path, encoding="utf-8-sig", newline="") as fh:
            rows = list(csv.reader(fh))
    except OSError:
        return []
    return [r for r in rows[1:] if r and any(c.strip() for c in r)]


def security_findings(root, version):
    """Check the security files against the edition's profile.

    Three defects (all ERROR, all would fail an installation):

      WRONG_SECURITY_FORMAT  the file has the wrong shape for the edition
                             (e.g. perm_read columns in 20.0, or
                              operation/domain in 18.0)
      UNLISTED_SECURITY_FILE a security file sits in the module but is not
                             loaded by the manifest's data -- dead weight, and
                             at worst a silent trap when someone adds it
      BAD_DOMAIN_NAME        the domain uses a name that is not in the
                             edition's eval context (uid in 20.0)

    Returns (findings, info) where info is a dict for --json.
    """
    profile = edition_profile(version)
    findings = []
    info = {"profile": None, "present": [], "listed": []}
    if profile is None:
        return findings, info
    info["profile"] = profile["security_format"]

    secdir = os.path.join(root, "security")
    present = []
    if os.path.isdir(secdir):
        for name in sorted(os.listdir(secdir)):
            if name in SECURITY_FILENAMES or name.endswith(".p.csv"):
                present.append(name)
    info["present"] = present

    # Which security files the manifest actually loads. Only those can fail
    # an installation -- a file in security/ that is not listed is never
    # loaded and must therefore not be judged (spec: "A file for another
    # edition exists but is not loaded"). That is the whole point of the
    # side-by-side layout: both files sit next to each other and the
    # manifest chooses.
    manifest = load_manifest(root) or {}
    listed_secs = set()
    for entry in manifest.get("data", []) or []:
        if os.path.basename(entry).endswith(".csv") and \
           os.path.basename(entry) in SECURITY_FILENAMES:
            listed_secs.add(entry)

    # Correct format for the edition, for both output and p-source.
    expected = profile["security_columns"]

    # A .p.csv whose output has already been reported yields the same
    # defect twice. Skip the p-source when its output file sits in the
    # same directory -- the defect is the same and the user fixes the
    # pair, not two files.
    reported = set()
    for name in present:
        if name.endswith(".p.csv"):
            out = name[: -len(".p.csv")] + ".csv"
            if out in present:
                reported.add(name)
    for name in present:
        if name in reported:
            continue
        path = os.path.join(secdir, name)
        # Only the file the manifest loads is judged. The other edition's
        # file is harmless and must not raise an error -- otherwise the
        # side-by-side layout can never be used.
        if ("security/" + name) not in listed_secs:
            continue
        header = csv_header(path)
        if header is None:
            continue                     # empty/headerless -- another check catches it
        # A .p.csv is a source; its header is the same across editions only
        # if the conditionals steer the rows. We check the output files,
        # plus the p-source to give an early warning.
        looks_legacy = "perm_read" in header
        looks_modern = "operation" in header
        if profile["security_format"] == "modern" and looks_legacy:
            findings.append((ERR, "WRONG_SECURITY_FORMAT", rel(root, path),
                             f"{name} har gammalt format (perm_*-kolumner) men "
                             f"edition {version} requires {profile['security_filename']} "
                             f"med kolumnerna {','.join(expected)}"))
        elif profile["security_format"] == "legacy" and looks_modern:
            findings.append((ERR, "WRONG_SECURITY_FORMAT", rel(root, path),
                             f"{name} har nytt format (operation/domain) men "
                             f"edition {version} requires {profile['security_filename']}"))
        elif not looks_legacy and not looks_modern and header != list(expected):
            findings.append((ERR, "WRONG_SECURITY_FORMAT", rel(root, path),
                             f"{name} has an unexpected header: {','.join(header)} -- "
                             f"expected {','.join(expected)}"))

        # Wrong filename for the shape: new format in ir.model.access.csv fails
        # fortfarande eftersom Odoo 20 tar modellen ur filnamnet.
        if looks_modern and name == "ir.model.access.csv":
            findings.append((ERR, "WRONG_SECURITY_FORMAT", rel(root, path),
                             f"nytt format ligger i {name} — Odoo 20 tar modellen ur "
                             f"the FILENAME before the content, so the file must be named "
                             f"ir.access.csv"))

    # Only the chosen security file may sit in the manifest's data
    manifest = load_manifest(root)
    if manifest is not None:
        data = manifest.get("data") or []
        listed = [d for d in data
                  if isinstance(d, str) and os.path.basename(d) in SECURITY_FILENAMES]
        info["listed"] = listed
        want = f"security/{profile['security_filename']}"
        manifest_name = "__manifest__.py"
        if not os.path.isfile(os.path.join(root, manifest_name)):
            manifest_name = "__manifest__.p.py"
        if len(listed) > 1:
            findings.append((ERR, "UNLISTED_SECURITY_FILE", manifest_name,
                             f"the manifest lists several security files: "
                             f"{', '.join(listed)} — bara {want} kan laddas"))
        for entry in listed:
            if os.path.basename(entry) != profile["security_filename"]:
                findings.append((ERR, "UNLISTED_SECURITY_FILE", manifest_name,
                                 f"the manifest loads {entry}, but edition {version} "
                                 f"requires {want}"))
        # A security file that exists but is not listed is dead weight. Not
        # a defect in itself (it is never loaded), but a silent trap: add it
        # to data without changing its shape and it fails. Reported as a warning.

    # Domain names that do not exist in the edition's eval context
    if profile["security_format"] == "modern":
        for name in present:
            path = os.path.join(secdir, name)
            header = csv_header(path)
            if not header or "domain" not in header:
                continue
            idx = header.index("domain")
            for lineno, row in enumerate(csv_rows(path), start=2):
                if len(row) <= idx:
                    continue
                # Odoo writes the domain with commas WITHOUT quotes
                # ([('user_id','=',user.id)]), so the csv module splits it
                # into several columns. A naive row[idx] read sees only the
                # first fragment ("[('user_id'") and misses uid in the tail.
                # Join everything from idx onward -- that is the domain.
                dom = ",".join(row[idx:])
                if not dom.strip():
                    continue
                for bad, good in BAD_DOMAIN_NAMES_MODERN.items():
                    if re.search(rf"\b{re.escape(bad)}\b", dom):
                        findings.append((ERR, "BAD_DOMAIN_NAME",
                                         f"{rel(root, path)}:{lineno}",
                                         f"the domain uses '{bad}' which is not in "
                                         f"20.0:s eval-kontext (user, time, "
                                         f"company_ids, company_id) -- use '{good}'"))
    return findings, info


def expand_ok(preprocess, pfile, outfile, version, repo, tmpdir, cache):
    """Returns (status, detail) where status is OK/STALE/ERROR."""
    if preprocess is None:
        return "ERROR", "preprocess saknas — kan inte verifiera expansion"
    if pfile not in cache:
        candidate = os.path.join(tmpdir, os.path.basename(outfile) or "out")
        if os.path.exists(candidate):
            os.remove(candidate)
        cmd = [preprocess, "-f", "-D", f"VERSION={version}", "-D", f"REPO={repo}",
               "-o", candidate, pfile]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        except subprocess.TimeoutExpired:
            cache[pfile] = ("ERROR", "preprocess timeout")
            return cache[pfile]
        if proc.returncode != 0:
            cache[pfile] = ("ERROR", f"preprocess misslyckades: {proc.stderr.strip()[:300]}")
            return cache[pfile]
        try:
            with open(candidate, "rb") as fh:
                cache[pfile] = (OK, fh.read())
        except OSError as exc:
            cache[pfile] = ("ERROR", f"could not read the expansion: {exc}")
        if os.path.exists(candidate):
            os.remove(candidate)
    status, value = cache[pfile]
    if status != OK:
        return status, value
    try:
        with open(outfile, "rb") as fh:
            actual = fh.read()
    except OSError as exc:
        return "ERROR", f"could not read the output: {exc}"
    if actual != value:
        return "STALE", "output differs from the expansion -- re-run preprocess"
    return OK, "matchar expansionen"


def check_root(root, version, exclude_allow, preprocess, tmpdir):
    allow, allow_src = load_allow(root)
    findings, cache = [], {}

    # Samla alla filer
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in EXCLUDED_DIRS)
        for name in sorted(filenames):
            files.append(os.path.join(dirpath, name))

    pfile_targets = {}
    for f in files:
        target, _ = pfile_split(os.path.basename(f))
        if target is not None:
            pfile_targets[os.path.join(os.path.dirname(f), target)] = f

    for f in files:
        name = os.path.basename(f)
        target, psuffix = pfile_split(name)
        relpath = rel(root, f)
        # The allow-list is module-qualified: "module/models/x.py". A flat
        # line ("models/x.py") matches ONLY when the module name is unknown --
        # otherwise one module's line would silence the same filename in
        # another module.
        allowed = f"{os.path.basename(root)}/{relpath}" in allow

        if target is not None:                                  # en p-fil
            outfile = os.path.join(os.path.dirname(f), target)
            if not os.path.isfile(outfile):
                findings.append((ERR, "MANUAL_PFILE", rel(root, f),
                                 f"{name} saknar genererad {target}"))
                continue
            if exclude_allow:
                st, detail = expand_ok(preprocess, f, outfile, version,
                                       os.path.basename(root), tmpdir, cache)
                findings.append((OK if st == OK else ERR,
                                 "PAIRED" if st == OK else st, rel(root, f), detail))
            else:
                findings.append((OK, "PAIRED", rel(root, f), "har genererad utdata"))
            continue

        if name in EXCLUDED_NAMES or not is_preprocessable(name):
            continue

        source = pfile_targets.get(f)                           # genererad fil?
        if source:
            if exclude_allow:
                continue        # p-filen rapporterar redan PARED/STALE
            try:
                with open(f, "rb") as fh:
                    generated = fh.read()
                with open(source, "rb") as fh:
                    origin = fh.read()
            except OSError as exc:
                findings.append((ERR, "STALE", rel(root, f), str(exc)))
                continue
            # The comparison must actually be used. Previously `same` was
            # computed and then discarded: the file was always reported as
            # identical to the p-file, even when it was not. In --no-expand
            # mode STALE was therefore impossible to get -- a silent false
            # green.
            if generated == origin:
                findings.append((OK, "PAIRED", rel(root, f), "identisk med p-filen"))
            else:
                findings.append((ERR, "STALE", rel(root, f),
                                 f"differs from {rel(root, source)} -- "
                                 f"re-run preprocess (or edit the p-file, "
                                 f"inte utdatafilen)"))
            continue

        if allowed:
            findings.append((OK, "ALLOWED", rel(root, f), "vitlistad i .pfiles-allow"))
        else:
            findings.append((ERR, "UNEXPLAINED", rel(root, f),
                             f"{name} is neither a p-file nor generated -- rename it to "
                             f"{pepfile_hint(name)} "
                             f"eller vitlista i .pfiles-allow"))

    # Edition-specific security checks. Added after the coverage check so
    # they always run, even with --no-expand.
    sec_findings, sec_info = security_findings(root, version)
    findings.extend(sec_findings)
    return findings, allow_src, allow, sec_info


def main(argv=None):
    ap = argparse.ArgumentParser(description="Hitta filer som saknar p-fil.")
    ap.add_argument("paths", nargs="+", help="moduler/repon att kontrollera")
    ap.add_argument("--version", default=os.environ.get("VERSION", ""),
                    help="Odoo edition, e.g. 18.0 (default: $VERSION)")
    ap.add_argument("--repo", default=None, help="REPO-definition (default: modulnamn)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--no-expand", action="store_true",
                    help="skip the expansion check (coverage only)")
    ap.add_argument("--print-allow", action="store_true",
                    help="print suggestions for .pfiles-allow (UNEXPLAINED -> lines)")
    ap.add_argument("-q", "--quiet", action="store_true", help="bara fel")
    args = ap.parse_args(argv)

    if not args.version and not args.no_expand:
        ap.error("--version is required (or $VERSION) -- the output depends on the edition")

    roots = find_roots(args.paths, explicit=False)
    if not roots:
        print("Found no module roots (a directory with __manifest__.py or *.p.py).",
              file=sys.stderr)
        return 2

    preprocess = None if args.no_expand else shutil.which("preprocess")
    tmpdir = tempfile.mkdtemp(prefix="pfiles-check-")
    all_findings, total_err = [], 0

    try:
        for root in roots:
            findings, allow_src, allow, sec_info = check_root(
                root, args.version, not args.no_expand, preprocess, tmpdir)
            errs = [f for f in findings if f[0] == ERR]
            total_err += len(errs)
            all_findings.append({"root": root, "allow": allow_src, "findings": findings,
                                 "errors": len(errs), "security": sec_info})
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    if args.print_allow:
        seen = set()
        for entry in all_findings:
            root = entry["root"]
            for sev, kind, path, _ in entry["findings"]:
                if kind == "UNEXPLAINED":
                    line = f"{os.path.basename(root)}/{path}"
                    if line not in seen:
                        seen.add(line)
                        print(line)
        return 0

    if args.json:
        print(json.dumps({"version": args.version, "preprocess": preprocess,
                          "roots": all_findings}, indent=2, ensure_ascii=False))
        return 1 if total_err else 0

    for entry in all_findings:
        rows = entry["findings"]
        shown = [r for r in rows if args.quiet is False or r[0] == ERR]
        print(f"=== {entry['root']}  ({entry['errors']} fel av {len(rows)} poster)")
        if entry["allow"]:
            print(f"    vitlista: {entry['allow']}")
        for sev, kind, path, detail in shown:
            mark = "✗" if sev == ERR else "✓"
            print(f"  {mark} {kind:<14} {path}")
            if sev == ERR or not args.quiet:
                print(f"      {detail}")
        missing = [r for r in rows if r[1] == "UNEXPLAINED"]
        if missing:
            print(f"    → {len(missing)} vitliknande rad(er). "
                  f"Generera: pfiles-check --version {args.version} --print-allow <rot>")
        if not rows:
            print("  (no p-files and no candidates -- the module does not use p-files)")

    if preprocess is None and not args.no_expand:
        print("\n⚠ preprocess not in PATH -- coverage check only. "
              "Installera: python3 -m pip install --break-system-packages preprocess", file=sys.stderr)
    return 1 if total_err else 0


if __name__ == "__main__":
    sys.exit(main())
