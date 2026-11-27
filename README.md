# odoo-auth

Autentiseringstillägg för Odoo: applikationsrättigheter, HTTP Basic Auth och
användarprovisionering.

## Moduler

| Modul | Vad den gör |
|---|---|
| `apps_access_right` | Skiljer rätten att **installera appar** från rätten att **administrera inställningar**. En Settings-administratör utan Apps-gruppen nekas install/upgrade/uninstall. |
| `auth_from_basic_http` | Autentiserar via `Authorization: Basic`-headern för konfigurerade domäner (`basic_auth_domains`). |
| `auth_provisioning` | Beräknar inbjudnings-/återställningslänken (`signup_url`) och en QR-kod för mobila enheter. |

## Portstatus

Samma kod på alla tre utgåvor, via p-filer. Status avser **den här grenen** (`20.0`).

| Modul | Utgåva | Installerad | Test | Blockerare |
|---|---|---|---|---|
| `apps_access_right` | 20.0 | ✅ `installed` | ✅ grön | — |
| `auth_from_basic_http` | 20.0 | ✅ `installed` | ✅ grön | — |
| `auth_provisioning` | 20.0 | ✅ `installed` | ✅ grön | — |

Verifierat i `tst_auth_20` med `ir_module_module.state = 'installed'` — inte
med en exitkod — och 17 tester körda med `--test-tags` mot alla tre moduler.

## Så skrivs koden

En källfil per logisk fil, `*.p.py` / `*.p.xml` / `*.p.csv`. Expansionen för
grenens utgåva committas. Redigera **p-filen**, aldrig utdatan.

```bash
# expandera för grenens utgåva
preprocess -f -D VERSION=20.0 -o <utdata> <p-fil>

# grinden (körs även av .githooks/pre-commit och av CI)
python3 .github/pfiles-check.py --version 20.0 .
```

Två saker som skiljer sig mellan utgåvorna och som därför står i p-filerna:

| Ändring | 18.0 / 19.0 | 20.0 |
|---|---|---|
| Säkerhetsfil | `security/ir.model.access.csv` (`perm_*`) | `security/ir.access.csv` (`operation`, `domain`) |
| `res.groups`-medlemmar | `users` | `user_ids` |
| `ir.ui.menu`-grupper | `groups_id` | `group_ids` |
| `ir.config_parameter` | `get_param` / `set_param` | `get_int` / `get_str` / `set_str` |
| `Binary`-fält | base64-text | `BinaryValue` |
| Session-patch | `Request._get_session_and_dbname` | `router._set_session_and_dbname` |

**XML-direktiv skrivs `<!-- #if -->`**, inte `# #if` — `preprocess` väljer
kommentarsyntax efter filtyp, och `# #if` i en `.xml` lämnas orörd.

## Tester

```bash
odoo-bin -c /etc/odoo/pfile/20.0/odoo.conf -d tst_auth_20 \
  -u apps_access_right,auth_from_basic_http,auth_provisioning \
  --test-tags=/apps_access_right,/auth_from_basic_http,/auth_provisioning \
  --workers 0 --stop-after-init
```

`--workers 0` krävs: i worker-läge startar inga tester.

Räkna `FAIL:` och `ERROR: Test` i loggen — inte `ERROR:` och inte exitkoden.
En mall som inte renderar skriver `ERROR:` utan att vara ett testfel.

## Källor

- `docs/pfiles-ci.md` — grinden, de fem filerna, utgåvematrisen
- `docs/pfiles-security-csv.md` — säkerhetsfilen 18/19 vs 20
- `/skill:odoo-pfiles` — p-filer och de elva fällorna
