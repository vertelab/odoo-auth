#!/usr/bin/env bash
#
# pfiles-install.sh -- install an expanded module in the right Odoo edition.
#
# The install gate. Deliberately separates three outcomes, because they need
# different action:
#
#   OK        modulen installerades (rc=0)
#   MODULE    Odoo startade men modulen gick inte att ladda  -> trasig modul
#   ENV       Odoo could not start at all                    -> environment error
#
# The distinction is the spec's requirement "a missing test environment is
# told apart from a broken module". A broken module must point at the module;
# an environment error must point at the environment and not blame the code.
#
# Usage:
#   pfiles-install.sh <edition> <module-dir> [module-name]
#
# Environment:
#   PFILES_OCB_SRC   existing OCB repo (local runs). When absent, OCB is
#                    OCB shallow till PFILES_OCB_CACHE.
#   PFILES_OCB_CACHE katalog att klona till (default /tmp/pfiles-ocb)
#   PFILES_EXTRA_ADDONS  colon-separated list of extra addons directories
#                    (e.g. an odoo-base worktree holding dependencies that are
#                    not in OCB). Missing dependencies are an environment
#                    error, not a broken module.
#   PFILES_DB_NAME   database (default pfiles_ci_<edition>)
#   PFILES_DB_USER / PFILES_DB_PASSWORD  roll (default odoo / pfiles-scratch)
#
# Exitkoder:
#   0  OK
#   2  invalid usage
#   4  ENV  -- Odoo/OCB/database could not be started
#   6  MODULE — modulen laddades inte
#
set -euo pipefail

VERSION="${1:-}"
MODDIR="${2:-}"
MODNAME="${3:-}"
[ -n "$VERSION" ] && [ -n "$MODDIR" ] || {
  echo "pfiles-install: usage: pfiles-install.sh <edition> <module-dir> [module-name]" >&2
  exit 2
}
[[ "$VERSION" =~ ^[0-9]{2}\.0$ ]] || { echo "pfiles-install: the edition must look like 20.0" >&2; exit 2; }

MODDIR="$(cd "$MODDIR" && pwd)"
MODNAME="${MODNAME:-$(basename "$MODDIR")}"

log()  { echo "pfiles-install: $*" >&2; }

env_fail() { echo "pfiles-install: ENV: $*" >&2; exit 4; }
mod_fail() { echo "pfiles-install: MODULE: $*" >&2; exit 6; }

# --- Odoo source ----------------------------------------------------------

OCB_SRC="${PFILES_OCB_SRC:-}"
OCB_CACHE="${PFILES_OCB_CACHE:-/tmp/pfiles-ocb}"

fresh_clone=0
user_supplied=1
if [ -z "$OCB_SRC" ]; then
  user_supplied=0
  repo="$OCB_CACHE/OCB"
  if [ ! -d "$repo/.git" ]; then
    fresh_clone=1
    log "klonar OCB $VERSION shallow till $repo"
    rm -rf "$repo"
    mkdir -p "$OCB_CACHE"
    if ! timeout 900 git clone --quiet --depth 1 --branch "$VERSION" \
          https://github.com/OCA/OCB.git "$repo" 2>&1 | sed 's/^/pfiles-install: git: /' >&2; then
      env_fail "could not clone OCB $VERSION -- is the network/branch reachable?"
    fi
  else
    log "reusing OCB clone $repo"
  fi
  OCB_SRC="$repo"
fi

[ -x "$OCB_SRC/odoo-bin" ] || env_fail "odoo-bin saknas i $OCB_SRC"

# Keep an inherited PYTHONPATH. Setting PYTHONPATH="$OCB_SRC" alone REPLACES
# it, and Odoo then loses the packages in site-packages (babel, jinja2). The
# failure reads as "wrong edition would run" because --version crashes.
ODOO_PYPATH="$OCB_SRC${PYTHONPATH:+:$PYTHONPATH}"

