# PharmaCare — User Guide

**For:** pharmacy staff (Administrators, Pharmacists, Cashiers, Store Managers)
**Version:** 1.0 · Covers all six modules

---

## Contents

1. [Before you start](#1-before-you-start)
2. [What your role can do](#2-what-your-role-can-do)
3. [Guide for Cashiers](#3-guide-for-cashiers)
4. [Guide for Pharmacists](#4-guide-for-pharmacists)
5. [Guide for Store Managers](#5-guide-for-store-managers)
6. [Guide for Administrators](#6-guide-for-administrators)
7. [How profit is calculated (batch costing)](#7-how-profit-is-calculated-batch-costing)
8. [Working across branches](#8-working-across-branches)
9. [The standard catalogue](#9-the-standard-catalogue)
10. [Stocktakes, the ledger and reorder planning](#10-stocktakes-the-ledger-and-reorder-planning)
11. [Common tasks, step by step](#11-common-tasks-step-by-step)
12. [Troubleshooting](#12-troubleshooting)

> **Printable guides.** Each role also has its own illustrated PDF in
> `docs/guides/` — Cashier (12 pages), Pharmacist (14), Store Manager (23),
> Administrator (19). Those are the ones to hand to staff; this file is the
> single-document reference.

---

## 1. Before you start

### Signing in

Go to the address your Administrator gave you (usually
`http://<server>:8000/`) and sign in with your username and password.

**First sign-in:** if your account was just created, or an Administrator
reset your password, you'll be asked to set a new password before you can
do anything else. This is deliberate — nobody, including the Administrator,
should know your working password. Your new password needs at least **10
characters**, including an uppercase letter, a lowercase letter, a number,
and a symbol.

**Where you land after signing in** depends on your role, so you start on
the page you actually need:

| Your role | You land on |
|---|---|
| Cashier | Point of Sale |
| Pharmacist | Point of Sale |
| Store Manager | Inventory |
| Administrator | Dashboard |

### Changing the language

Click the **globe icon** in the top bar and choose **English** or **አማርኛ**.
The whole interface switches immediately, including printed invoices and
exported reports. Your choice is remembered.

### Dark mode

Toggle the **moon icon** in the top bar. Also remembered.

### On a phone or tablet

The interface works on small screens. Tap the **☰ menu button** (top left)
to open the sidebar; tap outside it to close.

### If you get locked out

Five wrong passwords in a row locks the account **and** that computer's
network address for 30 minutes. This protects against someone guessing
passwords. Wait it out, or ask an Administrator. Use **Forgot your
password?** on the sign-in page if you genuinely can't remember it.

---

## 2. What your role can do

A tick means you can do it; a dash means the page will refuse you.

| | Administrator | Store Manager | Pharmacist | Cashier |
|---|:---:|:---:|:---:|:---:|
| Dashboard & analytics | ✅ | – | – | – |
| Point of Sale (ring up sales) | ✅ | – | ✅ | ✅ |
| Sales history & reprint receipts | ✅ | ✅ | ✅ | ✅ |
| Void a sale | ✅ | – | – | – |
| View medicines | ✅ | ✅ | ✅ | ✅ |
| Add / edit / delete medicines & categories | ✅ | ✅ | – | – |
| See **cost prices** | ✅ | ✅ | – | – |
| View suppliers | ✅ | ✅ | ✅ | – |
| Add / edit suppliers | ✅ | ✅ | – | – |
| Add / edit customers | ✅ | ✅ | ✅ | ✅ |
| Delete customers | ✅ | ✅ | – | – |
| Adjust customer loyalty points | ✅ | ✅ | – | – |
| Record purchases | ✅ | ✅ | – | – |
| Delete a purchase | ✅ | – | – | – |
| Inventory & stock reports | ✅ | ✅ | ✅ | – |
| Record stock movements | ✅ | ✅ | – | – |
| Reports — sales, summary, customers | ✅ | ✅ | ✅ | ✅ |
| Reports — inventory, low stock, expiry, suppliers | ✅ | ✅ | ✅ | – |
| Reports — **purchases and profit** | ✅ | ✅ | – | – |
| Export reports (PDF / Excel / CSV) | ✅ | ✅ | – | – |
| Notifications | ✅ | ✅ | ✅ | ✅ |
| Browse standard catalogue | ✅ | ✅ | ✅ | ✅ |
| Register / add catalogue entries | ✅ | ✅ | – | – |
| Branch stock page | ✅ | ✅ | ✅ | – |
| Transfer stock between branches | ✅ | ✅ | – | – |
| Manage branches | ✅ | – | – | – |
| Switch active branch | ✅ | – | – | – |
| Stock ledger | ✅ | ✅ | ✅ | – |
| Stock aging | ✅ | ✅ | ✅ | – |
| Stocktakes | ✅ | ✅ | – | – |
| Reorder plan | ✅ | ✅ | – | – |
| Audit log | ✅ | – | – | – |
| Settings & database backup | ✅ | – | – | – |
| Manage staff accounts | ✅ | – | – | – |

**Why cost prices are hidden from Cashiers and Pharmacists.** What the
pharmacy pays suppliers is commercially sensitive. Those roles see the
selling price everywhere they need it, but never the cost, the margin, or
the purchase records. This applies to screens *and* to data — the till's
medicine lookup does not transmit cost prices at all.

**Why the Store Manager can't use the till, and the Cashier can't see
stock reports.** Permissions follow the actual job rather than seniority.
The Store Manager's work is purchasing and stock; the Cashier's is the
counter. Neither is "above" the other.

---

## 3. Guide for Cashiers

Your day is mostly one screen: **Point of Sale**.

### Ringing up a sale

1. Open **Point of Sale** from the sidebar (it's also where you land after
   signing in).
2. **Add items**, either way:
   - **Scan the barcode.** The cursor sits in the search box ready. A
     scanner types the code and presses Enter for you; on an exact match
     the item drops straight into the cart.
   - **Type to search** by name, code, or generic name. Results appear as
     you type — click a row or its **Add** button.
3. **Adjust the cart** on the right:
   - Change **Qty** for more than one. You can't exceed available stock —
     the system will tell you what's left.
   - Enter a **Disc %** for a per-item discount.
   - Click the **✕** to remove a line.
   - Totals (subtotal, discount, VAT, grand total) update as you type.
4. **Choose the customer** — leave it on *Walk-in customer* if they're not
   registered. Selecting a named customer earns them loyalty points.
5. **Choose the payment method** — Cash, Card, or Mobile Money.
6. **Enter Amount Paid.** The **Change due** figure updates live.
7. Click **Complete Sale**. You'll see the invoice number and change due.
   Choose **View / Print Invoice** to print a receipt, or **New Sale** to
   start the next customer.

Stock is reduced the moment the sale completes.

### Reprinting a receipt

**Sales** in the sidebar → find the invoice (search by number or customer
name) → the **receipt icon** → **Print**.

### Registering a customer

**Customers** → **Add Customer**. Name and phone are required.

> **The phone number must be unique.** If it's already registered you'll be
> told which customer has it — open that record instead of making a second
> one. Duplicates split a person's purchase history and loyalty points
> across two records, which is hard to unpick later. Spaces and hyphens are
> ignored, so `0911 22 33 44` and `0911223344` count as the same number.

You can't adjust loyalty points yourself — that field only appears for
Administrators and Store Managers. Points are awarded automatically on
sales.

### Notifications

The **bell** in the top bar shows unread alerts for your role. Click one to
jump to what it's about, or open **Notifications** for the full list.

### What you can't do — and who to ask

| You need to… | Ask a… |
|---|---|
| Correct a completed sale | Administrator (only they can void) |
| Add or edit a medicine or price | Store Manager or Administrator |
| Check stock levels or expiry reports | Pharmacist, Store Manager, or Administrator |
| Delete a customer | Store Manager or Administrator |

---

## 4. Guide for Pharmacists

You have the Cashier's till duties **plus** stock visibility — everything in
[section 3](#3-guide-for-cashiers) applies to you as well.

### Checking stock before dispensing

**Inventory** in the sidebar shows the full current stock list. You can:

- **Search** by medicine name or code.
- **Filter** by *Low stock*, *Out of stock*, or *Expired*.
- Click the four cards at the top to jump straight to **Low Stock**,
  **Out of Stock**, or **Expired** lists.

### Expiry checks

Click the **Expired Medicines** card, or go to **Inventory → Expired**.
Three tabs:

- **Expired** — already past expiry. Do not dispense. Quarantine it and ask
  a Store Manager to write it off.
- **Within 30 days** — use first, or plan a return to the supplier.
- **Within 60 days** — keep an eye on it.

The system dispenses stock on a **first-expired-first-out** basis
automatically, so selling normally already runs down the soonest-expiring
batch first.

### Batches

**Inventory → Batches** shows each intake of a medicine separately, with its
expiry date and how much is left. Useful when a medicine has arrived in
several deliveries. You won't see cost figures — those are restricted.

### Suppliers

You can **view** supplier records (useful for chasing a delivery or checking
who supplies what) but not change them.

### Reports available to you

Sales, Sales Summary, Customers, Inventory, Low Stock, Expiry, Suppliers.
You can view and print them, but not export files — ask a Store Manager or
Administrator if you need a PDF or spreadsheet to send on.

Purchase and Profit reports are not available to your role.

---

## 5. Guide for Store Managers

Your focus is **stock and purchasing**. You don't operate the till.

### Recording a purchase (this is the important one)

**Purchases → Record Purchase**.

1. Choose the **Supplier** and the **Purchase Date**.
2. The form opens with **one** line item. Click **+ Add Item** for each
   additional medicine — as many as you need.
3. For each line:
   - **Medicine** — type to search.
   - **Quantity** received.
   - **Purchase Price** — the unit cost **for this delivery**.
   - **New Selling Price** — *optional*. Fill this in **only if this
     delivery changes what you charge customers.* Leave blank to keep the
     current price.
   - **Discount %** and **VAT %** for the supplier invoice.
   - The line total and the running **Invoice Total** update as you type.
4. Click **Save Purchase & Update Stock**.

**What happens:** stock increases immediately, and this delivery is stored
as its **own batch with its own cost**. This is what keeps profit accurate
when prices change — see [section 7](#7-how-profit-is-calculated-batch-costing).

> Purchases cannot be edited after saving. This is intentional: a purchase
> is a financial record, and silently editing one would rewrite history. If
> you make a mistake, ask an Administrator to delete it (which also reverses
> the stock) and record it again.

### Stock movements

**Inventory → Record Stock Movement** for anything that isn't a purchase or
a sale:

| Type | Use it for | What to enter in Quantity |
|---|---|---|
| **Stock In** | Found stock, a donation, a manufacturer sample | How many to **add** |
| **Stock Out** | Breakage, spillage, internal use, expiry write-off | How many to **remove** |
| **Stock Adjustment** | After a physical count | The **new counted total** — not the difference |
| **Stock Transfer** | Stock leaving for another branch | How many are leaving (a **Destination** is required) |

Every movement is logged with your name, the before and after quantities,
and the reason. Always fill in **Reason** — the whole point of the log is
that someone can understand it a month later.

**Stock Adjustment is an absolute figure, not a delta.** If the system says
100 and you counted 94, enter **94**, not 6. A count of **0** is allowed and
writes the product off entirely — useful for a batch that turned out to be
expired or damaged.

### Managing the catalogue

**Medicines** → **Add Medicine** / edit.

> **Medicines must link to the standard catalogue.** If Product Type is
> Medicine, this form requires a catalogue entry — pick one, or use
> **Standard Catalogue → Register** instead (§9). Once linked, Name and
> Generic Name are taken from the catalogue and can't be edited here; that's
> what keeps "Paracetamol" from becoming three unrelated products across the
> system. Non-medicine types (Cosmetic, Medical Supply, Supplement, Baby &
> Mother Care, Medical Device, Other) have no such requirement and are typed
> in freely, exactly as below.

Notable fields:

- **Medicine Code** is generated automatically (`MED-000001`).
- **Reorder Level** drives the Low Stock alerts — set it to the point where
  you'd want to reorder, not to zero.
- **Purchase Price** here is the *current headline* cost. Actual costing
  comes from batches, so this field is a reference figure.
- **Barcode** — if the product has one, enter it so the till can scan it.

**Categories** and **Suppliers** work the same way. A category can't be
deleted while medicines are still assigned to it; move them first.

### Shelf labels

Open a medicine → **Print Label**. Prints a label with a scannable barcode,
a QR code, the price, and the expiry date.

### Reports and exports

You have access to everything, including **Purchases** and **Profit**, and
you can **export** to PDF, Excel, or CSV. Exports carry a footer noting
AI-assisted output — review anything before sending it outside the pharmacy.

### What you can't do

Operate the till, delete a purchase, view the audit log, or change Settings.
Ask an Administrator.

---

## 6. Guide for Administrators

You can do everything. The parts unique to you:

### Dashboard

Your landing page, and yours alone — it shows cost prices, margins, and
per-staff performance.

- **Nine KPI cards.** Every card is clickable and takes you to the detail
  behind the number.
- **Four operational charts:** monthly sales, sales trend, top sellers,
  stock by category.
- **Five analytical charts:**
  - **Revenue vs Cost of Goods Sold** — the gap between the bars is your
    gross margin. The most useful figure on the page.
  - **Payment Method Mix** — by revenue, not transaction count, so it shows
    where the money actually arrives.
  - **Expiry Risk Profile** — items by remaining shelf life, with **value at
    risk** overlaid. Watch the line, not just the bars: one expired box of
    cheap tablets is not the same problem as expired insulin.
  - **Top Customers by Spend** — who's worth retaining.
  - **Sales by Staff Member** — revenue served.

### Managing staff

**Staff & Roles** → **Add Staff**. Set their role carefully — it decides
everything they can reach. New accounts must change their password on first
sign-in, so give them a temporary one and let them replace it.

Prefer **deactivating** (untick *Active Employee*) over deleting, so the
audit history keeps their name.

### Voiding a sale

Only you can. **Sales** → open the invoice → **Void** → give a reason.

The stock goes back to the **exact batches it came from**, so costing stays
honest. The invoice stays on record marked *Voided* — it isn't deleted,
because a financial record shouldn't vanish. A sale can't be voided twice.

### Deleting a purchase

**Purchases** → open it → **Delete**. This reverses the stock it added.
Units already sold are left alone — clawing those back would corrupt both
the count and the recorded cost of those sales.

### Audit log

**Audit Log** shows who changed what, when, and from which network address.

- It is **append-only** — nobody, including you, can edit or delete entries.
- **Failed sign-ins are recorded** with the attempted username (never the
  password). Repeated failures from one address are worth investigating.
- Filter by action, record type, or user.

### Settings

**Settings** covers pharmacy name, logo, phone, address, licence and TIN
numbers, currency, default tax rate, invoice prefix and footer, the
**large-sale alert threshold**, and the **loyalty point rate**.

These flow through to the interface, printed invoices, and shelf labels.
Set them up before going live.

### Database backup

**Settings → Download Backup**.

- On **SQLite** (typical for a single-branch setup) this downloads the
  database file — a complete, restorable backup. Store it somewhere secure:
  it contains everything.
- On **PostgreSQL** the button is deliberately disabled. A valid backup has
  to be taken on the database server with `pg_dump`; the page shows the exact
  command. A browser download there would produce an incomplete file, which
  is more dangerous than no backup at all.

**Take backups on a schedule, and test that one restores.** An untested
backup is a guess.

### Keeping alerts fresh

Stock, expiry and payment alerts recalculate when someone opens the
Notifications page and when you press **Refresh**. To keep them current
overnight, have IT schedule this with Windows Task Scheduler:

```
python manage.py refresh_notifications
```

---

## 7. How profit is calculated (batch costing)

This matters whenever a medicine's cost changes between deliveries, so it's
worth understanding.

### The problem

Suppose you stock a medicine like this:

| | Quantity | Cost each | Sold at |
|---|---|---|---|
| First delivery | 40 | 20 ETB | 50 ETB |
| Second delivery | 100 | 30 ETB | 60 ETB |

If the system kept only *one* cost figure per medicine, the second delivery
would overwrite the first. Profit on units bought at 20 would then be
calculated at 30 — understating your profit, and quietly changing last
month's numbers.

### What PharmaCare does instead

Each delivery is stored as its own **batch**, with its own cost, and stock is
dispensed **first-expired-first-out (FEFO)** — the batch expiring soonest
goes first, which is the correct rule for medicines.

Continuing the example, if you now **sell 50 units**:

- 40 units come from the first batch at **20 ETB** = 800
- 10 units come from the second batch at **30 ETB** = 300
- **Recorded cost of goods = 1,100 ETB**

At the current price of 60 ETB, revenue (excluding VAT) is 3,000 ETB, so:

> **Gross profit = 3,000 − 1,100 = 1,900 ETB**

That figure is **fixed at the moment of sale**. Buy more stock next week at
45 ETB and this sale still reports 1,900 — history doesn't move.

### Where to see it

- **Inventory → Batches** — every batch, its cost, and what's left.
- **Reports → Profit** — revenue, true cost of goods, gross profit and
  margin per medicine.
- Open any sale to see its cost and profit; each line records exactly which
  batches it drew from.

### Two things to note

**VAT is excluded from profit.** VAT is collected on behalf of the tax
authority — it was never your margin, so including it would overstate
profit.

**Selling price changes are forward-only.** Setting **New Selling Price** on
a purchase changes what you charge from then on. Sales already made keep the
price they were actually sold at, because a past receipt must always match
what the customer paid.

**Stock that predates batch tracking** (or entered by typing a quantity onto
the medicine form) is turned into an *Opening* batch at the medicine's
recorded cost, so nothing is stranded. Those figures are only as good as the
cost that was on the record — for exact costing, bring stock in through
**Record Purchase**.

---

## 8. Working across branches

Each branch keeps **its own stock**. The product catalogue, customers and
suppliers are **shared** — one paracetamol record and one customer record,
wherever they shop.

| Shared across branches | Kept per branch |
|---|---|
| Products, categories, suppliers | Stock quantity and reorder level |
| Customers and loyalty points | Batches, and therefore cost |
| Settings and staff accounts | Sales, purchases, stock movements |
| | Notifications and invoice number prefix |

**Your branch is shown in the top bar** next to a shop icon. Administrators can
click it to switch; everyone else sees a fixed label, because their account is
tied to where they work and that is enforced by the system, not by hiding a
menu.

Consequences worth knowing:

- The till only offers stock **your** branch holds. A product missing from the
  search may simply be out of stock here while another branch has plenty.
- Reorder levels are per branch, so a busy branch can reorder earlier than a
  quiet one.
- Invoice prefixes can differ per branch (`BOL-000001`, `GON-000001`) so numbers
  are never confused.

**Transfers** (Store Manager) move stock between branches. Units arrive at the
cost they left at, carrying their expiry dates, so both branches' profit figures
stay correct and the receiving branch still dispenses soonest-expiry first.
There is no "in transit" state — record a transfer when the goods actually move.

## 9. The standard catalogue

Menu → **Standard Catalogue**.

Without it, four people typing names produce "Paracetamol 500mg", "paracetamol
500 mg", "PCM 500" and "Panadol 500mg" — four unrelated products no report can
add together. Registering from the catalogue gives every pharmacy the same
identity for the same medicine.

**The catalogue provides** the generic (INN) name, strength, dosage form, route,
ATC code, therapeutic category, legal class, and cold-chain and
essential-medicine flags.

**You provide** your own category, purchase and selling prices, opening
quantity, reorder level, expiry date and batch number.

Two rules the system enforces:

- The **legal class sets the prescription warning**, not the person registering
  — a prescription-only medicine cannot be registered as over the counter.
- The **same catalogue product cannot be registered twice**; you are told which
  product code already exists.

> **About the bundled data.** The entries shipped with the system are a starter
> set of common medicines, marked as such, and registration numbers are left
> blank on purpose. They are **not** an extract of the EFDA register. Before
> using this for regulatory reporting, an Administrator should load the
> authority's own list with `import_catalogue`.

The catalogue page shows how many of your products are **not standardised** —
those still work, but will not roll up in group or regulatory reporting.

> **This has been relaxed since the note above was first written.** Linking
> a medicine to the catalogue is no longer required, only strongly
> recommended — a pharmacy can legitimately stock genuine medicines that
> simply aren't on the ~600-item essential-medicines list. Adding one
> without a link still works; it's flagged with a **Not Standardised**
> badge on the medicine list and detail page as a reminder to link it
> later if it turns out to exist. Browsing the catalogue itself is a
> platform-staff-only screen now, not something any pharmacy account
> reaches directly — the badge on your own medicines is how you'd notice.

## 10. Stocktakes, the ledger and reorder planning

### Stocktakes (Store Manager)

Menu → **Stocktakes**. Start → count → review → post.

Starting a count **freezes the expected figures**, so sales made while you count
are not mistaken for counting errors. Counts save separately from posting, so a
count can span shifts. Print the count sheet and count against paper.

> **An empty count box means "not counted", never zero.** Anything you did not
> reach is left exactly as it was. The posting message tells you how many
> products were skipped.

Only one stocktake can be open per branch, and posting is final.

### The stock ledger

Menu → **Inventory → Manage → Stock Ledger**.

Every change to stock with a running balance and the document behind it —
purchases, sales, voids, transfers, corrections, stocktakes and opening
balances. Append-only: entries are never edited or deleted.

Use it when numbers are disputed. Filter by product for its whole history, or
by a reference such as `PUR-000007` to see everything one delivery did.

### Reorder plan (Store Manager)

Menu → **Reorder Plan**. A reorder level says *that* something is low; this says
*how much* to buy, from actual sales over the last 60 days. Grouped by supplier,
because that is how orders are placed.

**Days of cover under 7 is shown in red.** A dash means no recent sales, so
there is no rate to measure — treat those lines with more judgement.

### Stock aging

Menu → **Inventory → Manage → Stock Aging**. Stock grouped by remaining shelf
life and valued at **what each batch actually cost**. Read the value column, not
just the units: twenty expiring insulin vials matter more than two hundred
expiring paracetamol tablets.

## 11. Common tasks, step by step

### A customer wants to return an item

There's no "return" button by design. Either:

- **Whole sale was wrong** → ask an Administrator to **Void** it (stock and
  cost return correctly), then ring up the correct sale.
- **Part of a sale** → ring up the correct items and have a Store Manager
  record a **Stock In** movement for the returned units, with the invoice
  number in the reason.

### Stock count doesn't match the system

1. Recount.
2. Store Manager: **Inventory → Record Stock Movement → Stock Adjustment**.
3. Enter the **counted total** and explain the discrepancy in Reason.
4. The audit log records the before and after figures and your name.

### Medicine has expired

1. Remove it from the shelf.
2. Store Manager: **Stock Out** for that quantity, reason "expired write-off".
3. Check **Reports → Expired & Expiring** for anything else nearby.

### A price needs to change

- **Because a new delivery cost more** → put the new price in **New Selling
  Price** on the purchase line. Cleanest option: cost and price change
  together and stay linked.
- **Just a price change, no delivery** → Store Manager edits the medicine's
  **Selling Price**. Past sales are unaffected.

### Preparing a month-end pack

1. **Reports → Sales Summary**, set the month, group by **Monthly**.
2. **Reports → Profit** for the same range.
3. **Reports → Purchases** for supplier spend.
4. **Reports → Inventory** for closing stock value.
5. Export each to PDF or Excel.
6. **Review before sending.** Exports are drafts and note AI assistance.

### Someone has left the pharmacy

**Staff & Roles** → open them → untick **Active Employee** → Save. Don't
delete: their name stays attached to the sales and stock movements they made.

---

## 12. Troubleshooting

| Symptom | What's happening | What to do |
|---|---|---|
| "You do not have permission" / 403 | Your role can't reach that page — this is normal, not a fault | See [section 2](#2-what-your-role-can-do); ask someone with the right role |
| Locked out after wrong passwords | 5 failures locks the account and address for 30 minutes | Wait, or ask an Administrator (they can clear it) |
| Asked to change password at sign-in | New or admin-reset account | Set your own password; you can't skip this |
| A medicine won't appear in the till search | POS only lists **active** medicines with stock above zero | Check Inventory; it may be out of stock or deactivated |
| "Not enough stock" when selling | Physical stock is ahead of the system | Store Manager records **Stock In** or a **Stock Adjustment** |
| Phone number rejected on a new customer | That number is already registered | Open the existing customer named in the message |
| No **Export** buttons on reports | Exporting is Administrator / Store Manager only | Ask one of them |
| Amharic text looks wrong in an exported CSV | Excel guessed the encoding | Open with Excel's *Data → From Text* and pick UTF-8; the PDF and Excel exports are unaffected |
| Alerts look out of date | They refresh on demand | Press **Refresh** on Notifications, or ask IT to schedule the refresh task |
| Cost columns missing from a report | Your role isn't cleared for cost data | Expected; ask a Store Manager or Administrator |
| A product is missing from the till search | Your branch may hold none of it, even if another branch does | Ask a Store Manager to transfer stock in |
| Figures look wrong after switching branch | You may be reading another branch's numbers | Check the branch name in the top bar |
| "Already registered as MED-000xx" | That catalogue product is already in your stock | Edit the existing product instead |
| Stocktake posted but a product was unchanged | Its count box was left empty, so it was skipped | Expected. Count it and run another stocktake |
| Stock and ledger disagree | Should never happen — the ledger is written on every change | Report it to your Administrator; it is a real finding |

### Getting help

Note **what you were doing**, **what you expected**, **what happened**, and
**your role** — then contact your Administrator. For anything touching
patient safety (a dispensing error, expired stock reaching a customer),
follow the pharmacy's clinical incident procedure first; the software record
can be corrected afterwards.

---

*PharmaCare is an internal system. All output — reports, invoices, exports —
is a draft for human review. Check figures against the screen before
anything goes to a customer, supplier or regulator.*
