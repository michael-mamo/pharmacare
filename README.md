# PharmaCare Management System

A modular, role-based, bilingual (English/Amharic) Pharmacy Management System
built with Django 6, Bootstrap 5, Chart.js, and DataTables. SQLite for local
development, PostgreSQL-ready for production via environment variables.

This repository is delivered in phases (see roadmap below). **Phase 1 is
complete and fully tested**: project setup, authentication, role-based access
control, the live KPI dashboard, full Amharic/English localization, a
professional design system, and a hardened security baseline. Every later
phase builds on this same foundation — i18n-wrapped strings, the design
tokens in `pharmacare.css`, and the security controls below all carry
forward automatically.

---

## Phase 1 — What's included

**Authentication & access control**
- Custom `User` model with four roles: **Administrator, Pharmacist, Cashier,
  Store Manager**
- Login, logout, and full password-reset flow (email-based, console backend
  in dev)
- Role-based access control via a reusable mixin (`RoleRequiredMixin`) and
  decorator (`role_required`) — enforced and tested (non-admins get a real
  HTTP 403 on admin-only pages, not just a hidden menu item)
- Staff management CRUD (Administrator-only): list/search/filter, create,
  edit, view, delete
- Self-service profile page for any logged-in user, including a language
  preference

**Security (banking-grade baseline)**
- **Account lockout** (`django-axes`): 5 failed sign-ins lock the
  account *and* the source IP for 30 minutes, with a dedicated lockout page
  — tested and confirmed to return HTTP 429
- **Forced password change**: every new or admin-reset account must set its
  own password before reaching anything else in the system, enforced by
  middleware server-side (not just a UI redirect)
- **Strong password policy**: 10+ characters, plus required uppercase,
  lowercase, digit, and special character (custom validator)
- **Hardened cookies** in every environment: `HttpOnly`, `SameSite=Lax` on
  session and CSRF cookies
- **TLS-only hardening auto-enables in production**: HSTS, secure cookies,
  SSL redirect all switch on automatically when `DEBUG=False`
- Login IP tracking, feeding the Phase 6 Audit Log
- CSRF protection on every form; passwords hashed with Django's PBKDF2

**Bilingual interface (English + Amharic / አማርኛ)**
- Full `django.utils.translation` i18n: every user-facing string is wrapped
  in `{% trans %}` / `{% blocktranslate %}`
- Language switcher in the top bar (and on the login page) — persists via
  session/cookie, no page-specific setup needed