# PEP420: OCB 19/20 skeppar odoo/init.py men ingen odoo/__init__.py. Utan
# the symlink the system-installed Odoo is imported instead -- silently, and
# the errors you see point at the wrong thing.
#
# The link is placed ONLY in a tree we fetched ourselves in this run. An
# existing tree (local development, reused cache) is left untouched: if
# someone removed the link there the assertion below must FAIL, not repair
# silently.
# Samma princip som --fix i scripts/pfiles-ocb.sh.
# The link is placed when the tree is OURS (cloned or cached by this script).
# A tree the user pointed at with PFILES_OCB_SRC is left untouched: there a
# removed link must fail the assertion below, not be repaired silently --
# otherwise the developer can never discover that their own environment runs
# the wrong edition.
if [ "$user_supplied" -eq 0 ] && [ -f "$OCB_SRC/odoo/init.py" ] && [ ! -e "$OCB_SRC/odoo/__init__.py" ]; then
  log "adding symlink odoo/__init__.py -> init.py (PEP420 fix)"
  ln -sfn init.py "$OCB_SRC/odoo/__init__.py" || env_fail "could not create the PEP420 symlink"
fi

# --- hard version assertion ----------------------------------------------
# Without it the whole step can run 18.0 and report 20.0 errors that never existed.
actual="$(PYTHONPATH="$ODOO_PYPATH" python3 "$OCB_SRC/odoo-bin" --version 2>&1 | tail -1 || true)"
series="$(printf '%s' "$actual" | grep -oE '[0-9]{2}\.0' | head -1 || true)"
if [ "$series" != "$VERSION" ]; then
  env_fail "wrong edition would run: asked for $VERSION, got '${series:-unknown}' ($actual)"
fi
log "Odoo $series i $OCB_SRC"

# --- databas --------------------------------------------------------------
# Peer auth does not work for the shell user; we always use TCP with an
# explicit role. If the database is already created by the workflow it is
# reused.
DB="${PFILES_DB_NAME:-pfiles_ci_${VERSION//./_}}"

DB_USER="${PFILES_DB_USER:-odoo}"
DB_PASS="${PFILES_DB_PASSWORD:-pfiles-scratch}"

