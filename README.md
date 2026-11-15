# odoo-auth — gren 19.0

> **Denna gren är avsiktligt tom.** Modulerna är INTE portade till Odoo 19.
> Grenen finns så att dev-miljöer (`hansolo19`) kan klona den utan att falla,
> men den påstår ingenting om att koden är portad.

## Baseline

| | |
|---|---|
| Källa | `20.0` |
| Moduler | **3** |
| Grenar i repot | `10.0`, `12.0`, `12.0-af`, `12.0-test`, `13.0`, `14.0`, `17.0`, `18.0`, `20.0`, `Dev-12.0`, `Dev-12.0-Fenix-Sprint-02`, `master` |

## Moduler

- `apps_access_right`
- `auth_from_basic_http`
- `auth_provisioning`

## Blockerare

✅ Inga externa beroenden saknas i Odoo 19-kärnan eller OCA 19.0.

Modulerna kan troligen portas utan att vänta på externa bidrag.

## Nästa steg

Portering sker på `*-pfile`-maskin med versionsagnostisk kod
(`.p.py` / `.p.xml`). Se `/skill:odoo-pfiles`.