- Amharic renders natively via Noto Sans Ethiopic layered into the font
  stack; no separate RTL handling needed (Ge'ez script is left-to-right)
- Translation source lives in `locale/am/LC_MESSAGES/django.po` — extend it
  with `python manage.py makemessages -l am`, then
  `python manage.py compilemessages`

**Design system**
- A real token system (see `static/css/pharmacare.css`): Manrope/Inter type
  pairing, restrained use of the brand yellow (left-border accents, primary
  actions, key figures — not smeared across every surface), refined shadows
  and spacing, dark mode
- **True mobile-first responsiveness**: off-canvas sidebar with a backdrop
  overlay (not just a collapse), auto-closing nav on link tap, comfortable
  44px+ tap targets on touch devices, and a KPI grid that reflows cleanly
  down to small phones
- Dashboard with KPI cards and four Chart.js charts (Monthly Sales, Sales
  Trend, Top Selling Medicines, Stock by Category) — render correctly at
  zero now and populate automatically once Phase 2-4 apps are installed
- Bootstrap 5, Font Awesome, SweetAlert2 (toast notifications), DataTables,
  fully responsive layout
- Brand palette applied throughout: `#F1AB15` (yellow), black, white

## Project structure

```
pharmacare/
├── apps/
│   ├── organizations/   # Tenancy: Organization + scoped managers
│   ├── core/            # Ethiopian calendar + fiscal year
│   ├── catalogue/        # Standard product catalogue + CSV import
│   ├── branches/        # Branch + BranchStock, branch context middleware
│   ├── accounts/        # Custom User, RBAC, auth views, staff CRUD, lockout, forced password change
│   ├── dashboard/       # KPI dashboard + chart data aggregation (live queries)
│   ├── medicine/        # Category + Medicine catalog, barcode/QR shelf labels
│   ├── suppliers/       # Supplier records
│   ├── customers/       # Customer records + loyalty points
│   ├── purchases/       # Purchase invoices (auto stock increase, immutable ledger)
│   ├── inventory/       # Stock movements (in/out/adjustment/transfer) + stock reports
│   ├── sales/           # POS terminal, sales, invoices, void-with-stock-return
│   ├── reports/         # 9 declarative reports + PDF/Excel/CSV exporters
│   ├── notifications/   # 5 alert types, self-resolving, role-targeted
│   ├── audit/           # Append-only audit trail (user/action/date/IP)
│   └── settings_app/    # Pharmacy settings singleton + DB backup
├── docs/
│   ├── guides/          # One illustrated PDF+HTML guide per role
│   ├── build_guides.py  # Regenerates the role guides
│   ├── guide_assets.py  # Shared styling + SVG diagrams
│   ├── USER_GUIDE.md    # Single-file written reference
│   ├── VISUAL_GUIDE.html
│   └── PharmaCare-Visual-Guide.pdf
├── pharmacare/          # Project settings, root urls.py, wsgi/asgi
├── locale/
│   └── am/LC_MESSAGES/  # Amharic translations (django.po / django.mo)
├── templates/
│   ├── base.html
│   ├── layout_app.html  # App shell: sidebar + topbar (topbar lives here, not in an include — see note below)
│   ├── partials/        # sidebar.html, navbar_actions.html
│   ├── organizations/   # Tenancy: Organization + scoped managers
│   ├── core/            # Ethiopian calendar + fiscal year
│   ├── catalogue/        # Standard product catalogue + CSV import
│   ├── branches/        # Branch + BranchStock, branch context middleware
│   ├── accounts/  medicine/  suppliers/  customers/
│   └── purchases/ inventory/ sales/      dashboard/
├── static/
│   ├── css/pharmacare.css
│   ├── js/pharmacare.js
│   └── fonts/           # Noto Sans Ethiopic (OFL) — required for Amharic PDFs
├── manage.py
├── requirements.txt
└── .env.example
```

> **Design note for future phases:** the per-page title in the top bar is a
> Django template `{% block %}` defined directly in `layout_app.html` (which
> every page `{% extends %}`), not inside an `{% include %}`. Django's block
> inheritance only resolves through the `{% extends %}` chain — a block
> declared inside an included partial can never be overridden by a child
> template. Keep any future per-page block the same way: on the file that's
> actually extended.

Remaining phases will add `apps/notifications`, `apps/audit`, and
`apps/settings_app` (Phase 6) — following
the exact same pattern already established (namespaced URLs,
RoleRequiredMixin, crispy forms, `{% trans %}`-wrapped strings, this design
system).

> **Design note — submit buttons live in templates, not form layouts.**
> `{{ form|crispy }}` is a *filter*: it renders fields only and silently
> ignores `FormHelper.layout`, so a `Submit()` added to a layout never
> appears on the page (this shipped as a real bug mid-project — six forms
> were unsaveable). The `{% crispy form %}` *tag* does honour the layout,
> but emits its own `<form>` element, which would nest inside the `<form>`
> our templates already provide. Keep buttons as explicit
> `<button type="submit">` in the template, wrapped in `{% trans %}`.

## Phase 2 — Medicine, Category, Supplier, Customer management

Three new apps: `apps/medicine` (Category + Medicine), `apps/suppliers`,
`apps/customers`. Same standard as Phase 1: real models, migrations, i18n,
this design system, and role-based access control — enforced per action,
not just per page, and verified with live HTTP tests (not just written).

**Features:** auto-generated medicine codes (`MED-000001`), barcode field,
printable shelf labels with a real generated Code128 barcode and QR code,
search/filter/pagination on every list, low-stock and expiry indicators
that feed directly into the Phase 1 dashboard (it "lit up" automatically
with zero code changes once these apps were installed).

### Access matrix

Access differs by role **and by action** — not just which pages a role can
open, but which fields it can see and which buttons actually work:

| Module | Administrator | Store Manager | Pharmacist | Cashier |
|---|---|---|---|---|
| Medicines — View | ✅ | ✅ | ✅ (no cost price) | ✅ (no cost price) |
| Medicines — Add / Edit / Delete | ✅ | ✅ | ❌ 403 | ❌ 403 |
| Categories — View | ✅ | ✅ | ✅ | ✅ |
| Categories — Add / Edit / Delete | ✅ | ✅ | ❌ 403 | ❌ 403 |
| Suppliers — View | ✅ | ✅ | ✅ | ❌ 403 (no need to see business/vendor data) |
| Suppliers — Add / Edit / Delete | ✅ | ✅ | ❌ 403 | — |
| Customers — View / Add / Edit | ✅ | ✅ | ✅ | ✅ |
| Customers — Loyalty points field | ✅ visible | ✅ visible | hidden from form | hidden from form |
| Customers — Delete | ✅ | ✅ | ❌ 403 | ❌ 403 |

This is implemented in two layers:
1. **View-level** (`apps/accounts/permissions.py::RoleRequiredMixin`) —
   each Create/Update/Delete view declares `allowed_roles`; Administrators
   always pass. A role outside the list gets a real HTTP 403, not a hidden
   button.
2. **Field-level** — `User.can_view_cost_price()` hides the purchase/cost
   price column and form field from Pharmacist/Cashier everywhere a price
   appears; `CustomerForm` drops the `loyalty_points` field entirely for
   any role that isn't Administrator/Store Manager, rather than just
   disabling it client-side.

The full set of role-capability checks lives on the `User` model itself
(`apps/accounts/models.py`) — `can_manage_catalog()`, `can_view_suppliers()`,
`can_manage_suppliers()`, `can_view_cost_price()`, `can_edit_customers()`,
`can_delete_customers()` — so Phase 3+ views can reuse the same predicates
instead of re-deriving role logic per app.

To seed a realistic catalog for exploring these differences:

```bash
python manage.py seed_catalog
# Adds 5 categories, 3 suppliers, 3 customers, 5 medicines
# (one is pre-expired, to exercise the dashboard's expiry alerts)
```

## Phase 3 — Purchases & Inventory

Two new apps: `apps/purchases` (PurchaseInvoice + PurchaseItem line items)
and `apps/inventory` (StockMovement covering Stock In/Out/Adjustment/
Transfer). Same standard as every prior phase — real models, migrations,
i18n, this design system, and role-based access control verified with live
tests, not just written.

**How stock moves through the system:**
- **Purchases** increase stock automatically — each `PurchaseItem` adds its
  quantity to the medicine on save, inside the same transaction as the
  invoice. Purchases are treated as an **immutable financial ledger**:
  once recorded there is no edit, only delete (Administrator only), and
  deleting reverses the stock it added rather than leaving phantom units
  behind. Verified: creating a purchase for 100 units took a medicine from
  500 → 600 in stock; deleting that same purchase brought it back to 500.
- **Stock Movements** cover everything that isn't a purchase or a sale:
  Stock In (found/received stock), Stock Out (breakage, write-off), Stock
  Adjustment (you enter the *new counted total*, not a delta — the system
  computes the difference), and Stock Transfer (leaving for another branch;
  see the note in `apps/inventory/models.py` about why this project doesn't
  yet model branches/locations, and how `destination` gives a clean upgrade
  path when it does). All four are validated server-side — e.g. Stock Out
  cannot remove more than is currently in stock — and run through row
  locking (`select_for_update`) so two staff adjusting the same medicine at
  once can't corrupt the count.
- **Low Stock** and **Out of Stock** reports are dedicated pages under
  Inventory, reusing the same `Medicine` queryset logic the Phase 1
  dashboard already relies on.

### Access matrix (extends the Phase 2 table)

| Module | Administrator | Store Manager | Pharmacist | Cashier |
|---|---|---|---|---|
| Purchases — View / Create | ✅ | ✅ | ❌ 403 (cost-sensitive) | ❌ 403 |
| Purchases — Delete | ✅ | ❌ 403 | ❌ | ❌ |
| Inventory reports (current/low/out-of-stock) | ✅ | ✅ | ✅ (needs it to dispense/reorder) | ❌ 403 |
| Stock Movements — Record | ✅ | ✅ | ❌ 403 | ❌ 403 |

The Purchases row is worth noting specifically: **creating** a purchase and
**deleting** one are governed by different rules for the same object —
Store Manager can record a purchase but gets a 403 trying to delete it,
because deletion reverses a financial stock effect and is tightened to
Administrator only. This was verified live: Store Manager → create
succeeds (302), Store Manager → delete same record (403), Administrator →
delete same record (200).

All new predicates live alongside the Phase 2 ones on the `User` model:
`can_view_purchases()`, `can_manage_purchases()`, `can_delete_purchases()`,
`can_view_inventory_reports()`, `can_manage_stock_movements()`.

## Phase 4 — Point of Sale & Sales

One new app, `apps/sales` (`Sale` + `SaleItem`), plus the POS terminal that
front-line staff actually work in all day.

**The POS terminal** (`/sales/pos/`) is a single screen: scan a barcode (an
exact match drops straight into the cart — hardware scanners send Enter
automatically, which the page treats as a scan), or type to search by name,
code, or generic name via a debounced AJAX lookup. The cart supports
per-line quantity and discount, shows live subtotal / discount / VAT /
grand total, takes Cash, Card, or Mobile Money, and calculates change due.
Completing a sale returns the invoice number and change in one dialog, with
a direct link to the printable receipt.

**Prices are snapshotted, not referenced.** Each `SaleItem` stores the
`unit_price`, `tax_percent`, `discount_percent`, and even `medicine_name`
as they were at the moment of sale. This is deliberate: when a medicine's
price changes next month — or the catalog entry is renamed — every
historical invoice must still show what the customer actually paid. Past
invoices are never recomputed from the current `Medicine` row.

**Sales are an immutable ledger, like purchases.** There is no edit. A
mistake is corrected by *voiding*, which returns every line's stock and
leaves the invoice on record marked as voided (with who voided it, when,
and why). Voiding is Administrator-only and cannot be applied twice.

**Concurrency is handled properly.** `complete_sale()` validates the entire
cart before writing anything, and locks every `Medicine` row it touches
with `select_for_update()`, ordered by primary key to avoid deadlocking
against another concurrent sale. Two cashiers ringing up the last packet at
the same moment cannot oversell it.

**Loyalty points** are awarded to named customers at a rate defined by
`LOYALTY_POINTS_PER_CURRENCY_UNIT` in `apps/sales/services.py` (default: 1
point per 100 currency units). Walk-in sales earn none. The rate lives in
one constant so the Phase 6 Settings module can lift it into the database
without touching sale logic.

**The dashboard now runs on real data.** All four Phase 1 charts populate
from live queries — 6-month revenue, 14-day sales trend, top-selling
medicines by units, and stock by category — plus real Sales Value and a
Profit Summary (revenue minus cost of goods sold).

### Access matrix (extends Phases 2–3)

| Module | Administrator | Store Manager | Pharmacist | Cashier |
|---|---|---|---|---|
| POS terminal (ring up a sale) | ✅ | ❌ 403 | ✅ | ✅ |
| POS medicine lookup API | ✅ | ❌ 403 | ✅ | ✅ |
| Sales history & invoices | ✅ | ✅ | ✅ | ✅ |
| Void a sale (returns stock) | ✅ | ❌ 403 | ❌ 403 | ❌ 403 |

Note the deliberate **inversion** versus Phase 3: the Store Manager is the
primary role for Purchases and Inventory but is blocked from the POS, while
the Cashier is blocked from Purchases/Inventory but is a primary role at the
till. Permissions follow the actual job, not a single seniority ladder.

Sales history is open to every role on purpose — a Cashier needs to reprint
a customer's receipt, and a Store Manager needs sales figures to plan
reordering. Note also that the POS lookup API returns `selling_price` but
never `purchase_price`, so cost data stays invisible to Cashiers and
Pharmacists even through the JSON endpoint (verified by test).

New predicates on the `User` model: `can_operate_pos()`, `can_view_sales()`,
`can_void_sales()`.

## Phase 5 — Reports & Export

One new app, `apps/reports`, providing **nine reports** with **PDF / Excel /
CSV** export and on-screen print.

Reports are **declarative**: each one is a small class in
`apps/reports/registry.py` stating who may open it, its columns, how to
build rows from filters, and its summary totals. Three generic views and
three generic exporters are driven from that declaration, so adding a
tenth report means writing one class — not four views and four templates.

| Report | Contents |
|---|---|
| Sales | Every completed sale in the period, with totals |
| Sales Summary | Revenue grouped **daily / weekly / monthly / yearly** (one `period` filter rather than four near-identical reports) |
| Purchase | Supplier purchases with invoice totals |
| Profit | Revenue vs cost of goods sold per medicine, with margin % |
| Inventory | Full stock position, optional stock value |
| Low Stock | At or below reorder level |
| Expired & Expiring | Expired plus 30/60-day horizons, with value at risk |
| Supplier | Medicines supplied and purchase totals per supplier |
| Customer | Purchase history and loyalty points |

### Access matrix

Access is **per report**, not per section — the index lists only what a role
may open, and the detail/export views re-check on direct URL access (a
guessed URL returns 403, not data).

| | Administrator | Store Manager | Pharmacist | Cashier |
|---|---|---|---|---|
| Sales, Sales Summary, Customer | ✅ | ✅ | ✅ | ✅ |
| Inventory, Low Stock, Expiry, Supplier | ✅ | ✅ | ✅ | ❌ 403 |
| **Purchase, Profit** (cost-sensitive) | ✅ | ✅ | ❌ 403 | ❌ 403 |
| **Export** (PDF/Excel/CSV) | ✅ | ✅ | ❌ 403 | ❌ 403 |

Reports visible per role: Administrator 9, Store Manager 9, Pharmacist 7,
Cashier 3. Cost columns (stock value, value at risk, supplier purchase
value) are additionally **masked** for roles that may open a report but
aren't cleared for cost data — a Pharmacist sees the Inventory report
without the "Total Stock Value" figure.

Exporting is held to a tighter standard than viewing, because an exported
file leaves the system entirely (email, USB, shared drive). Every export
carries a small footer noting it's AI-assisted output and should be
verified before external distribution.

### Export implementation notes

Three non-obvious problems came up here; all are fixed, and worth knowing
before touching this code:

1. **ReportLab has no Ethiopic glyphs, and fails silently.** Amharic PDFs
   rendered as `■■■■` boxes with no error at all — caught only by
   extracting text back out of a generated PDF. Fixed by bundling Noto
   Sans Ethiopic (`static/fonts/`, SIL Open Font License).
2. **…but Noto Sans Ethiopic has no Latin letters or digits** (533 glyphs,
   Ethiopic only), so simply switching the document font broke every
   English label and every number instead. ReportLab does no automatic font
   fallback, so `_rich()` in `exporters.py` splits each string into runs and
   tags only the Ethiopic ones with `<font name="NotoEthiopic">`, leaving
   Latin and numerals in Helvetica. Mixed Amharic/English/numeric strings
   now render correctly in one paragraph.
3. **Excel forbids `\ / * ? : [ ]` in sheet names** and caps them at 31
   characters. The "Sales Summary (Daily / Weekly / Monthly / Yearly)"
   title tripped this and returned a 500. `_safe_sheet_title()` sanitizes
   it; the untruncated title still appears inside the sheet.

Also: CSV is written with a UTF-8 BOM so Excel on Windows opens Amharic
correctly rather than as mojibake, and the Excel exporter writes numeric
columns as real numbers (not text) so totals and sorting work in the
spreadsheet — which is the main reason to offer xlsx alongside CSV.

## Phase 6 — Notifications, Audit Log & Settings

Three apps complete the system: `apps/notifications`, `apps/audit`,
`apps/settings_app`. Every previously-disabled sidebar link is now live.

### Notifications

Five alert types, matching the spec: **low stock, expired medicines, new
purchase, large sales, pending payments**.

Two design decisions worth knowing:

- **Alerts are role-targeted, not user-targeted.** A low-stock warning is
  relevant to whoever is on shift, not to one named person, so
  `target_roles` holds a role list rather than fanning out one row per user
  every time stock dips. Read state *is* per user
  (`NotificationRead`), because each person must dismiss independently.
- **Condition-based alerts resolve themselves.** Replenish a low-stock
  medicine and its warning disappears with a `resolved_at` timestamp —
  nobody has to tidy up stale alerts. A `dedupe_key` makes the generator
  idempotent, so re-running it never piles up duplicate rows. Event alerts
  (new purchase, large sale) are *not* auto-resolved, because the event
  genuinely happened.

Refresh happens on demand from the UI, or on a schedule:

```powershell
python manage.py refresh_notifications
```

Use Windows Task Scheduler to run that periodically if you want alerts
current even when nobody is logged in.

### Audit Log

Records **user, action, date, and IP address** — the four fields the spec
asks for — plus the record affected. Entries are written by signal handlers
using the thread-local user/IP captured by `CurrentUserMiddleware`, which
was deliberately wired in back in Phase 1 so this app wouldn't need to
thread `request` through every model method.

- **Append-only**: there is no edit or delete view, and the Django admin
  registration blocks add/change/delete too. An audit trail that can be
  altered from the UI provides little assurance in a regulated environment.
- **Administrator-only** to read (Store Manager, Pharmacist, Cashier all
  get 403).
- **Failed logins are logged**, which matters more than successful ones for
  spotting an attack — with the attempted username only. Verified by test
  that the submitted password never reaches the log.
- Audited models are an explicit **allow-list**. Logging `Session`,
  `AccessAttempt` and similar churn would bury the entries that matter, and
  audit noise is functionally the same as no audit.

### Settings

A database-backed singleton covering pharmacy information, logo, tax rate,
currency, invoice prefix and footer, licence/TIN numbers, plus the
large-sale alert threshold and loyalty-point rate.

This **closes the loop on a Phase 1 note**: branding was read from
environment variables with a comment saying it would move into the database
once this module existed. It now does — `PharmacySettings.load()` feeds the
context processor, with the env values as fallback so an existing
deployment keeps working before the first save. Verified live that changing
the name in Settings updates the sidebar, the login page, and printed
invoices. The `large_sale_threshold` and `loyalty_points_per_unit` fields
likewise replaced the module constants noted in Phase 4.

**Database backup** behaves differently per engine, deliberately:

- **SQLite (development)** — downloads the database file, which is a
  complete and directly restorable backup.
- **PostgreSQL (production)** — the button is *disabled on purpose*. A valid
  dump must be taken server-side with `pg_dump`; a download button that
  silently produced an incomplete backup would be worse than no button at
  all. The page shows the exact command to run instead.

### Access matrix

| | Administrator | Store Manager | Pharmacist | Cashier |
|---|---|---|---|---|
| Notifications | ✅ | ✅ | ✅ | ✅ (role-filtered) |
| Audit Log | ✅ | ❌ 403 | ❌ 403 | ❌ 403 |
| Settings | ✅ | ❌ 403 | ❌ 403 | ❌ 403 |
| Database backup | ✅ | ❌ 403 | ❌ 403 | ❌ 403 |

Notification *content* is filtered per role even though the page is open to
all: stock and expiry alerts target Administrator/Store Manager/Pharmacist,
while purchase, large-sale and pending-payment alerts target
Administrator/Store Manager only.

## Product types — beyond medicines

The catalogue is not medicine-only. `Medicine.product_type` covers
**Medicine, Cosmetic/Personal Care, Medical Supply** (bandages, gauze,
syringes), **Medical Device/Support** (knee braces, BP monitors),
**Supplement, Baby & Mother Care** and **Other**.

One catalogue rather than a parallel one, deliberately: a second product
model would split stock, sales, batches and reporting in two. Every type
flows through POS, FEFO batch costing, expiry alerts and reports unchanged.

Two type-aware behaviours:

- **`expiry_date` is now nullable.** A knee brace has no shelf life. But
  `Medicine.clean()` still *requires* an expiry date for consumable types —
  only `MEDICAL_DEVICE` and `OTHER` may omit it. Items with no expiry are
  excluded from expiry alerts and the expiry report rather than being
  treated as expired (verified by test).
- **`requires_prescription`** shows an `Rx` badge in the catalogue and an
  explicit confirmation dialog at the till before the item enters the
  basket. It is a counter-discipline aid, not a legal control — the
  pharmacist remains responsible.

New units were added for non-medicine goods: Pack, Roll, Pair, Sachet, Jar,
Unit.

## Oversell and input-validation fixes

Three genuine bugs, found by probing the checkout endpoint directly:

1. **Duplicate cart lines could oversell.** Validation compared each line
   against stock independently, so two lines of 490 against 500 stock both
   passed (490 ≤ 500 each) despite totalling 980. The batch layer caught it
   and rolled back, but the message was confusing and the check belonged
   earlier. Quantities are now **aggregated per product** before validating.
2. **A negative quantity returned HTTP 500** (`IntegrityError: CHECK
   constraint failed`) instead of a readable error.
3. **No bounds on discount or amount paid.**

All now return clean 400s with plain-language messages. Verified: over-stock,
duplicate lines, negative quantity, zero quantity, 500% discount, negative
payment and empty cart are each rejected, while a legitimate multi-line cart
for the same product still succeeds.

Also fixed: the **dashboard profit KPI** was still using the medicine's
current headline cost rather than each sale line's recorded batch cost, so it
disagreed with the Profit report. Both now use the batch figure, net of VAT.

## User guides

**One printable guide per role** (`docs/guides/`), each self-contained — a
Cashier should never have to read the Administrator's document to do their job,
so shared basics are repeated rather than cross-referenced. All four are
illustrated with labelled diagrams of the actual screens.

| Guide | Pages | Covers |
|---|---|---|
| `PharmaCare-Guide-1-Cashier.pdf` | 12 | Till workflow step by step, working in a branch, product types, Rx confirmations, receipts and reprints, looking products up in the catalogue, customers, who to ask |
| `PharmaCare-Guide-2-Pharmacist.pdf` | 14 | Dispensing, prescription verification sequence, the standard catalogue clinically, stock checks, expiry sweeps and quarantine, batches/FEFO, tracing stock in the ledger, stock aging, suppliers, the reports available |
| `PharmaCare-Guide-3-Store-Manager.pdf` | 23 | Registering from the catalogue, recording purchases, batch costing explained, own products/categories/suppliers, product types, shelf labels, stock movements, **running a stocktake**, **reorder planning**, **the ledger**, **stock aging**, **branch transfers**, all nine reports, month-end routine |
| `PharmaCare-Guide-4-Administrator.pdf` | 19 | First-run checklist, dashboard analytics interpretation, **managing branches**, staff and roles, **catalogue administration and authority imports**, voiding, deleting purchases, audit log, **stock ledger**, settings, backup discipline, security responsibilities |

Diagrams include: screen layout, the till, purchase form, inventory page,
dashboard, role matrix, batch costing, **branches (shared vs per-branch)**,
**branch transfers**, **the stocktake flow**, **catalogue registration** and
**the stock ledger**.

Also available: **`docs/USER_GUIDE.md`** (single-file written reference covering
all roles) and **`docs/VISUAL_GUIDE.html` / `.pdf`** (short shared picture
guide).

**Accuracy is checked, not assumed.** Before each release the guides are
verified against the running app: every `manage.py` command they mention
exists, all 25 documented destinations resolve, every menu label they tell users
to look for is actually in that role's menu, and the documented access table is
compared row by row against the permissions the code enforces.

**Regenerating them** after any UI change:

```powershell
python docs\build_guides.py
```

`docs/guide_assets.py` holds the styling and the reusable diagrams;
`docs/build_guides.py` holds the content. Both HTML and PDF are written to
`docs/guides/`. PDF rendering uses Playwright's Chromium — if it isn't
installed, the HTML is still produced.

Also retained: **`docs/USER_GUIDE.md`** (single-file written reference for
all roles) and **`docs/VISUAL_GUIDE.html` / `.pdf`** (a short shared
picture guide).

## Multi-tenancy (organizations)

The system now has an **Organization** (pharmacy company) above Branch:

```
Platform
 └── Organization (pharmacy company)
      └── Branch
           └── Stock, sales, purchases, accounting
```

Running with one organization behaves exactly as before. Nothing here changes
when more are added — only the seeding does.

### Scoping is enforced by the manager, not by call sites

The naive approach is `.filter(organization=...)` at every query. There were
already **118 query sites** and the accounting engine will roughly double
that, so relying on every future call site remembering is a hope, not a
control — and one forgotten filter is a silent cross-company leak.

Instead, models inheriting `OrganizationOwnedModel` filter automatically:

| Context | Behaviour |
|---|---|
| Organization set | Filtered to it |
| Web request, no organization | **Empty** — fails closed |
| Command / shell / migration | Unfiltered (platform-wide) |

Views needed no changes at all. Code that must cross organizations says so
explicitly via `Model.all_objects` or `with unscoped():`, both greppable in
review — so the safe path is the default and the dangerous one is visible.

The organization is derived **from the authenticated user**, never from a URL,
form field or header. If the client could supply it, it could forge it.

### Ownership inference

When a caller does not set an organization, `save()` fills it from the
request, or from the only organization that exists. With several
organizations and no request, the owner is genuinely unknown, so it stays
null rather than being guessed — attaching one company's data to another is
the exact failure tenancy prevents.

### Two admin levels

| Role | Scope |
|---|---|
| **System Administrator** | The platform. Belongs to **no organization** — that null is what grants platform scope. Manages organizations |
| **Administrator** (pharmacy) | Full power inside one company, none outside it |

```powershell
python manage.py create_system_admin --username you --email you@example.com
```

A system administrator sees **no pharmacy business data** until they
explicitly select an organization to work inside, so the boundary stays
visible rather than implicit.

### Upgrading an existing install

`organizations/migrations/0002_default_organization.py` creates one
organization from your existing pharmacy settings and assigns every branch,
product, category, customer, supplier, sale, purchase and staff account to
it. Platform staff are deliberately left unassigned.

### What is *not* organization-owned

The **standard product catalogue** is platform-level shared reference data,
not company data — one Paracetamol 500mg identity that every pharmacy
registers against. That is what makes cross-pharmacy reporting possible at
all.

### Tested

27 tenancy tests, including: another company's record is unreachable by URL
(returns 404, not 403 — existence itself is not disclosed), filtering by a
known foreign primary key returns nothing, strict mode denies when no
organization resolves, state does not leak between requests, and an
organization with trading data cannot be deleted.

## Fiscal year — configurable, Ethiopian by default

Default: the **Ethiopian government fiscal year, Hamle 1 → Sene 30**. Fully
changeable, in either calendar.

```powershell
python manage.py fiscal_years                # show the rule and stored periods
python manage.py fiscal_years --generate 3   # create the next three years
```

### The important guarantee: changing the rule never moves history

Two separate things:

- **`FiscalYearSettings`** — the rule used to generate *future* years. Change
  it whenever you like.
- **`FiscalYear`** — a concrete, dated period. Once created it keeps its dates;
  once **closed** they cannot be altered at all.

If the boundary were a live setting, changing it would silently re-slice every
historical period and every comparative statement with it. Instead, changing
the rule affects only years not yet generated. Verified by test.

| Rule | Period containing 1 Sep 2026 |
|---|---|
| Ethiopian, Hamle 1 *(default)* | 2026-07-08 → 2027-07-07, labelled **2018 EC** |
| Gregorian, 1 January | 2026-01-01 → 2026-12-31, labelled **2026** |
| Gregorian, 1 July | 2026-07-01 → 2027-06-30, labelled **2026/27** |

Closing is ordered and reversible: a year cannot be closed before it ends, nor
out of sequence, nor twice; reopening requires later years to be open first.
`is_date_postable()` is the hook the accounting engine will use to refuse
back-dated entries into a closed period.

> **Confirm the start date with your accountant.** Hamle 1 is the Ethiopian
> government year and the common default, but a company may file on a different
> accounting period. Getting this wrong misaligns every period close.

### Ethiopian calendar

`apps/core/ethiopian_calendar.py` converts via Julian Day Number, so the round
trip is exact. 13 months (twelve of 30 days plus Pagume), leap years where
`year % 4 == 3`. Verified against independent anchors: Ethiopian New Year falls
on 11 September, or 12 September in the year before a Gregorian leap year, and
4,000 consecutive days round-trip with zero mismatches.

## Automated tests

```powershell
python manage.py test
```

**121 tests.** They cover the behaviours that would be most expensive to get
wrong:

| Area | What is asserted |
|---|---|
| FEFO costing | Soonest-expiry batch is consumed first (by expiry, not arrival order); a sale spanning two batches records both costs; a later purchase never changes an earlier sale's profit; VAT is excluded from profit; discount applies before VAT |
| Oversell | Stock cannot go negative; duplicate cart lines are summed before checking; zero and negative quantities rejected |
| Voids | Stock returns to the exact batches it came from; a sale cannot be voided twice |
| Branch isolation | A branch cannot sell another branch's stock; selling at one leaves the other untouched; reorder levels stay independent; exactly one main branch |
| Transfers | Cost and expiry travel with the goods; nothing is created or destroyed; over-transfer, same-branch and inactive-destination all refused |
| Stock ledger | Ledger entries sum exactly to current stock; every cause is recorded; running balance matches |
| Stocktakes | Opening freezes expected figures against mid-count sales; **uncounted lines are left untouched on posting**; one open count per branch; no double-post |
| Catalogue | Prescription flag comes from the legal class, not the caller; no duplicate registration; blank barcodes stay NULL |
| Permissions | Full role × page matrix at the HTTP layer; restricted cost figures absent from the HTML, not merely hidden |
| Fiscal year | Calendar anchors, contiguous periods, ordered closing, and that changing the rule leaves history alone |

Access control is tested through the views rather than by calling permission
methods, because a view that forgets its mixin passes every model-level test
and still leaks.

> **Template comment gotcha, enforced by a check.** Django's `{# ... #}`
> comment is **single-line only**. A `{# ... #}` spanning several lines is not
> treated as a comment at all — it renders as visible text on the page, with
> no exception and no warning. This shipped once, appearing at the top of the
> dashboard. `apps/dashboard/checks.py` now flags it (and a `{% trans %}` used
> above `{% load i18n %}`) on every `manage.py check`, so it cannot recur.
> Use `{% comment %} ... {% endcomment %}` for anything multi-line.

## Standard product catalogue

Previously every pharmacy typed its own product names, producing
"Paracetamol 500mg", "paracetamol 500 mg", "PCM 500" and "Panadol 500mg" as
four unrelated products. Group reporting, price comparison and regulatory
returns are impossible on that basis.

`apps/catalogue` adds a shared reference catalogue. A pharmacy **registers**
stock against a standard record instead of naming it themselves.

### What the catalogue holds — and does not

It holds **identity**: INN generic name, brand, strength, dosage form, route,
ATC code, therapeutic category, legal class, pack size, manufacturer, country
of origin, EFDA registration number, GTIN barcode, essential-medicine and
cold-chain flags.

It deliberately holds **no prices and no stock** — those are commercial and
per-pharmacy, and stay on `Medicine`. A `Medicine` gains an optional
`catalogue_product` link, so something genuinely not in the catalogue can
still be added unlinked (it just won't roll up in group reporting, and the
catalogue page counts how many such products you have).

### Registering keeps the standard intact

`register_product` copies identity across and **the legal class decides the
prescription flag, not the person registering** — so a prescription-only
medicine cannot be registered as over-the-counter. It also refuses to
register the same catalogue record twice, naming the existing product code
instead, since duplication is exactly what the catalogue prevents. Expiry is
required for consumables and optional for devices, consistent with the
product-type rules.

### Provenance is recorded, and the bundled data is labelled honestly

`data_source` is one of EFDA, WHO_EML, STARTER or LOCAL, and the UI shows a
"Verified" badge only for the first two.

**The 66 bundled entries are marked `STARTER`, not `EFDA`.** They are common
INN medicines, dosage forms and ATC codes of the kind found on the WHO Model
List of Essential Medicines. They are **not an extract of the EFDA register**,
and `efda_registration_number` is left blank rather than guessed — a wrong
registration number on a regulatory return is worse than a missing one. This
is stated on the catalogue page itself, not just here.

To use the authority's own list:

```powershell
python manage.py import_catalogue efda_register.csv --source EFDA --dry-run
python manage.py import_catalogue efda_register.csv --source EFDA
```

Matching is on generic name + strength + form + brand, so re-importing an
updated list revises rows in place. Unknown dosage forms are **reported and
skipped rather than mapped to "Other"**, because silently coercing them would
corrupt the standardisation the catalogue exists to provide.

### Access

| | Administrator | Store Manager | Pharmacist | Cashier |
|---|:---:|:---:|:---:|:---:|
| Browse catalogue | ✅ | ✅ | ✅ | ✅ |
| Register a product / add an entry | ✅ | ✅ | ❌ 403 | ❌ 403 |

## Full inventory management

Four additions on top of batches, FEFO costing, movements and transfers.

### 1. Stock ledger — a complete audit trail

The movement log used to record only *manual* moves. Sales and purchases
changed stock without writing to it, so the log could never answer "why is
this number what it is?".

`StockLedger` records **every** change with a running balance and a link to
the document responsible: purchases, sales, voids, deleted purchases,
transfers (both sides), manual movements and stocktakes. It is written
centrally in `allocation._adjust_branch_stock` — the one funnel every stock
change already passed through — so a new caller gets complete history for
free and cannot forget to log.

Append-only: no edit or delete route exists in the UI or the admin. Verified
that the ledger's `balance_after` matches `BranchStock` exactly after a
purchase, sale, stock-out, transfer and void in sequence.

### 2. Stocktakes — count, review, post

`Inventory → Stocktakes`. Opening a count **freezes the expected quantity**
for everything in scope, which matters because counting a large branch takes
hours and without the snapshot a sale made mid-count would look like a
counting error.

- Count a whole branch or one category at a time.
- Counts save **separately from posting**, so a count can span shifts without
  losing work; there is a printable count sheet.
- Filter views: all / not yet counted / counted / differences only.
- Posting creates one adjustment per differing line, so a count that
  confirmed 400 correct products does not add 400 no-op ledger rows.

**The critical default:** an empty count box means *not counted*, never zero.
Uncounted lines are skipped on posting rather than wiping out stock nobody
got round to counting. Verified by test, along with: only one open stocktake
per branch, posting twice changes nothing, and counts lock after posting.

### 3. Reorder plan — how much to order, not just what

`Inventory → Reorder Plan`. A reorder level tells you *that* something is
low, not *how much* to buy. This measures units sold per day over a 60-day
window, works out days of cover remaining, and suggests a quantity that
restores a target number of days (adjustable). Grouped **by supplier**,
because an order is placed with a supplier rather than with a spreadsheet.

Products with no recent sales have no velocity to measure, so rather than
suggesting nothing for something that has genuinely run out, the suggestion
falls back to topping up to twice the reorder level — and the days-of-cover
column shows a dash so the basis is visible.

### 4. Stock aging — value at risk by shelf life

`Inventory → Stock Aging`. Buckets stock on hand by remaining life
(expired / 0–30 / 31–90 / 91–180 / 180+ / no expiry) and values each bucket
at **actual batch cost**, not the product's headline cost. Different from the
expiry report, which counts items: a small number of expensive items expiring
matters more than a large number of cheap ones.

### Access

| | Administrator | Store Manager | Pharmacist | Cashier |
|---|:---:|:---:|:---:|:---:|
| Stock ledger | ✅ | ✅ | ✅ | ❌ 403 |
| Stock aging | ✅ | ✅ | ✅ | ❌ 403 |
| Stocktakes | ✅ | ✅ | ❌ 403 | ❌ 403 |
| Reorder plan | ✅ | ✅ | ❌ 403 | ❌ 403 |

Cost and value columns are hidden from roles not cleared for cost data, on
every one of these pages.

### Not included

Worth being explicit about what a larger IMS would add and this does not:
purchase-order documents with a draft→sent→received lifecycle (record the
order through Purchases when goods arrive), stock in transit between branches
(transfers are instantaneous), supplier returns as a distinct document type
(use Stock Out), and serial-number tracking.

## Multiple branches

Stock is per branch; the catalogue and customers are shared. A paracetamol is
the same product everywhere, and a customer keeps one loyalty balance wherever
they shop — but the stock behind them is separate, and so is everything that
moves it.

| Shared across branches | Per branch |
|---|---|
| Products, categories, suppliers | Stock quantity and reorder level |
| Customers and loyalty points | Batches (and therefore cost) |
| Pharmacy settings | Sales, purchases, stock movements |
| Staff accounts | Notifications, invoice number prefix |

### How it is modelled

`BranchStock` holds quantity and reorder level for each (branch, product)
pair. Putting a branch field on `Medicine` instead would have forced one
product row per branch, duplicating every name, price and barcode — which
then drift apart. `Medicine.quantity` survives as a **cached rollup** of the
per-branch figures, kept in step by `BranchStock.save()`, so pharmacy-wide
reports and the shared catalogue page still read a sensible total.

**Reorder level is per branch on purpose.** A busy city branch should not be
forced to reorder at the same threshold as a quiet rural one.

### Access

`BranchContextMiddleware` resolves `request.branch` once per request:

- A user with a branch assigned always gets that branch, and **cannot switch**.
  This is enforced server-side, not by hiding a dropdown — verified by test
  that neither `?branch=<id>` nor a crafted POST to the switcher changes it.
- An **Administrator** (no branch assigned) may switch; the choice lives in the
  session and is re-validated every request, so revoking access or
  deactivating a branch takes effect immediately rather than at next login.
- A blank branch on a user is meaningful, not missing: it is what grants the
  cross-branch view. For any other role it means no stock to work with, and
  the staff form says so.

### Transfers carry cost and expiry

`apps/inventory/transfers.py` moves stock between branches atomically. Units
arrive at the destination **at the cost they left at**, batch by batch, with
their original expiry dates. Receiving them at the destination's average cost
would quietly manufacture or destroy profit every time stock moved, and make
each branch's margin depend on transfer history rather than on trading.
Expiry travels too, so the destination keeps dispensing FEFO correctly.

### What became branch-aware

- **Till**: search only offers what this branch holds, and checkout validates
  against `BranchStock`, not the rollup — so a branch cannot sell stock that
  physically sits elsewhere.
- **Purchases**: goods land at the receiving branch.
- **Stock movements**: all four types act on one branch; `TRANSFER` with a
  destination branch performs a real two-sided move.
- **Reports**: sales, summary, purchase, profit, inventory, low stock and
  expiry all filter by branch, and every export names the branch it covers.
  Low Stock run pharmacy-wide lists each branch separately, so a shortage in
  one branch is not masked by a surplus in another. Supplier and Customer
  reports are deliberately *not* branch-scoped.
- **Dashboard**: every KPI and all nine charts follow the selected branch.
- **Notifications**: raised per (branch, product) and shown only to staff at
  that branch.

### Upgrading an existing single-branch install

`branches/migrations/0002_create_main_branch.py` creates a "Main Branch",
copies each product's quantity into a `BranchStock` row, stamps existing
batches, sales, purchases and movements with it, and assigns existing staff to
it — **leaving Administrators unassigned**, since that is what preserves their
cross-branch access. Safe on an empty database too, so a fresh install gets a
usable Main Branch out of the box.

### New screens

Branches list · branch detail (staff, reorder list, recent sales) · branch
form · per-branch stock · **stock comparison grid** across all branches ·
transfer form · navbar branch indicator (switcher for Administrators, static
label for everyone else).

## Batch costing — how profit stays accurate when prices change

**The problem.** A Medicine used to carry a single `purchase_price`. Buy more
at a different cost and that field had to be overwritten, which silently
rewrote history: last month's profit got recalculated at this month's cost.

**The fix.** Each intake is now a `StockBatch` with its own unit cost and
remaining quantity (`apps/inventory/batches.py`). Sales consume batches
**FEFO - first-expired-first-out**, which is the correct rule for a pharmacy
(you dispense what expires soonest, not what arrived first). Every sale line
records the actual cost of the units it consumed, plus a `SaleItemCost` row
per batch as an audit trail.

Worked example, verified by test:

| | Quantity | Cost each | Sold at |
|---|---|---|---|
| First intake | 40 | 20 | 50 |
| Second intake | 100 | 30 | 60 |

Selling 50 units draws 40 @ 20 + 10 @ 30 = **1,100 cost**. Revenue excluding
VAT is 3,000, so gross profit is **1,900** - and buying more stock at 45
afterwards leaves that figure untouched.

Notes:

- **VAT is excluded from profit.** It is collected for the tax authority and
  was never margin; including it overstated profit in the old report.
- **`Medicine.quantity` is retained** as the fast authoritative total and
  always equals the sum of `quantity_remaining` across batches.
  `verify_consistency()` asserts this.
- **Voiding a sale returns units to their original batches**, so a void and
  re-sale reports the same profit as the original would have.
- **Deleting a purchase only removes unsold units.** Clawing back dispensed
  stock would corrupt both the count and the recorded cost of those sales.
- **Stock predating batch tracking** (or typed straight onto the medicine
  form) is converted to an `OPENING` batch at the medicine's recorded cost by
  `ensure_opening_batch()`, so a sale never fails for lack of batch coverage.
- **Selling price changes are forward-only.** The optional *New Selling
  Price* on a purchase line updates the medicine going forward; past sales
  keep the price they were sold at.

See **Inventory > Batches** in the UI for per-batch costs and FEFO order.

## Duplicate customers

`Customer.phone` is `unique`, and `CustomerForm.clean_phone()` normalises
away spaces and hyphens before checking - so `0911 22 33 44` and
`0911223344` are recognised as the same customer. The error names the
existing record rather than saying "already exists", because the useful next
action is to open that customer, not to invent a different number.

Duplicates matter more here than in most systems: a second record silently
splits a customer's purchase history and loyalty points.

## Dashboard access & role landing pages

The dashboard is **Administrator-only**. It aggregates cost prices, gross
margin, per-staff performance and company-wide figures, none of which the
other roles should see.

Because of that, every other role needs somewhere sensible to land — sending
them to a 403 on login would be broken. `dashboard:landing`
(`apps/dashboard/views.py::RoleLandingView`) resolves the right destination
per role and is wired to both `LOGIN_REDIRECT_URL` and the site root `/`:

| Role | Lands on |
|---|---|
| Administrator | Dashboard (`/dashboard/`) |
| Cashier | Point of Sale (`/sales/pos/`) |
| Pharmacist | Point of Sale (`/sales/pos/`) |
| Store Manager | Inventory overview (`/inventory/`) |
| *(any future role)* | Own profile — safe fallback, never a 403 |

The sidebar Dashboard link is hidden for non-administrators too, so the UI
never advertises a page the user cannot open.

### Analytics on the dashboard

Beyond the four operational charts, the dashboard carries five analytical
ones, all computed from live data:

- **Revenue vs Cost of Goods Sold** — grouped bars per month; the gap is
  gross margin, which is the single most useful figure on the page.
- **Payment Method Mix** — split by *revenue*, not transaction count, so it
  shows where the money actually arrives.
- **Expiry Risk Profile** — medicines bucketed by remaining shelf life,
  with **value at risk** overlaid as a line. Item count alone is
  misleading: one expired box of cheap tablets is not the same problem as
  expired insulin.
- **Top Customers by Spend** — lifetime value, horizontal bars so names
  stay readable.
- **Sales by Staff Member** — revenue served, completed sales only.

## Searchable dropdowns

Long `<select>` lists (medicines, categories, suppliers, customers) are
type-to-search via [Tom Select](https://tom-select.js.org/), enhanced
automatically in `static/js/pharmacare.js`: any single select with more than
8 options is upgraded. Escape hatches — add `class="no-search"` to opt a
field out, or `class="searchable"` to force it on a short list. Pages that
build their own instances (the purchase form's dynamic rows) are skipped
automatically, since Tom Select sets `el.tomselect` once initialised.

## Purchase line items

The purchase form opens with **one** empty line-item row and grows on
demand via the **+ Add Item** button, which clones Django's
`formset.empty_form`, substitutes the `__prefix__` placeholder for the new
index, and increments `TOTAL_FORMS`. There is no fixed ceiling on items.

Two details worth knowing if you touch this:

- `inlineformset_factory` renders `min_num + extra` forms. With
  `min_num=1`, `extra` must be **0** to get exactly one starting row —
  `extra=1` renders two.
- Removing a row that already exists in the database ticks its hidden
  `DELETE` checkbox and hides the row, rather than removing it from the
  DOM. Dropping a saved row from the POST entirely would make Django's
  formset validation fail on the missing index.

The form also shows a live per-line total and running invoice total, using
the same discount-then-VAT order as `PurchaseItem.line_total` server-side,
so the figure on screen matches what gets saved.

## Adding a new language or extending translations

```bash
# After adding new {% trans %} tags or verbose_name=_(...) strings:
python manage.py makemessages -l am --no-location --no-obsolete

# Edit locale/am/LC_MESSAGES/django.po, then:
python manage.py compilemessages
```

**Caution — two related traps with `makemessages`, both of which bit this
project during development:**

1. **Fuzzy matching invents wrong translations.** When a new string
   resembles an existing one, `makemessages` copies that translation over
   and marks it `#, fuzzy`. Real examples caught here: `"Cash"` was given
   the Amharic for *Cashier*, `"Change due"` the Amharic for *Change
   language*, `"Add"` the Amharic for *Address*, and `"Medicine Name"` the
   Amharic for *Medicine Code*. Always review each fuzzy entry against its
   own msgid before accepting it.

2. **`msgfmt` silently drops fuzzy entries from the compiled `.mo`.** This
   is standard gettext behaviour, and it means a translation can be
   perfectly correct in the `.po` file and still render in English on the
   page, with no error anywhere. If a string refuses to translate, check
   for a `#, fuzzy` flag on it first.

Useful commands:

```powershell
# List entries needing human review (do this before every compile)
msgattrib --only-fuzzy locale\am\LC_MESSAGES\django.po

# List anything still untranslated
msgattrib --untranslated locale\am\LC_MESSAGES\django.po

# Confirm what actually made it into the .mo — the count here should match
# your expected total; anything fuzzy is excluded from it
msgfmt --check --statistics locale\am\LC_MESSAGES\django.po -o NUL
```

A useful sanity check for wrong-reuse: group entries by their translation
and inspect any Amharic string used for two *semantically different*
English strings. Case variants (`"Sign In"` / `"Sign in"`) sharing one
translation are fine; `"Cash"` and `"Cashier"` sharing one are a bug.

## Hosting it

See **`DEPLOYMENT.md`** for a step-by-step walkthrough: pushing to GitHub,
creating a free managed Postgres database, and deploying to Vercel (with an
honest account of where Vercel's serverless model conflicts with this app) or
to Render as the closer-to-normal-server alternative.

Deployment files included: `vercel.json`, `api/index.py`, `.vercelignore`.
Settings now read a single `DATABASE_URL`, serve static files through
WhiteNoise without a build step, trust the platform's HTTPS terminator, and
read the real client IP from `X-Forwarded-For` so one user's failed logins
cannot lock out everyone.

## Getting started (development — Windows)

These steps assume Windows 10/11 with Python 3.11+ installed (get it from
[python.org](https://www.python.org/downloads/) — tick **"Add python.exe to
PATH"** during install) and PowerShell as your shell. Commands for Command
Prompt (`cmd.exe`) are noted where they differ.

```powershell
# 1. Create and activate a virtual environment
python -m venv venv
venv\Scripts\Activate.ps1
# cmd.exe equivalent:  venv\Scripts\activate.bat
# If PowerShell blocks the script with an "execution policy" error, run
# this once first: Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

# 2. Install dependencies
pip install -r requirements.txt

# 3. Install gettext (needed to compile Amharic translations)
#    Windows has no built-in gettext. Easiest options:
#      a) Chocolatey (https://chocolatey.org/install), then:
choco install gettext
#      b) Or download the precompiled binaries from
#         https://mlocati.github.io/articles/gettext-iconv-windows.html
#         and add their bin\ folder to your PATH.
#    Verify it worked:
msgfmt --version

# 4. Configure environment
copy .env.example .env
# defaults work out of the box for local dev — edit .env in Notepad if needed

# 5. Run migrations
python manage.py migrate

# 6. Compile translations
python manage.py compilemessages

# 7. Seed demo accounts (one per role)
python manage.py seed_accounts
# Creates: admin / pharmacist1 / cashier1 / storemanager1
# Password for all: PharmaCare2026!  (change immediately outside local dev)
# Note: demo accounts skip the forced-password-change flow so you can
# explore the app immediately; real admin-created accounts will NOT skip it.

# 8. (Optional) Seed sample catalog data — categories, suppliers,
#    customers, and medicines, so Phase 2/3 screens aren't empty
python manage.py seed_catalog

# 9. Run the server
python manage.py runserver

# 10. (Optional) Generate the first batch of notifications
python manage.py refresh_notifications

# 11. Visit in your browser
http://127.0.0.1:8000/            # role-aware landing page (login required)
http://127.0.0.1:8000/admin/      # Django admin
```

**Keeping alerts current.** Low-stock, expiry and pending-payment alerts are
recomputed on demand (there is a Refresh button on the Notifications page).
To keep them fresh even when nobody is logged in, schedule the command with
Windows Task Scheduler:

- Program: `C:\path\to\venv\Scripts\python.exe`
- Arguments: `manage.py refresh_notifications`
- Start in: `C:\path\to\pharmacare`

**First-run configuration.** Log in as `admin` and open **Settings** to set
the pharmacy name, logo, currency, tax rate, invoice prefix/footer, and
licence/TIN numbers. Until you do, the values from `.env` are used.

**Troubleshooting on Windows:**
- `'python' is not recognized` — Python wasn't added to PATH during install;
  re-run the installer and tick that option, or use `py` instead of `python`.
- `pip install` fails on `psycopg2-binary` or `Pillow` — make sure you're
  using a 64-bit Python 3.11+ install; both ship prebuilt wheels for
  Windows and shouldn't need a compiler.
- Antivirus/Defender flagging `venv\Scripts\python.exe` — this is a common
  false positive with virtual environments; add an exclusion for the
  project folder if it happens.

## Switching to PostgreSQL (production)

Set in your `.env` (or real environment variables):

```
DJANGO_ENV=production
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=yourdomain.com
DATABASE_NAME=pharmacare
DATABASE_USER=pharmacare_user
DATABASE_PASSWORD=********
DATABASE_HOST=localhost
DATABASE_PORT=5432
```

Then run `python manage.py migrate` again against Postgres. `DEBUG=False`
automatically turns on HSTS, secure cookies, and SSL redirect (already
configured in `settings.py`).

**Serving in production on Windows:** `gunicorn` (listed in
`requirements.txt`) does not run on Windows — it depends on the `fcntl`
module, which is Unix-only. For a Windows-hosted deployment, use
[waitress](https://docs.pylonsproject.org/projects/waitress/) instead:

```powershell
pip install waitress
waitress-serve --host=0.0.0.0 --port=8000 pharmacare.wsgi:application
```

Alternatively, deploy behind IIS with
[wfastcgi](https://learn.microsoft.com/en-us/visualstudio/python/configure-web-apps-for-iis-windows),
or run the project inside Docker / WSL2 (Windows Subsystem for Linux) and
use `gunicorn` there as originally intended — either is a reasonable choice
for an NBE-regulated deployment where the hosting environment is typically
Linux-based regardless of the development machine's OS.

## Security notes

- Account lockout thresholds are configurable via `AXES_FAILURE_LIMIT` and
  `AXES_COOLOFF_TIME` in `.env` (defaults: 5 attempts, 30-minute cooldown)
- Role checks happen server-side on every view (`RoleRequiredMixin` /
  `role_required`), not just hidden in the UI
- New/reset accounts cannot bypass the mandatory password change —
  enforced by `ForcePasswordChangeMiddleware`, verified with an end-to-end
  test that confirms the dashboard is unreachable until the password is set
- `CurrentUserMiddleware` is already wired in so the Phase 6 Audit Log can
  attribute every database change to a user without threading `request`
  through every function
- Rotate `DJANGO_SECRET_KEY` and the demo account passwords before any
  shared or production deployment
- If you ever get accidentally locked out during development, run
  `python manage.py axes_reset`

## Roadmap

| Phase | Scope |
|---|---|
| **1 ✅** | Project setup, authentication, RBAC, dashboard, i18n (EN/AM), security hardening, design system |
| **2 ✅** | Medicine, Category, Supplier, Customer management — differentiated role-based access, barcode/QR labels |
| **3 ✅** | Purchases (auto stock increase, immutable ledger) & Inventory (stock in/out/adjustment/transfer, low-stock/out-of-stock reports) |
| **4 ✅** | POS terminal (barcode + search, cart, discount/VAT, Cash/Card/Mobile Money), printable invoices, void-with-stock-return, live dashboard charts |
| **5 ✅** | Nine reports (sales/summary/purchase/profit/inventory/low-stock/expiry/supplier/customer) with per-report RBAC, cost masking, and PDF/Excel/CSV export |
| **6 ✅** | Notifications (5 alert types, self-resolving), append-only Audit Log with IP tracking, DB-backed Settings + backup |

Say "continue" / "build Phase 2" to proceed.