# A module must be tested in a CLEAN database. Otherwise it inherits the
# neighbours' half-finished installations and fails for defects that are not
# its own -- a module failure that is really a test-method failure. The
# workflow sets PFILES_DB_FRESH=1 and gets a fresh database per module.
if [ "${PFILES_DB_FRESH:-0}" = "1" ]; then
  # Without a psql client we cannot guarantee a clean database. Carrying on
  # against a database that already has the neighbours installed gives a
  # false green: a broken module is "installed" without anything loading,
  # because Odoo skips a module already marked installed. That happened on a
  # psql — linkedin_contacts med en trasig xpath rapporterades som OK.
  command -v psql >/dev/null \
    || env_fail "PFILES_DB_FRESH=1 but psql is missing -- cannot create a clean database (environment error)"
  # Connect as superuser over TCP. In CI postgres is a service container where
  # the POSTGRES_USER role is already superuser; locally sudo -u postgres is
  # needed because the shell user has no role. We try sudo first and fall
  # back to TCP, so the same script works in both places.
  psql_admin() {
    if sudo -n -u postgres psql -v ON_ERROR_STOP=1 -tAc "SELECT 1" >/dev/null 2>&1; then
      sudo -n -u postgres psql -v ON_ERROR_STOP=1 -tAc "$1"
    else
      # I CI ar POSTGRES_USER redan superuser men har ett annat losenord an
      # DB_PASS. Vi provar DB_PASS forst och faller tillbaka pa losenordet
      # postgres-tjansten satt, annars misslyckas CREATE DATABASE tyst och
      # varje modul blir ENV av fel anledning.
      if PGPASSWORD="$DB_PASS" psql -h 127.0.0.1 -U "$DB_USER" -d postgres \
           -v ON_ERROR_STOP=1 -tAc "SELECT 1" >/dev/null 2>&1; then
        PGPASSWORD="$DB_PASS" psql -h 127.0.0.1 -U "$DB_USER" -d postgres \
          -v ON_ERROR_STOP=1 -tAc "$1"
      else
        PGPASSWORD="${POSTGRES_PASSWORD:-postgres}" psql -h 127.0.0.1 -U "$DB_USER" -d postgres \
          -v ON_ERROR_STOP=1 -tAc "$1"
      fi
    fi
  }
  # DROP kan misslyckas tyst om en anslutning ligger kvar. Da finns databasen
  # kvar med grannmodulerna installerade och nasta modul "installeras" utan
  # att nagot laddas. Vi kollar efterat att databasen verkligen ar borta och
  # skapar den sedan — ordningen maste vara DROP -> verifiera -> CREATE.
  psql_admin "DROP DATABASE IF EXISTS \"$DB\" WITH (FORCE)" >/dev/null 2>&1 || true
  still_there="$(psql_admin "SELECT 1 FROM pg_database WHERE datname='$DB'" 2>/dev/null | tr -d ' ' || true)"
  if [ -n "$still_there" ]; then
    psql_admin "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='$DB'" >/dev/null 2>&1 || true
    psql_admin "DROP DATABASE IF EXISTS \"$DB\" WITH (FORCE)" >/dev/null 2>&1 || true
    still_there="$(psql_admin "SELECT 1 FROM pg_database WHERE datname='$DB'" 2>/dev/null | tr -d ' ' || true)"
    [ -z "$still_there" ] || env_fail "could not drop database $DB (environment error)"
  fi
  if ! psql_admin "CREATE DATABASE \"$DB\" OWNER \"$DB_USER\"" >/dev/null 2>&1; then
    # Visa VARFOR det gick fel, inte bara att det gick fel. Utan orsaken gar
    # det inte att skilja en trasig miljo fran en trasig grind.
    why="$(psql_admin "CREATE DATABASE \"$DB\" OWNER \"$DB_USER\"" 2>&1 | head -2 | tr '\n' ' ')"
    env_fail "could not create a clean database $DB (environment error): $why"
  fi
  psql_admin "ALTER ROLE \"$DB_USER\" WITH PASSWORD '$DB_PASS'" >/dev/null 2>&1 || true

  # Verifiera att databasen verkligen ar NY. Om DROP/CREATE tyst misslyckades
  # (fel roll, ingen rattighet) skulle modulen koras mot en databas dar
  # grannarna redan ar installerade — och da ar "installerad" ett falskt
  # gront, eftersom Odoo hoppar over en modul som redan star som installerad.
  # Rak TCP-anslutning som primar vag. psql_admin valjer sudo forst, och i
  # en runner dar sudo finns men postgres-rollen inte gor det kan det ge tom
  # utdata — vilket gjorde att ALLA moduler rapporterades som "inte ren
  # databas". Samma anslutningssatt som workflowens miljosteg anvander.
  n_tables="$(PGPASSWORD="$DB_PASS" psql -h 127.0.0.1 -U "$DB_USER" -d "$DB" \
      -tAc "SELECT count(*) FROM information_schema.tables WHERE table_schema='public'" \
      2>/dev/null | tr -d ' \n' || true)"
  if [ -z "$n_tables" ]; then
    n_tables="$(psql_admin "SELECT count(*) FROM information_schema.tables WHERE table_schema='public'" 2>/dev/null | tr -d ' \n' || true)"
  fi
  if [ "${n_tables:-x}" != "0" ]; then
    env_fail "databasen $DB ar inte ren (${n_tables:-okant} tabeller) — kan inte bevisa nagot om modulen (miljofel)"
  fi
fi

if command -v pg_isready >/dev/null; then
  pg_isready -q -h 127.0.0.1 || env_fail "PostgreSQL is not responding on 127.0.0.1 (environment error)"
fi

# --- run ------------------------------------------------------------------
# We run against a copy of the module directory: Odoo writes __pycache__ and
# can in the worst case create files next to the module, and the CI tree must
# stay untouched so the next edition's comparison is not affected.
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
addons="$work/addons"
mkdir -p "$addons"
cp -a "$MODDIR" "$addons/$MODNAME"

# Extra addons directories (dependencies living outside OCB). They are placed
# after the module's own directory but before OCB's, so a local copy wins over a
# eventuell OCB-version med samma namn.
addons_path="$addons"
if [ -n "${PFILES_EXTRA_ADDONS:-}" ]; then
  IFS=':' read -r -a extra <<< "$PFILES_EXTRA_ADDONS"
  for d in "${extra[@]}"; do
    # Hoppa over kataloger som inte finns i stallet for att falla. Listan
    # kommer fran en sokning i .deps och kan innehalla t.ex. docs/ som inte
    # ar en addons-katalog; att falla pa en sadan gor att HELA sokvagen
    # forkastas och modulen rapporteras sakna ett beroende den hade.
    [ -d "$d" ] || continue
    addons_path="$addons_path,$d"
  done
fi
addons_path="$addons_path,$OCB_SRC/addons,$OCB_SRC/odoo/addons"

logfile="$work/odoo.log"
set +e
PYTHONPATH="$ODOO_PYPATH" python3 "$OCB_SRC/odoo-bin" \
  --addons-path="$addons_path" \
  --db_host=127.0.0.1 --db_port=5432 \
  --db_user="$DB_USER" --db_password="$DB_PASS" \
  -d "$DB" -i "$MODNAME" --stop-after-init --without-demo=all \
  --log-level=info >"$logfile" 2>&1
rc=$?
set -e

if [ "$rc" -eq 0 ]; then
  # rc=0 is not enough: Odoo can log the error and still exit zero. Check
  # that the module really is installed, otherwise we silently approve a
  # modul som inte laddades.
  # Las modulens state ur databasen. Vi fragar efter en MARKOR i utdata i
  # stallet for att lita pa sista raden: odoo-bin shell skriver en banner och
  # kan skriva varningar efter svaret, sa `tail -1` kan ge en varning som
  # state. Det gjorde att ett falskt gront slank igenom pa en runner.
  state="$(PYTHONPATH="$ODOO_PYPATH" python3 "$OCB_SRC/odoo-bin" shell \
      --db_host=127.0.0.1 --db_port=5432 --db_user="$DB_USER" --db_password="$DB_PASS" \
      -d "$DB" --no-http 2>/dev/null <<PYSTATE || true
print("PFILES_STATE=" + (env['ir.module.module'].search([('name','=','$MODNAME')]).state or 'missing'))
PYSTATE
)"
  state="$(printf '%s\n' "$state" | grep -o 'PFILES_STATE=.*' | head -1 | cut -d= -f2)"

  # Tom state betyder att fragan aldrig nadde databasen — det ar ett miljofel,
  # inte ett godkannande. Utan den kontrollen blir ett trasigt svar "OK".
  if [ -z "$state" ]; then
    tail -20 "$logfile" >&2
    env_fail "kunde inte lasa modulstatus for $MODNAME i $DB (miljofel)"
  fi
  if [ "$state" != "installed" ]; then
    log "modulen ar inte installerad (state='$state'), rc=$rc"
    # 'uninstallable' betyder att Odoo sjalv fann modulen oinstallerbar —
    # nastan alltid ett beroende som inte finns. Det ar ett miljofel, inte
    # en trasig modul, och ska inte skicka utvecklaren att leta i sin kod.
    # Vilka beroenden som saknas star i loggen (Module <x> not found).
    # Fraga databasen vilka beroenden modulen har och om de finns. Forst om
    # ett beroende SAKNAS ar det ett miljofel. 'uninstallable' med alla
    # beroenden pa plats betyder att modulen sjalv ar trasig (t.ex. en vy som
    # inte kan laddas) och da ar MODULE ratt svar.
    if [ "$state" = "uninstallable" ]; then
      deps_ok="$(PYTHONPATH="$ODOO_PYPATH" python3 "$OCB_SRC/odoo-bin" shell \
          --db_host=127.0.0.1 --db_port=5432 --db_user="$DB_USER" --db_password="$DB_PASS" \
          -d "$DB" --no-http 2>/dev/null <<PYDEPS || true
m = env['ir.module.module'].search([('name','=','$MODNAME')])
deps = m.dependencies_id.mapped('name')
have = set(env['ir.module.module'].search([('name','in',deps)]).mapped('name'))
missing = sorted(set(deps) - have)
print("PFILES_MISSING=" + (",".join(missing) if missing else "NONE"))
PYDEPS
)"
      deps_ok="$(printf '%s\n' "$deps_ok" | grep -o 'PFILES_MISSING=.*' | head -1 | cut -d= -f2)"
      if [ -n "$deps_ok" ] && [ "$deps_ok" != "NONE" ]; then
        tail -20 "$logfile" >&2
        env_fail "$MODNAME ar oinstallerbar i $VERSION — saknade beroenden: $deps_ok (miljofel)"
      fi
      # Alla beroenden finns: modulen ar trasig, inte miljon.
      tail -40 "$logfile" >&2
      mod_fail "$MODNAME ar oinstallerbar i $VERSION trots att beroendena finns — modulen kan inte laddas"
    fi
    tail -40 "$logfile" >&2
    mod_fail "$MODNAME installerades inte i $VERSION (state='$state')"
  fi
  log "OK: $MODNAME installerades i $VERSION"
  grep -E "ERROR|CRITICAL|Traceback" "$logfile" >&2 || true
  exit 0
fi

# A missing DEPENDENCY is an environment error: the module is not broken, it is
# testsviten som inte fick med sig beroendet. Att klassa det som MODULE
# skickar utvecklaren att leta fel i sin egen kod.
# Odoo splits the message across TWO lines:
#   You try to install module "x" that depends on module "y".
#   But the latter module is not available in your system.
# A grep for the whole phrase on one line therefore never matches -- that was
# the defect that first classified missing dependencies as broken modules.
if grep -qF 'But the latter module is not available' "$logfile"; then
  missing="$(grep -oE 'depends on module "[^"]+"' "$logfile" | head -1 | sed 's/.*"\(.*\)"/\1/')"
  tail -20 "$logfile" >&2
  env_fail "dependency '${missing:-unknown}' is not on the addons path -- add it with PFILES_EXTRA_ADDONS (environment error, not a module error)"
fi

# Tell environment errors from module errors. A module that cannot load
# typically gives KeyError/ParseError/ValueError with the module name in the
# trace, and Odoo gets as far as starting the registry. An environment error
# (DB refuses, port closed, wrong password) shows up
# som anslutningsfel INNAN registret laddas.
if grep -qE "could not connect|Connection refused|password authentication failed|FATAL:|database .* does not exist|psycopg2.OperationalError" "$logfile"; then
  tail -30 "$logfile" >&2
  env_fail "could not connect to database $DB (environment error, not a module error)"
fi

if grep -qE "CRITICAL.*Failed to (load|initialize) (registry|database)|Failed to initialize database" "$logfile"; then
  tail -40 "$logfile" >&2
  mod_fail "$MODNAME could not be loaded in $VERSION (rc=$rc) -- see the trace above"
fi

tail -40 "$logfile" >&2
mod_fail "$MODNAME returned rc=$rc in $VERSION and could not be classified as an environment error"
