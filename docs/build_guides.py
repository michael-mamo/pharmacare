"""
Builds one detailed user guide per role, as HTML and PDF.

    python docs/build_guides.py

Output lands in docs/guides/. Each guide is self-contained: a person in that
role should never need to read another role's document, so the shared basics
(signing in, the screen, the language switch) are repeated in each rather
than cross-referenced.

Regenerate after changing anything a user sees. Requires Playwright's
Chromium for PDF rendering; if it isn't available the HTML is still written.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from guide_assets import (  # noqa: E402
    CSS, FONTS, svg_batch_costing, svg_branches, svg_catalogue, svg_dashboard,
    svg_inventory, svg_ledger, svg_pos, svg_product_types, svg_purchase_form,
    svg_roles_matrix, svg_screen_layout, svg_stocktake_flow, svg_transfer,
)

OUT = pathlib.Path(__file__).resolve().parent / "guides"
CURRENCY = "ETB"
#: The pharmacy's actual login address. Set this to wherever staff really
#: sign in — a real URL here is far less confusing than a made-up example,
#: and it means the same guide can be handed to a new hire without editing
#: it by hand. Update this when the deployment moves (new domain, self-hosted
#: box, etc.) and regenerate.
SITE_URL = "https://pharmacare-five-ebon.vercel.app/"


# ===========================================================================
# Shared sections
# ===========================================================================
def sec_signin(role_lands_on):
    return f"""
<h2 id="signin">Signing in and finding your way</h2>
<p class="lead">The same three steps every shift.</p>

<div class="card"><ol class="steps">
  <li><strong>Open {SITE_URL}</strong>
      <span>Bookmark it, or add it to your phone's home screen.</span></li>
  <li><strong>Type your username and password</strong>
      <span>Your username is personal — never share it or sign in as someone else. Everything
      you do is recorded against your name.</span></li>
  <li><strong>You land on {role_lands_on}</strong>
      <span>The system sends each role to the page they use most.</span></li>
</ol></div>

<div class="note"><strong>First sign-in, or after a password reset.</strong> You are asked to
create your own password before you can do anything else. This is deliberate — it means nobody
else knows it, including your manager. You need at least <strong>10 characters</strong> with a
capital letter, a small letter, a number and a symbol. Example of the right shape (do not use
this one): <code>Bole#Pharm24</code></div>

<div class="warn"><strong>Five wrong passwords locks you out for 30 minutes.</strong> This is a
safety measure against someone guessing their way in. Wait it out, or ask an Administrator to
clear it. Use <strong>Forgot your password?</strong> on the sign-in page if you truly cannot
remember it.</div>

{svg_screen_layout()}

<h3>The top bar, button by button</h3>
<table>
 <tr><th>Button</th><th>What it does</th></tr>
 <tr><td><span class="kbd">☰</span></td><td>On a phone or tablet, opens the menu. Tap outside it to close.</td></tr>
 <tr><td>🌐 Globe</td><td>Switches the whole system between <strong>English</strong> and
     <strong>አማርኛ</strong> — including printed receipts. Your choice is remembered.</td></tr>
 <tr><td>🌙 Moon</td><td>Dark mode, easier on the eyes in a dim dispensary.</td></tr>
 <tr><td>🔔 Bell</td><td>Your alerts. A red number means unread. Click one to jump to what it is about.</td></tr>
 <tr><td>Your name</td><td><strong>My Profile</strong> (change your details or language) and
     <strong>Logout</strong>. Always log out on a shared computer.</td></tr>
</table>

<div class="info"><strong>Working on a phone?</strong> Everything works on a small screen. The
menu hides behind ☰ and tables scroll sideways.</div>
"""


def sec_customers(can_delete, can_points):
    del_row = ("<li><strong>Deleting a customer</strong><span>Use the red bin icon. Prefer editing "
               "over deleting — deleting loses their purchase history.</span></li>"
               if can_delete else
               "<li><strong>You cannot delete customers</strong><span>Ask a Store Manager or "
               "Administrator if a record genuinely must go.</span></li>")
    points = ("<li><strong>Loyalty points</strong><span>You can adjust these by hand when "
              "correcting a mistake. Normally they are awarded automatically on each sale.</span></li>"
              if can_points else
              "<li><strong>Loyalty points</strong><span>The field is not shown to your role. Points "
              "are added automatically when a named customer buys something.</span></li>")
    return f"""
<h2 id="customers">Customers</h2>
<p class="lead">Menu → <strong>Customers</strong>. Registering someone lets them earn loyalty
points and gives you their purchase history.</p>

<div class="card">
<h4 style="margin-top:0">Registering a new customer</h4>
<ol class="steps">
  <li><strong>Customers → Add Customer</strong><span>Name and phone number are required; email
      and address are optional.</span></li>
  <li><strong>Save Customer</strong><span>They are immediately selectable at the till.</span></li>
</ol>
</div>

<div class="warn"><strong>One phone number, one customer.</strong> If the number is already
registered, the system refuses and <em>tells you which customer has it</em> — open that record
instead of creating a second one. Two records for the same person split their history and
loyalty points, which is painful to unpick later.<br><br>
Spacing does not matter: <code>0911 22 33 44</code> and <code>0911223344</code> are treated as
the same number.</div>

<div class="card"><ul class="steps">{points}{del_row}</ul></div>
"""


def sec_branches(can_switch):
    """Branch section. Text differs for staff fixed to one branch versus an
    Administrator who can move between them — telling a cashier about a
    switcher they will never see is just noise."""
    if can_switch:
        body = """
<div class="card"><ol class="steps">
  <li><strong>Your current branch is in the top bar</strong>
      <span>Next to a shop icon. Click it to switch.</span></li>
  <li><strong>Switching changes everything on screen</strong>
      <span>Stock, sales, reports and the dashboard all follow the branch you
      picked. Check it before reading any figure.</span></li>
  <li><strong>Use "Compare all branches" to see them side by side</strong>
      <span>In the same menu. This is where you spot a product sitting in one
      branch while another has run out.</span></li>
</ol></div>
<div class="warn"><strong>Always check which branch you are in before acting.</strong>
Recording a delivery or a stock correction against the wrong branch creates two
errors at once — a surplus in one and a shortage in the other.</div>"""
    else:
        body = """
<div class="card">
<p style="margin:0 0 10px">Your branch is shown in the top bar next to a shop
icon. You cannot change it, and that is deliberate — your account is tied to
where you work.</p>
<p style="margin:0"><strong>What this means day to day:</strong> the till only
offers stock your branch actually holds, and the sales you see are your
branch's. If a product is missing from the till search, your branch may have
none even though another branch does — ask a Store Manager about a transfer.</p>
</div>"""
    return f"""
<h2 id="branches">Working across branches</h2>
<p class="lead">Each branch keeps its own stock. The product list, customers and
suppliers are shared.</p>
{svg_branches()}
{body}
"""


def sec_language():
    return """
<h2 id="language">Working in Amharic</h2>
<p class="lead">Press the 🌐 globe in the top bar and choose <strong>አማርኛ</strong>.</p>
<div class="card">
<p style="margin:0 0 10px">Switching changes everything: menus, buttons, warning messages,
printed receipts and exported reports. Product names stay exactly as they were typed in, because
those are your own data, not part of the system's wording.</p>
<p class="mini" style="margin:0">Your choice sticks to your account, so a colleague on the same
computer can work in English while you work in Amharic.</p>
</div>
"""


def sec_troubleshoot(rows):
    body = "".join(f"<tr><td>{a}</td><td>{b}</td><td>{c}</td></tr>" for a, b, c in rows)
    return f"""
<h2 id="problems">When something goes wrong</h2>
<table>
 <tr><th style="width:30%">What you see</th><th style="width:32%">What it means</th><th>What to do</th></tr>
 {body}
</table>

<div class="warn"><strong>If a patient may have been harmed</strong> — the wrong item dispensed,
expired stock sold, a dosage mix-up — follow the pharmacy's clinical incident procedure
<strong>first</strong>. The computer record can be corrected afterwards; patient safety cannot
wait for paperwork.</div>

<h3>Reporting a problem usefully</h3>
<div class="card"><p style="margin:0">Tell your Administrator four things:
<strong>1)</strong> what you were doing, <strong>2)</strong> what you expected,
<strong>3)</strong> what actually happened (the exact wording of any message),
<strong>4)</strong> your role and username. That is usually enough to fix it without a
back-and-forth.</p></div>
"""


FOOTER = """
<div class="footer">
PharmaCare Management System · internal use only. Reports, invoices and exports are drafts for
human review — check them before anything goes to a customer, supplier or regulator.
</div>
"""


def shell(title, role, tagline, sections, toc):
    toc_html = "".join(f"<li>{t}</li>" for t in toc)
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>{FONTS}<style>{CSS}</style></head><body>
<div class="cover">
  <div class="mark">PC</div>
  <p class="kicker">PharmaCare · User Guide</p>
  <h1>{role}</h1>
  <p class="sub">{tagline}</p>
  <div class="meta">
    <div>Written for<strong>{role}s</strong></div>
    <div>Covers<strong>Every task in your role</strong></div>
    <div>Languages<strong>English / አማርኛ</strong></div>
  </div>
</div>
<div class="page">
<div class="toc"><strong>What's in this guide</strong><ol>{toc_html}</ol></div>
{sections}
{FOOTER}
</div></body></html>"""


# ===========================================================================
# CASHIER
# ===========================================================================
def guide_cashier():
    toc = ["Signing in and finding your way", "Working across branches",
           "Selling something — the till, step by step",
           "What you sell — more than medicines", "Prescription items",
           "Receipts, reprints and corrections", "Looking up a medicine's identity",
           "Customers", "Your alerts",
           "Working in Amharic", "What your role cannot do", "When something goes wrong"]
    s = sec_signin("the <strong>Point of Sale</strong> screen — your till")
    s += sec_branches(can_switch=False)
    s += f"""
<h2 id="till">Selling something — the till, step by step</h2>
<p class="lead">Menu → <strong>Point of Sale</strong>. Left side finds the item, right side takes
the money.</p>
{svg_pos()}

<div class="card"><ol class="steps">
  <li><strong>Put the cursor in the search box</strong>
      <span>It is already there when the page opens. If you clicked elsewhere, click the box again.</span></li>
  <li><strong>Add the item — two ways</strong>
      <span><strong>Scanner:</strong> point and shoot. The scanner types the barcode and presses
      Enter for you, and the item drops straight into the basket.<br>
      <strong>By hand:</strong> type part of the name, the code, or the generic name. Results
      appear as you type — click the row or its <em>Add</em> button.</span></li>
  <li><strong>Check what you added</strong>
      <span>Under each name you see the <strong>type</strong> (Medicine, Cosmetic, Medical
      Device…) and how many are <strong>available</strong>. A red <strong>Rx</strong> tag means a
      prescription is required — see the next section.</span></li>
  <li><strong>Set the quantity</strong>
      <span>Type over the <em>qty</em> box. If you try to go above what is in stock, the system
      tells you the real number and holds you there.</span></li>
  <li><strong>Add a discount if you were told to</strong>
      <span>The <em>disc %</em> box is per item, not for the whole basket. Leave it at 0 unless a
      manager has authorised a discount.</span></li>
  <li><strong>Remove a mistake</strong>
      <span>Press the <span class="kbd">✕</span> on that line, or <strong>Clear</strong> to empty
      the whole basket and start again.</span></li>
  <li><strong>Pick the customer</strong>
      <span>Leave it on <em>Walk-in customer</em> for someone not registered. Choosing a named
      customer earns them loyalty points automatically.</span></li>
  <li><strong>Choose how they are paying</strong>
      <span>Cash, Card, or Mobile Money.</span></li>
  <li><strong>Type what they handed you</strong>
      <span>Put the amount in <em>Paid</em>. The <strong>change due</strong> figure appears
      instantly — read it from the screen rather than doing the sum in your head.</span></li>
  <li><strong>Press Complete Sale</strong>
      <span>You get the invoice number and the change. Then choose
      <strong>View / Print Invoice</strong> to print the receipt, or <strong>New Sale</strong> to
      move to the next customer.</span></li>
</ol></div>

<div class="ok"><strong>You cannot accidentally oversell.</strong> The system checks the real
stock at the moment you press Complete Sale — even if a colleague sold the last packet a second
earlier on another till. If there is not enough, nothing is recorded and you are told how many
are actually left.</div>

<div class="ok"><strong>You cannot accidentally sell expired stock either.</strong> If every pack
of a product has passed its expiry date, Complete Sale is refused with a clear message — it is not
a warning you can click past. If you see this, remove the product from the shelf and tell a Store
Manager so it can be written off.</div>

<div class="note"><strong>Reading the totals.</strong> <em>Subtotal</em> is the plain price ×
quantity. <em>Discount</em> comes off next. <em>VAT</em> is added after the discount. The big
<strong>Total</strong> is what the customer pays.</div>

<h2 id="types">What you sell — more than medicines</h2>
<p class="lead">The counter sells tablets, but also creams, dressings and equipment. They are all
in the same list and behave the same way.</p>
{svg_product_types()}
<div class="info"><strong>Some things have no expiry date</strong> — a knee support or a
blood-pressure monitor, for example. You will see a dash where the date would be. That is normal
and not a fault.</div>

<h2 id="rx">Prescription items</h2>
<div class="card">
<p style="margin:0 0 12px">Some products carry a red <strong>Rx</strong> tag. When you add one to
the basket a message appears asking you to confirm you have seen a valid prescription.</p>
<ol class="steps">
  <li><strong>Read the message and stop</strong><span>Do not click it away by reflex.</span></li>
  <li><strong>Check the prescription in your hand</strong><span>Right patient, in date, signed.</span></li>
  <li><strong>If anything is unclear, call the Pharmacist</strong><span>Do not guess. This is
      exactly the moment to ask.</span></li>
</ol>
</div>
<div class="warn">The on-screen message is a reminder, not a legal check. The pharmacist is
responsible for the decision to dispense.</div>

<h2 id="receipts">Receipts, reprints and corrections</h2>
<div class="card">
<h4 style="margin-top:0">Reprinting a receipt</h4>
<ol class="steps">
  <li><strong>Menu → Sales</strong><span>Every sale, newest first.</span></li>
  <li><strong>Find it</strong><span>Search by invoice number (for example <code>INV-000042</code>)
      or by customer name.</span></li>
  <li><strong>Press the receipt icon, then Print</strong><span>Prints the same document as the
      original.</span></li>
</ol>
</div>
<div class="warn"><strong>You cannot cancel or change a completed sale.</strong> This is
deliberate — a sale is a money record. If something is wrong:
<ul style="margin:8px 0 0 18px">
  <li><strong>Whole sale wrong</strong> → ask an Administrator to <em>void</em> it. Stock goes
      back automatically. Then ring the correct sale.</li>
  <li><strong>One item wrong</strong> → ring up the correct items, and tell a Store Manager which
      items came back so they can put them into stock.</li>
</ul></div>

<h2 id="catalogue">Looking up a medicine's identity</h2>
<p class="lead">You don't browse a separate catalogue — use the same search box you already use at
the till, or <strong>Medicines</strong> in the sidebar.</p>
<div class="card">
<p style="margin:0 0 10px"><strong>What you can use it for.</strong> Checking whether a product
exists and what it actually is — its full name, strength, form, and whether it needs a
prescription. Useful when a customer asks for something by a brand name you do not recognise:
search the brand and the generic name behind it is shown alongside it.</p>
<p style="margin:0"><strong>What you cannot do.</strong> Registering a new product into stock
is a Store Manager job — and the shared standard catalogue behind it (ATC codes, legal
classes) is managed at the platform level, not by any one pharmacy.</p>
</div>

{sec_customers(can_delete=False, can_points=False)}

<h2 id="alerts">Your alerts</h2>
<div class="card">
<p style="margin:0 0 10px">The 🔔 bell shows messages meant for your role. Click one to jump
straight to what it refers to, or open <strong>Notifications</strong> for the full list.</p>
<p class="mini" style="margin:0">Alerts about stock levels and expiry are aimed at the Pharmacist
and Store Manager, so you will see fewer than they do. That is normal.</p>
</div>

{sec_language()}

<h2 id="cannot">What your role cannot do — and who to ask</h2>
{svg_roles_matrix()}
<table>
 <tr><th>You need to…</th><th>Ask a…</th></tr>
 <tr><td>Cancel or correct a completed sale</td><td><strong>Administrator</strong> (only they can void)</td></tr>
 <tr><td>Change a price, or add a new product</td><td>Store Manager or Administrator</td></tr>
 <tr><td>Check stock levels or expiry lists</td><td>Pharmacist, Store Manager or Administrator</td></tr>
 <tr><td>Delete a customer</td><td>Store Manager or Administrator</td></tr>
 <tr><td>See cost prices or profit</td><td>Not available to your role — this is business-confidential</td></tr>
 <tr><td>Save a report as PDF or Excel</td><td>Store Manager or Administrator</td></tr>
</table>
<div class="info">Being refused a page is not an error or a sign of distrust — the system simply
shows each role what their job needs.</div>
"""
    s += sec_troubleshoot([
        ("“You do not have permission”",
         "That page is not part of your role", "Normal. See the table above for who to ask"),
        ("Locked out after wrong passwords",
         "Safety lock for 30 minutes", "Wait, or ask an Administrator to clear it"),
        ("Asked to change password when signing in",
         "New account, or an Administrator reset it", "Create your own password — you cannot skip this"),
        ("“Not enough stock”",
         "The shelf has more than the system thinks", "Sell what the system allows, then ask a Store Manager to correct the count"),
        ("An item does not appear when searching",
         "It is out of stock, or switched off in the catalogue", "Ask a Pharmacist or Store Manager to check it"),
        ("Phone number rejected for a new customer",
         "That customer already exists", "Open the customer named in the message"),
        ("Red <strong>Rx</strong> tag on an item",
         "Prescription required", "Check the prescription; call the Pharmacist if unsure"),
        ("Barcode scanner does nothing",
         "The cursor is not in the search box", "Click the search box, then scan again"),
        ("Screen looks wrong or frozen",
         "Page needs reloading", "Press <span class='kbd'>F5</span>. Nothing in a saved sale is lost"),
    ])
    return shell("PharmaCare — Cashier Guide", "Cashier",
                 "Everything you need at the till: selling, receipts, customers and what to do "
                 "when something looks wrong.", s, toc)


# ===========================================================================
# PHARMACIST
# ===========================================================================
def guide_pharmacist():
    toc = ["Signing in and finding your way", "Working across branches",
           "Dispensing at the till",
           "Prescription-only items", "What you sell — more than medicines",
           "Where a medicine's details come from", "Checking stock before you dispense",
           "Expiry checks and what to do", "Understanding batches",
           "Tracing stock movements", "Stock aging and value at risk",
           "Suppliers", "Reports you can use",
           "Customers", "Working in Amharic", "What your role cannot do",
           "When something goes wrong"]
    s = sec_signin("the <strong>Point of Sale</strong> screen")
    s += sec_branches(can_switch=False)
    s += f"""
<h2 id="till">Dispensing at the till</h2>
<p class="lead">You have the same till as the Cashier. Menu → <strong>Point of Sale</strong>.</p>
{svg_pos()}
<div class="card"><ol class="steps">
  <li><strong>Scan or search</strong><span>Barcode, name, code, or generic name.</span></li>
  <li><strong>Check type, stock and any Rx tag</strong><span>Shown under each product name.</span></li>
  <li><strong>Set quantity and any authorised discount</strong><span>Stock is enforced — you
      cannot exceed it.</span></li>
  <li><strong>Choose customer and payment, enter cash taken</strong><span>Change due appears
      automatically.</span></li>
  <li><strong>Complete Sale, then print if needed</strong><span>Stock drops immediately.</span></li>
</ol></div>
<div class="ok"><strong>Oldest-expiry stock is dispensed first, automatically.</strong> You do not
have to pick batches by hand — selling normally always draws down the packs that expire soonest.
If every pack of a product has already expired, the sale is refused outright rather than let
through with a warning — remove it from the shelf and have a Store Manager write it off.</div>

<h2 id="rx">Prescription-only items</h2>
<div class="card">
<p style="margin:0 0 12px">Products marked <strong>Rx</strong> trigger a confirmation before they
enter the basket. As the Pharmacist, this is your professional check, not a formality.</p>
<ol class="steps">
  <li><strong>Verify the prescription</strong><span>Correct patient, in date, prescriber
      identifiable, dose and quantity legible.</span></li>
  <li><strong>Check the product against it</strong><span>Right medicine, right strength, right form.</span></li>
  <li><strong>Check the stock itself</strong><span>Intact packaging, and in date — see the expiry
      section below.</span></li>
  <li><strong>Counsel the patient</strong><span>Dose, timing, food, common side effects, what to do
      if a dose is missed.</span></li>
  <li><strong>Then confirm on screen</strong></li>
</ol>
</div>
<div class="warn">The system flags Rx items as a discipline aid. It cannot judge clinical
appropriateness, interactions or dose. That judgement stays with you.</div>

<h2 id="types">What you sell — more than medicines</h2>
{svg_product_types()}
<div class="info"><strong>Durable items have no expiry date</strong> (a brace, a monitor) and show
a dash instead. They are correctly excluded from expiry warnings. Anything swallowed or applied to
skin always carries an expiry date.</div>

<h2 id="catalogue">Where a medicine's details come from</h2>
<p class="lead">You don't browse a separate catalogue — the standard reference identity (generic
name, strength, form, legal class) is already copied onto each medicine's own detail page,
because it was locked in when a Store Manager or platform staff registered that stock.</p>
<div class="card">
<h4 style="margin-top:0">On a medicine's detail page</h4>
<ul style="margin:0 0 0 18px">
  <li><strong>Identifying a brand.</strong> The generic (INN) name is shown alongside the
      brand — the same identity everywhere it's sold, not this pharmacy's own wording.</li>
  <li><strong>Checking the legal class.</strong> Over the counter, prescription only, or
      controlled — and that classification, not anyone's opinion, is what sets the till
      warning.</li>
  <li><strong>Strength and form.</strong> Shown exactly as registered, so there's no
      ambiguity between, say, two different strengths of the same tablet.</li>
</ul>
</div>
<div class="note">The full standard catalogue itself (ATC codes, cold-chain flags, data
source) is a platform-level reference list, not something any one pharmacy's staff browse
directly — if something about a medicine's identity looks wrong, flag it to your Store
Manager or Administrator.</div>

<h2 id="stock">Checking stock before you dispense</h2>
<p class="lead">Menu → <strong>Inventory</strong>. This is your stock picture for the whole shop.</p>
{svg_inventory()}
<div class="card"><ol class="steps">
  <li><strong>Search by name or code</strong><span>Fastest way to answer “do we have any?”</span></li>
  <li><strong>Filter by status</strong><span><em>Low stock</em>, <em>Out of stock</em> or
      <em>Expired</em>.</span></li>
  <li><strong>Use the four cards at the top as shortcuts</strong><span>Each one opens the matching
      list. They are buttons, not just numbers.</span></li>
  <li><strong>Read the status column</strong><span><span class="tick">OK</span>,
      <strong>LOW</strong> (at or below reorder level) or <strong>OUT</strong>. An expiry warning
      appears alongside.</span></li>
</ol></div>
<div class="note">You can see quantities, reorder levels and expiry dates, but not cost prices —
those are restricted to Administrators and Store Managers.</div>

<h2 id="expiry">Expiry checks and what to do</h2>
<p class="lead">Menu → <strong>Inventory</strong> → the <strong>Expired</strong> card, or
Inventory → Expired.</p>
<table>
 <tr><th>Tab</th><th>Meaning</th><th>Action</th></tr>
 <tr><td><strong>Expired</strong></td><td>Already past its date</td>
     <td class="non">Do not dispense. Remove from the shelf now and quarantine it</td></tr>
 <tr><td><strong>Within 30 days</strong></td><td>Expiring very soon</td>
     <td>Dispense these first; consider a supplier return</td></tr>
 <tr><td><strong>Within 60 days</strong></td><td>On the horizon</td>
     <td>Watch it; avoid reordering more until it moves</td></tr>
</table>
<div class="card">
<h4 style="margin-top:0">If you find expired stock on the shelf</h4>
<ol class="steps">
  <li><strong>Remove it immediately</strong><span>Before anything else. Put it in the quarantine
      area, not back on the shelf.</span></li>
  <li><strong>Tell the Store Manager</strong><span>They record a <em>Stock Out</em> with the reason
      “expired write-off” so the system count matches the shelf.</span></li>
  <li><strong>Check the rest of that product</strong><span>Other packs may be from the same batch —
      use Inventory → Batches.</span></li>
  <li><strong>If any may have reached a patient</strong><span>Follow the clinical incident
      procedure straight away.</span></li>
</ol>
</div>

<h2 id="batches">Understanding batches</h2>
<p class="lead">Menu → <strong>Inventory</strong> → <strong>Batches</strong>.</p>
{svg_batch_costing()}
<div class="note">You will not see the cost columns shown above — those are restricted — but the
batch list and the soonest-expiry-first order are visible to you, which is what matters clinically.</div>
<div class="card">
<p style="margin:0 0 10px">Each delivery of a product is stored separately, with its own expiry
date and its own remaining quantity. This is why the system can dispense soonest-expiry first,
and why you can trace which delivery a pack came from.</p>
<p style="margin:0"><strong>Useful for:</strong> a recall (which batch, how many left, where it
came from), an expiry sweep, or checking whether a product has newer stock behind the older packs.</p>
<p class="mini" style="margin:10px 0 0">Cost columns are not shown to your role.</p>
</div>

<h2 id="ledger">Tracing stock movements</h2>
<p class="lead">Menu → <strong>Inventory</strong> → <strong>Manage</strong> →
<strong>Stock Ledger</strong>.</p>
{svg_ledger()}
<div class="card">
<p style="margin:0 0 10px">Every change to stock appears here with a running
balance — purchases, sales, voids, transfers, corrections and stocktakes. It is
append-only: entries are never edited or deleted.</p>
<p style="margin:0"><strong>When you will reach for it:</strong> a count looks
wrong and you need to know what happened; a recall means tracing where a batch
went; or a colleague asks why stock dropped overnight. Filter by product name or
by a reference such as an invoice number.</p>
</div>

<h2 id="aging">Stock aging and value at risk</h2>
<p class="lead">Menu → <strong>Inventory</strong> → <strong>Manage</strong> →
<strong>Stock Aging</strong>.</p>
<div class="card">
<p style="margin:0 0 10px">Groups everything on hand by how long it has left:
expired, 0–30 days, 31–90, 91–180, over 180, and items with no expiry at all.</p>
<p style="margin:0">Use the 0–30 day bucket as your weekly action list: those are
the packs to dispense first and to flag to the Store Manager for a possible
supplier return. Value figures are hidden from your role; the counts are not.</p>
</div>

<h2 id="suppliers">Suppliers</h2>
<div class="card"><p style="margin:0">Menu → <strong>Suppliers</strong>. You can <strong>view</strong>
supplier records — contact person, phone, email, and how many products they supply — which is what
you need to chase a delivery or ask about a shortage. Adding and editing suppliers is a Store
Manager task.</p></div>

<h2 id="reports">Reports you can use</h2>
<p class="lead">Menu → <strong>Reports</strong>. You will see seven; the two financial ones are not
available to your role.</p>
<table>
 <tr><th>Report</th><th>What you would use it for</th></tr>
 <tr><td>Sales</td><td>Every sale in a date range — checking what went out on a given day</td></tr>
 <tr><td>Sales Summary</td><td>Daily / weekly / monthly / yearly totals</td></tr>
 <tr><td>Inventory</td><td>Full stock position, printable for a shelf check</td></tr>
 <tr><td>Low Stock</td><td>What needs reordering — hand this to the Store Manager</td></tr>
 <tr><td>Expired &amp; Expiring</td><td>Your expiry sweep list, with 30- and 60-day horizons</td></tr>
 <tr><td>Supplier</td><td>Who supplies what</td></tr>
 <tr><td>Customer</td><td>Purchase history and loyalty points</td></tr>
</table>
<div class="card"><ol class="steps">
  <li><strong>Pick the report, then set the dates</strong><span>Most default to the current month.</span></li>
  <li><strong>Press Apply</strong><span>Totals appear in the yellow boxes above the table.</span></li>
  <li><strong>Press Print for a paper copy</strong><span>Saving as PDF or Excel is limited to Store
      Managers and Administrators — ask if you need a file to send.</span></li>
</ol></div>

{sec_customers(can_delete=False, can_points=False)}
{sec_language()}

<h2 id="cannot">What your role cannot do</h2>
<table>
 <tr><th>Task</th><th>Who does it</th></tr>
 <tr><td>Add or edit a product, price or category</td><td>Store Manager / Administrator</td></tr>
 <tr><td>Record a delivery (purchase)</td><td>Store Manager / Administrator</td></tr>
 <tr><td>Correct a stock count / write off expired stock</td><td>Store Manager / Administrator</td></tr>
 <tr><td>See cost prices, purchase records or profit</td><td>Store Manager / Administrator</td></tr>
 <tr><td>Void a sale</td><td>Administrator only</td></tr>
 <tr><td>Export reports to PDF / Excel</td><td>Store Manager / Administrator</td></tr>
</table>
"""
    s += sec_troubleshoot([
        ("“You do not have permission”", "That page belongs to another role",
         "Normal. See the table above"),
        ("“Not enough stock” when you can see the packs",
         "System count is behind the shelf",
         "Ask a Store Manager for a Stock Adjustment; do not force the sale"),
        ("An expired item won't go through at the till",
         "Correct behaviour — every pack of it has expired",
         "Remove it from the shelf; ask a Store Manager to write it off. It cannot be sold, not even by mistake"),
        ("A device shows no expiry date", "It does not expire",
         "Correct behaviour — nothing to do"),
        ("Locked out after wrong passwords", "Safety lock, 30 minutes",
         "Wait, or ask an Administrator"),
        ("No Export buttons on a report", "Exporting is restricted",
         "Ask a Store Manager or Administrator"),
        ("Cost columns missing", "Your role is not cleared for cost data",
         "Expected. Ask a Store Manager if you need a figure"),
        ("Phone number rejected for a new customer", "That customer already exists",
         "Open the record named in the message"),
    ])
    return shell("PharmaCare — Pharmacist Guide", "Pharmacist",
                 "Dispensing, prescription checks, stock and expiry — plus the reports and "
                 "batch information you need on shift.", s, toc)


# ===========================================================================
# STORE MANAGER
# ===========================================================================
def guide_store_manager():
    toc = ["Signing in and finding your way", "Working across branches",
           "Receiving a delivery (purchases)",
           "How batch costing protects your profit figures",
           "Managing your own products, categories and suppliers",
           "Product types, including cosmetics and devices",
           "Shelf labels and barcodes", "Inventory and stock corrections",
           "Running a stocktake", "Planning what to reorder",
           "Tracing stock with the ledger", "Stock aging and value at risk",
           "Moving stock between branches",
           "Expiry management", "Reports and exports", "Customers",
           "Your alerts", "Working in Amharic", "What your role cannot do",
           "When something goes wrong"]
    s = sec_signin("the <strong>Inventory</strong> screen — your stock picture")
    s += sec_branches(can_switch=False)
    s += f"""
<h2 id="purchases">Receiving a delivery (purchases)</h2>
<p class="lead">This is the most important thing you do in the system. Menu →
<strong>Purchases</strong> → <strong>Record Purchase</strong>.</p>
{svg_purchase_form()}
<div class="card"><ol class="steps">
  <li><strong>Choose the Supplier and Purchase Date</strong><span>Take both from the delivery note,
      not from today's date, if the goods arrived earlier.</span></li>
  <li><strong>Fill in the first line item</strong><span>The form opens with exactly one row.
      Product (type to search), <em>Quantity</em> received, and <em>Cost each</em> — the unit cost
      <strong>for this delivery</strong>.</span></li>
  <li><strong>Only if the customer price is changing, fill New Selling Price</strong>
      <span>The yellow box. Leave it empty to keep the current price. This changes the price from
      now on; sales already made keep the price they were sold at.</span></li>
  <li><strong>Enter Discount % and VAT % from the supplier invoice</strong><span>These affect what
      you paid, not what you charge.</span></li>
  <li><strong>Press + Add Item for each additional product</strong><span>Add as many rows as the
      delivery note needs — there is no limit. The <strong>Invoice Total</strong> updates as you
      type, so you can check it against the supplier's figure before saving.</span></li>
  <li><strong>Remove a row you added by mistake</strong><span>Press the ✕ on that row.</span></li>
  <li><strong>Save Purchase &amp; Update Stock</strong><span>Stock goes up immediately, and this
      delivery is stored as its own costed batch.</span></li>
</ol></div>

<div class="warn"><strong>Check carefully before saving — purchases cannot be edited.</strong>
A purchase is a financial record; letting people quietly edit one would rewrite history. If you
make a mistake, an Administrator must delete it (which reverses the stock) and you record it
again.</div>

<div class="ok"><strong>Match the invoice total on screen against the supplier's invoice before you
save.</strong> Thirty seconds here saves an Administrator having to unpick it later.</div>

<h2 id="costing">How batch costing protects your profit figures</h2>
<p class="lead">Worth understanding, because it is the reason your profit reports can be trusted.</p>
{svg_batch_costing()}
<div class="card">
<h4 style="margin-top:0">What this means in practice</h4>
<ul style="margin:0 0 0 18px">
  <li><strong>Each delivery keeps its own cost, permanently.</strong> Buying at a higher price
      never rewrites the profit on sales you already made.</li>
  <li><strong>Soonest-expiry stock is sold first (FEFO).</strong> Not oldest-purchased —
      soonest-expiring, which is the right rule for a pharmacy.</li>
  <li><strong>VAT is excluded from profit.</strong> It is collected for the tax authority and was
      never your margin.</li>
  <li><strong>A sale can span two batches.</strong> Selling 50 when only 40 old units remain draws
      40 at the old cost and 10 at the new one, and records both.</li>
</ul>
</div>
<div class="note"><strong>See it yourself:</strong> Menu → <strong>Inventory</strong> →
<strong>Batches</strong> shows every delivery, its unit cost, expiry date and how much is left, in
the order it will be dispensed.</div>
<div class="info"><strong>One limitation worth knowing.</strong> If you add stock through
<em>Stock In</em> or a <em>Stock Adjustment</em> rather than a purchase, there is no supplier
invoice to cost it against, so those units take the product's current headline cost. For exact
costing, always bring goods in through <strong>Record Purchase</strong>.</div>

<h2 id="ownproducts">Managing your own products, categories and suppliers</h2>
<h3>Adding a product</h3>
<div class="warn"><strong>Link medicines to the standard catalogue whenever you can — it's strongly
recommended, not required.</strong> If Product Type is <em>Medicine</em>, the <strong>Catalogue
Product</strong> field near the top of this form is where you search it out — by generic name,
brand or ATC code. Once picked, the Name and Generic Name below are taken from the catalogue and
can't be typed over — that's deliberate, it's what stops "Paracetamol", "paracetamol 500mg" and
"PCM 500" becoming three unrelated products, and lets group reporting add the same medicine
together across pharmacies. If the catalogue genuinely doesn't have what you need, you can leave
it blank and type the name yourself — the form still saves it, just flagged with a
<strong>Not Standardised</strong> badge on the list and detail page as a reminder to link it
later if it turns out to exist. Every <strong>other</strong> product type — Cosmetic, Medical
Supply, Supplement, Baby &amp; Mother Care, Medical Device, Other — was never subject to this at
all; a perfume, a bandage or a blood-pressure monitor is typed in below exactly as before.</div>
<div class="card"><ol class="steps">
  <li><strong>Menu → Medicines → Add Medicine</strong><span>The same form covers every product
      type, not just medicines.</span></li>
  <li><strong>Set the Product Type first</strong><span>It decides whether a catalogue link is
      required and whether an expiry date is required — see below.</span></li>
  <li><strong>Medicine only: pick the Catalogue Product</strong><span>Search by generic name,
      brand or ATC code. Only entries you haven't already registered are offered.</span></li>
  <li><strong>Name, generic name, brand</strong><span>For a non-medicine type, use the name staff
      will actually search for — consistency matters more than perfection. For a medicine, these
      are filled in for you from the catalogue link.</span></li>
  <li><strong>Category and Supplier</strong><span>Both are searchable dropdowns — start typing.</span></li>
  <li><strong>Barcode</strong><span>If the pack has one, enter it. This is what makes scanning at
      the till work.</span></li>
  <li><strong>Batch number, manufacturing and expiry dates</strong><span>Expiry is required for
      anything consumable.</span></li>
  <li><strong>Prices</strong><span><em>Purchase Price</em> is the current headline cost (a reference
      figure — real costing comes from batches). <em>Selling Price</em> is what customers pay.
      <em>Tax</em> and <em>Discount</em> pre-fill the till.</span></li>
  <li><strong>Quantity and Reorder Level</strong><span>Set the reorder level to the point where you
      would want to order more — not zero, or the warning arrives too late.</span></li>
  <li><strong>Unit</strong><span>Tablet, Bottle, Pack, Roll, Pair, Jar and others — pick what you
      actually sell it by.</span></li>
  <li><strong>Requires Prescription</strong><span>For a medicine this comes from the catalogue's
      legal class and can't be changed here. For other types, tick it if it genuinely needs one.</span></li>
  <li><strong>Save Medicine</strong><span>A code like <code>MED-000042</code> is generated
      automatically.</span></li>
</ol></div>
<div class="note"><strong>Prefer editing over deleting.</strong> Untick <em>Active</em> to retire a
product; its sales history stays intact. Deleting is blocked anyway once a product has been sold.</div>

<h3>Categories</h3>
<div class="card"><p style="margin:0">Menu → <strong>Medicines</strong> →
<strong>Categories</strong>. Keep them broad enough to be useful — a category with one product in it
helps nobody. A category cannot be deleted while products are still assigned to it; move them
first.</p></div>

<h3>Suppliers</h3>
<div class="card"><p style="margin:0">Menu → <strong>Suppliers</strong>. Record the contact person
and phone — this is what someone reaches for when a delivery is late. Set <em>Status</em> to
Inactive rather than deleting a supplier you have stopped using, so purchase history stays
readable.</p></div>

<h2 id="types">Product types, including cosmetics and devices</h2>
{svg_product_types()}
<table>
 <tr><th>Type</th><th>Examples</th><th>Expiry date</th></tr>
 <tr><td>Medicine</td><td>Tablets, capsules, syrups</td><td class="non">Required</td></tr>
 <tr><td>Cosmetic / Personal Care</td><td>Creams, lotions, soaps</td><td class="non">Required</td></tr>
 <tr><td>Medical Supply</td><td>Bandages, gauze, plasters, syringes</td><td class="non">Required</td></tr>
 <tr><td>Supplement / Vitamin</td><td>Vitamin C, multivitamins</td><td class="non">Required</td></tr>
 <tr><td>Baby &amp; Mother Care</td><td>Nappies, formula</td><td class="non">Required</td></tr>
 <tr><td>Medical Device / Support</td><td>Knee braces, BP monitors, crutches</td><td class="yes">Optional</td></tr>
 <tr><td>Other</td><td>Anything that fits nowhere else</td><td class="yes">Optional</td></tr>
</table>
<div class="info">If you leave the expiry date blank on a type that needs one, the form stops you
and explains why. Items saved without an expiry are correctly left out of all expiry warnings.</div>

<h2 id="labels">Shelf labels and barcodes</h2>
<div class="card"><ol class="steps">
  <li><strong>Open the product, press Print Label</strong><span>Menu → Medicines → the product →
      <em>Print Label</em>.</span></li>
  <li><strong>Check the label before printing a batch of them</strong><span>It carries a scannable
      barcode, a QR code, the price and the expiry date.</span></li>
  <li><strong>If a product has no barcode of its own</strong><span>The label uses the generated
      product code, so scanning still works at the till.</span></li>
</ol></div>

<h2 id="inventory">Inventory and stock corrections</h2>
{svg_inventory()}
<h3>Recording a stock movement</h3>
<p class="lead">Menu → <strong>Inventory</strong> → <strong>Record Stock Movement</strong>. Use this
for anything that is not a purchase or a sale.</p>
<table>
 <tr><th>Type</th><th>Use it for</th><th>What to type in Quantity</th></tr>
 <tr><td><strong>Stock In</strong></td><td>Found stock, a donation, a sample, a customer return</td>
     <td>How many to <strong>add</strong></td></tr>
 <tr><td><strong>Stock Out</strong></td><td>Breakage, spillage, internal use, expired write-off</td>
     <td>How many to <strong>remove</strong></td></tr>
 <tr><td><strong>Stock Adjustment</strong></td><td>After a physical count</td>
     <td class="non">The <strong>new counted total</strong> — not the difference</td></tr>
 <tr><td><strong>Stock Transfer</strong></td><td>Stock going to another branch</td>
     <td>How many are leaving (a <strong>Destination</strong> is required)</td></tr>
</table>
<div class="warn"><strong>Stock Adjustment is an absolute figure.</strong> If the system says 100
and you counted 94, type <strong>94</strong> — not 6. Getting this backwards is the most common
mistake in this screen. A count of <strong>0</strong> is allowed and writes the product off
entirely — useful when a whole batch turned out to be expired or damaged and Stock Out feels like
the wrong tool because you're recording a recount, not a removal.</div>
<div class="note"><strong>Always fill in Reason.</strong> The whole value of the movement log is
that someone — possibly you, in three months — can understand what happened and why. "Correction"
is not a reason; "counted 94 during monthly stocktake, 6 unaccounted" is.</div>

<h3>Doing a stocktake</h3>
<div class="card"><ol class="steps">
  <li><strong>Print the Inventory report</strong><span>Reports → Inventory → Print. Count against
      paper, not against the screen.</span></li>
  <li><strong>Count a section at a time</strong><span>Note the actual figure beside each line.</span></li>
  <li><strong>Record one Stock Adjustment per discrepancy</strong><span>Entering the counted total,
      with the reason.</span></li>
  <li><strong>Investigate anything large</strong><span>A big gap is more likely a process problem
      than a counting error — check recent sales and deliveries for that product.</span></li>
</ol></div>

<h2 id="stocktake">Running a stocktake</h2>
<p class="lead">Menu → <strong>Stocktakes</strong>. This replaces correcting
products one at a time.</p>
{svg_stocktake_flow()}
<div class="card"><ol class="steps">
  <li><strong>Start the count</strong>
      <span>Pick a category to count one section, or leave it blank for the whole
      branch. Add a note such as "month-end, aisles 1–4". Starting the count
      freezes the expected figures, so sales made while you count are not
      mistaken for counting errors.</span></li>
  <li><strong>Print the count sheet</strong>
      <span>Press <em>Count Sheet</em> and count against paper, not a screen.</span></li>
  <li><strong>Type in what you counted</strong>
      <span>Press <em>Save Counts</em> as often as you like — a count can span
      shifts without losing work. Only one stocktake can be open per branch.</span></li>
  <li><strong>Review the differences</strong>
      <span>Use the <em>Differences only</em> tab. Investigate anything large
      before posting: a big gap is usually a process problem, not a miscount.
      Add a note against a line to explain it.</span></li>
  <li><strong>Post it</strong>
      <span>Differences are applied to stock in one go and written to the ledger
      with the stocktake reference.</span></li>
</ol></div>
<div class="warn"><strong>An empty count box means "not counted" — never zero.</strong>
Anything you did not reach is left exactly as it was when you post. This is
deliberate: treating blanks as zero would wipe out stock nobody got round to
counting. The posting message tells you how many products were skipped.</div>
<div class="note">Posting is final. A posted stocktake cannot be posted again or
edited. If you need to correct something afterwards, use a normal Stock
Adjustment, or run another count.</div>

<h2 id="reorder">Planning what to reorder</h2>
<p class="lead">Menu → <strong>Reorder Plan</strong>.</p>
<div class="card">
<p style="margin:0 0 10px">A reorder level tells you <em>that</em> something is
low. This tells you <em>how much</em> to buy. It measures units actually sold
per day over the last 60 days, works out how many days of stock you have left,
and suggests a quantity that restores a target number of days — adjustable at
the top of the page.</p>
<p style="margin:0"><strong>It is grouped by supplier</strong>, because you place
an order with a supplier, not with a spreadsheet.</p>
</div>
<table>
 <tr><th>Column</th><th>What it means</th></tr>
 <tr><td><strong>On Hand</strong></td><td>Stock at this branch now</td></tr>
 <tr><td><strong>Sold / Day</strong></td><td>Average daily sales over the window</td></tr>
 <tr><td><strong>Days of Cover</strong></td><td>How long current stock lasts at that rate. Under 7 days is shown in red</td></tr>
 <tr><td><strong>Suggested Order</strong></td><td>Quantity to restore your target days of cover</td></tr>
</table>
<div class="note"><strong>A dash in Days of Cover</strong> means the product had
no sales in the window, so there is no rate to measure. The suggestion falls
back to topping up to twice the reorder level. Treat those lines with more
judgement than the rest — the system is guessing where you are not.</div>
<div class="card"><p style="margin:0">The plan is advice, not an order. When the
goods arrive, record them through <strong>Purchases</strong> so cost and batch
tracking stay accurate.</p></div>

<h2 id="ledger">Tracing stock with the ledger</h2>
<p class="lead">Menu → <strong>Inventory</strong> → <strong>Manage</strong> →
<strong>Stock Ledger</strong>.</p>
{svg_ledger()}
<div class="card">
<p style="margin:0 0 10px">Every stock change with a running balance and the
document behind it. Nothing can change stock without appearing here, and
entries are never edited or deleted.</p>
<p style="margin:0"><strong>Use it when the numbers argue.</strong> Filter by
product to see its whole history, or by a reference such as
<code>PUR-000007</code> to see everything one delivery did. If the ledger and
the shelf disagree, the shelf is right — run a stocktake.</p>
</div>

<h2 id="aging">Stock aging and value at risk</h2>
<p class="lead">Menu → <strong>Inventory</strong> → <strong>Manage</strong> →
<strong>Stock Aging</strong>.</p>
<div class="card">
<p style="margin:0 0 10px">Stock grouped by remaining shelf life and valued at
<strong>what each batch actually cost</strong> — not the product's headline
price. That distinction matters: it shows the money genuinely at risk.</p>
<p style="margin:0"><strong>Read the value column, not just the units.</strong>
Twenty expiring insulin vials are a far bigger problem than two hundred
expiring paracetamol tablets, and only the value column tells you that.</p>
</div>

<h2 id="transfers">Moving stock between branches</h2>
<p class="lead">Menu → <strong>Branch Stock</strong> → <strong>Transfer Stock</strong>.</p>
{svg_transfer()}
<div class="card"><ol class="steps">
  <li><strong>Pick the product</strong>
      <span>Only products your branch actually holds are offered.</span></li>
  <li><strong>Pick the destination branch</strong>
      <span>Your own branch is not in the list.</span></li>
  <li><strong>Enter the quantity and a reason</strong>
      <span>You cannot send more than you have; the form tells you the real
      figure.</span></li>
  <li><strong>Transfer</strong>
      <span>Stock leaves your branch and arrives at the other one immediately,
      and both sides are written to the ledger.</span></li>
</ol></div>
<div class="note"><strong>Cost and expiry travel with the goods.</strong> Units
arrive at the destination at the cost they left at, with their original expiry
dates, so both branches' profit figures stay correct and the receiving branch
still dispenses soonest-expiry first.</div>
<div class="warn"><strong>The transfer is instant in the system.</strong> There
is no "in transit" state, so only record it when the goods actually move. If
they will spend days on a vehicle, record the transfer at the point they arrive,
or the receiving branch will appear to hold stock it cannot yet sell.</div>

<h2 id="expiry">Expiry management</h2>
<div class="card"><ol class="steps">
  <li><strong>Check weekly</strong><span>Inventory → Expired card, or Reports → Expired &amp;
      Expiring. Use the <em>Within 30 days</em> tab to act early.</span></li>
  <li><strong>Move soon-to-expire stock to the front</strong><span>The system already dispenses
      soonest-expiry first, but a physical reshuffle helps staff too.</span></li>
  <li><strong>Talk to the supplier while a return is still possible</strong><span>Most returns need
      notice well before the expiry date.</span></li>
  <li><strong>Write off what has expired</strong><span>Stock Out, reason "expired write-off". The
      Value at Risk column in the report tells you what it cost you.</span></li>
</ol></div>

<h2 id="reports">Reports and exports</h2>
<p class="lead">Menu → <strong>Reports</strong>. You have all nine, and you can export.</p>
<table>
 <tr><th>Report</th><th>Use it for</th></tr>
 <tr><td>Sales / Sales Summary</td><td>What sold, and revenue by day, week, month or year</td></tr>
 <tr><td><strong>Purchase</strong></td><td>Supplier spend in a period — reconciling invoices</td></tr>
 <tr><td><strong>Profit</strong></td><td>Revenue vs true batch cost, and margin per product</td></tr>
 <tr><td>Inventory</td><td>Full stock position and stock value</td></tr>
 <tr><td>Low Stock</td><td>Your reorder list</td></tr>
 <tr><td>Expired &amp; Expiring</td><td>Write-offs and value at risk</td></tr>
 <tr><td>Supplier</td><td>Spend and product count per supplier</td></tr>
 <tr><td>Customer</td><td>Spend and loyalty points</td></tr>
</table>
<div class="card"><ol class="steps">
  <li><strong>Set the date range, press Apply</strong></li>
  <li><strong>Read the yellow summary boxes first</strong><span>They carry the totals; the table is
      the detail behind them.</span></li>
  <li><strong>Export via the Export button</strong><span><strong>PDF</strong> to send or file,
      <strong>Excel</strong> to do your own sums (numbers arrive as numbers, so they add up),
      <strong>CSV</strong> for another system.</span></li>
</ol></div>
<div class="warn"><strong>Exports leave the system.</strong> They carry a footer noting AI-assisted
output. Review any figure before it goes to a supplier or an auditor — it is a draft until a
human has checked it.</div>

<h3>A month-end routine that works</h3>
<div class="card"><ol class="steps">
  <li><strong>Sales Summary</strong><span>Set the month, group by Monthly.</span></li>
  <li><strong>Profit</strong><span>Same range — check the margin looks sane against last month.</span></li>
  <li><strong>Purchase</strong><span>Reconcile against supplier statements.</span></li>
  <li><strong>Inventory</strong><span>Closing stock value.</span></li>
  <li><strong>Expired &amp; Expiring</strong><span>Write-offs, and what is at risk next month.</span></li>
  <li><strong>Export each to PDF, review, then send</strong></li>
</ol></div>

{sec_customers(can_delete=True, can_points=True)}

<h2 id="alerts">Your alerts</h2>
<div class="card"><p style="margin:0 0 8px">The 🔔 bell carries the alerts that matter to your job:
</p>
<ul style="margin:0 0 0 18px">
  <li><strong>Low stock / out of stock</strong> — your reorder prompt</li>
  <li><strong>Expired and expiring</strong> — your write-off and return prompt</li>
  <li><strong>New purchase recorded</strong> — confirmation stock went up</li>
  <li><strong>Large sale</strong> — unusually big transactions, worth a glance</li>
  <li><strong>Pending payment</strong> — a customer paid less than the invoice total</li>
</ul>
<p class="mini" style="margin:10px 0 0">Stock and expiry alerts clear themselves once you fix the
underlying situation — you do not have to tidy them up.</p></div>

{sec_language()}

<h2 id="cannot">What your role cannot do</h2>
<table>
 <tr><th>Task</th><th>Why / who</th></tr>
 <tr><td>Use the till</td><td>Deliberate. Your job is stock and purchasing; the counter is the
     Cashier's and Pharmacist's. Ask them to ring a sale</td></tr>
 <tr><td>Delete a purchase</td><td>Administrator only — it reverses stock and money records</td></tr>
 <tr><td>Void a sale</td><td>Administrator only</td></tr>
 <tr><td>View the audit log</td><td>Administrator only</td></tr>
 <tr><td>Change Settings or manage staff</td><td>Administrator only</td></tr>
</table>
"""
    s += sec_troubleshoot([
        ("Purchase form will not save", "A required field is empty or invalid",
         "Look for the red text under a field. Every line needs product, quantity and cost"),
        ("Saved a purchase with the wrong figures", "Purchases cannot be edited",
         "Ask an Administrator to delete it (stock reverses), then record it again"),
        ("Stock count is wrong after a delivery", "Purchase recorded twice, or not at all",
         "Check Purchases for a duplicate; then correct with a Stock Adjustment"),
        ("“This category cannot be deleted”", "Products are still assigned to it",
         "Move those products to another category first"),
        ("Cannot open the till", "Not part of your role, by design",
         "Ask a Cashier or Pharmacist"),
        ("Profit looks lower than expected", "VAT is excluded, and true batch cost is used",
         "Check Reports → Profit for the per-product breakdown"),
        ("Expiry date field refuses to stay blank", "That product type must have an expiry",
         "Set the type to Medical Device or Other if it genuinely does not expire"),
        ("Locked out after wrong passwords", "Safety lock, 30 minutes",
         "Wait, or ask an Administrator"),
    ])
    return shell("PharmaCare — Store Manager Guide", "Store Manager",
                 "Purchasing, stock control, the catalogue and the reports that tell you whether "
                 "the pharmacy is making money.", s, toc)


# ===========================================================================
# ADMINISTRATOR
# ===========================================================================
def guide_admin():
    toc = ["Signing in and finding your way", "First-time setup checklist",
           "The Dashboard and what each chart tells you",
           "Managing branches", "Managing staff and roles",
           "The standard catalogue",
           "Voiding a sale", "Deleting a purchase",
           "The audit log", "The stock ledger", "Settings",
           "Database backup and restore",
           "Notifications and keeping alerts current",
           "Everything the other roles do", "Reports and exports",
           "Security you are responsible for", "Working in Amharic",
           "When something goes wrong"]
    s = sec_signin("the <strong>Dashboard</strong> — yours alone")
    s += """
<h2 id="setup">First-time setup checklist</h2>
<p class="lead">Do these in order before letting staff on the system.</p>
<div class="card"><ol class="steps">
  <li><strong>Change the demo passwords</strong><span>The seeded accounts (<code>admin</code>,
      <code>pharmacist1</code>, <code>cashier1</code>, <code>storemanager1</code>) all share a
      known password. Change or delete them before going live. This is the single most important
      step on this page.</span></li>
  <li><strong>Fill in Settings</strong><span>Pharmacy name, logo, phone, address, licence and TIN
      numbers, currency, default tax rate, invoice prefix and footer. These appear on every receipt
      and report.</span></li>
  <li><strong>Create real staff accounts</strong><span>One per person — never a shared login, or
      the audit log becomes worthless.</span></li>
  <li><strong>Set up categories and suppliers</strong><span>Or have your Store Manager do it.</span></li>
  <li><strong>Load the catalogue</strong><span>Bring opening stock in through
      <em>Record Purchase</em> where you can, so costs are accurate from day one.</span></li>
  <li><strong>Schedule the notification refresh</strong><span>See the Notifications section.</span></li>
  <li><strong>Take a backup, and test that it restores</strong><span>An untested backup is a
      guess.</span></li>
</ol></div>

<h2 id="dashboard">The Dashboard and what each chart tells you</h2>
<p class="lead">Your landing page, and restricted to you — it shows cost prices, margins and
per-staff performance.</p>
""" + svg_dashboard() + """
<div class="card">
<h4 style="margin-top:0">The KPI cards</h4>
<p style="margin:0 0 8px">All nine are clickable and take you to the detail behind the number.</p>
<table>
 <tr><th>Card</th><th>Goes to</th></tr>
 <tr><td>Total Medicines / Categories</td><td>The catalogue lists</td></tr>
 <tr><td>Low Stock / Expired</td><td>The matching stock report</td></tr>
 <tr><td>Today's Sales</td><td>Sales history</td></tr>
 <tr><td>Monthly Sales</td><td>Sales Summary report</td></tr>
 <tr><td>Customers / Suppliers</td><td>Those lists</td></tr>
 <tr><td>Purchase Value / Sales Value / Profit</td><td>The Purchase, Sales and Profit reports</td></tr>
</table>
</div>
<div class="card">
<h4 style="margin-top:0">Reading the analytics</h4>
<table>
 <tr><th>Chart</th><th>What to look for</th></tr>
 <tr><td><strong>Revenue vs Cost of Goods Sold</strong></td>
     <td>The gap between the bars is your gross margin. A narrowing gap month on month means costs
     are rising faster than prices — the most important signal on this page</td></tr>
 <tr><td><strong>Payment Method Mix</strong></td>
     <td>Split by revenue, not transaction count, so it shows where the money actually arrives.
     Useful for cash-handling and reconciliation decisions</td></tr>
 <tr><td><strong>Expiry Risk Profile</strong></td>
     <td>Bars are item counts; the red line is <strong>value at risk</strong>. Watch the line —
     a few expiring insulin packs matter far more than a shelf of cheap tablets</td></tr>
 <tr><td><strong>Top Customers by Spend</strong></td><td>Who is worth retaining</td></tr>
 <tr><td><strong>Sales by Staff Member</strong></td>
     <td>Revenue served. Read it alongside shift patterns before drawing conclusions</td></tr>
 <tr><td>Monthly Sales / Sales Trend</td><td>Direction of travel; the 14-day trend catches sudden
     drops early</td></tr>
 <tr><td>Top Selling Medicines / Stock by Category</td><td>What moves, and where stock is tied up</td></tr>
</table>
</div>
<div class="info"><strong>Profit here excludes VAT and uses true batch cost</strong> — the same
basis as the Profit report, so the two always agree.</div>

<h2 id="branches">Managing branches</h2>
<p class="lead">Menu → <strong>Branches</strong>. Only you can create or edit
them.</p>
""" + svg_branches() + """
<div class="card"><ol class="steps">
  <li><strong>Add Branch</strong><span>Name, city, phone, licence number. Set an
      <em>invoice prefix</em> such as <code>BOL-</code> so each branch's invoice
      numbers are distinguishable at a glance.</span></li>
  <li><strong>Assign a manager</strong><span>Only Store Managers and
      Administrators can be chosen.</span></li>
  <li><strong>Assign staff to it</strong><span>In Staff &amp; Roles. A branch
      with no staff cannot trade.</span></li>
  <li><strong>Stock it</strong><span>A new branch starts empty. Either record a
      purchase against it, or have a Store Manager transfer stock in.</span></li>
</ol></div>
<div class="card">
<h4 style="margin-top:0">Switching between branches</h4>
<p style="margin:0 0 8px">You are the only role that can. Use the shop icon in
the top bar. <strong>Everything on screen follows your selection</strong> — the
dashboard, stock, sales and reports. Check which branch you are in before
reading a figure or recording anything.</p>
<p style="margin:0"><strong>Compare all branches</strong> in the same menu shows
every product across every branch side by side. That is where you spot stock
sitting idle in one branch while another has none.</p>
</div>
<div class="warn"><strong>Deactivating, not deleting.</strong> A branch with
sales or purchases cannot be deleted — its history has to remain auditable. Mark
it inactive instead. The main branch cannot be deactivated at all; make another
branch the main one first.</div>

<h2 id="staff">Managing staff and roles</h2>
<p class="lead">Menu → <strong>Staff &amp; Roles</strong>. Choosing the role is the single most
consequential decision here.</p>
""" + svg_roles_matrix() + """
<div class="card"><ol class="steps">
  <li><strong>Add Staff</strong><span>Name, username, email, phone, and — most importantly —
      <strong>Role</strong>.</span></li>
  <li><strong>Give them a temporary password</strong><span>They will be forced to replace it on
      first sign-in, so you never know their working password.</span></li>
  <li><strong>Choose the role carefully</strong><span>It decides everything they can reach. When in
      doubt, give less — you can always widen it.</span></li>
  <li><strong>Assign a branch</strong><span>Every role except Administrator
      must have one, or they will have no stock to work with. Leave it blank
      <em>only</em> for Administrators — a blank branch is what grants the
      cross-branch view.</span></li>
  <li><strong>To remove someone, untick Active Employee</strong><span>Do not delete. Deactivating
      blocks access while keeping their name on the sales and stock movements they made.</span></li>
</ol></div>
<table>
 <tr><th>Role</th><th>Give it to someone who…</th></tr>
 <tr><td><strong>Cashier</strong></td><td>Works the counter. Till, receipts, customers. No stock,
     no costs</td></tr>
 <tr><td><strong>Pharmacist</strong></td><td>Dispenses. Everything a Cashier has, plus stock,
     expiry, batches and suppliers — but no costs</td></tr>
 <tr><td><strong>Store Manager</strong></td><td>Buys and controls stock. Catalogue, purchases,
     stock corrections, costs, profit, exports. <strong>No till</strong></td></tr>
 <tr><td><strong>Administrator</strong></td><td>Runs the system. Everything, including settings,
     audit log, voids and backups. Keep this list short</td></tr>
</table>
<div class="warn"><strong>Never create a shared login.</strong> The audit log records who did what;
a shared account makes that record meaningless and removes any accountability.</div>

<h2 id="catalogue">The standard catalogue</h2>
<p class="lead">This is now a platform-level function, not something any pharmacy's own Administrator
account reaches — including yours.</p>
<div class="card">
<h4 style="margin-top:0">What changed, and why</h4>
<p style="margin:0 0 10px">The standard catalogue (generic names, strengths, forms, legal
classes, ATC codes) is shared reference data across every pharmacy on the platform, not this
pharmacy's own data. Letting each pharmacy's Administrator browse or edit it directly meant
one company's sloppy addition could quietly affect every other company's reports. It's now
managed by platform staff only.</p>
<p style="margin:0">This doesn't block your staff from adding stock — Store Managers still search and
link new medicines against the catalogue from <strong>Add Medicine</strong>, exactly as before,
and it's still strongly recommended: it's what keeps the same medicine reading the same way
across every pharmacy in reporting. It's no longer <em>required</em>, though — a genuine medicine
that isn't on the catalogue can still be added, typed in by hand, and is simply flagged
<strong>Not Standardised</strong> on the medicine list so it stays easy to reconcile later.
What's gone is the separate "browse the catalogue" screen and the ability to add a new catalogue
entry yourselves; if staff can't find something and it should really be standard, escalate it to
platform administration to add.</p>
</div>
<div class="note">If you also happen to be the platform administrator for this installation,
that's a separate account and a separate part of the system (Pharmacies + Standard Catalogue,
only visible when signed in as platform staff) — not something reachable from this pharmacy's
own Administrator login.</div>

<h2 id="void">Voiding a sale</h2>
<p class="lead">Only you can do this. Menu → <strong>Sales</strong> → open the invoice →
<strong>Void</strong>.</p>
<div class="card"><ol class="steps">
  <li><strong>Confirm it is the right invoice</strong><span>Check the number, customer and total
      against what you were told.</span></li>
  <li><strong>Type a real reason</strong><span>"wrong item dispensed", "customer returned unopened
      pack" — this is what an auditor reads later.</span></li>
  <li><strong>Confirm</strong><span>Every item returns to <strong>the exact batch it came from</strong>,
      so costing stays honest. The invoice stays on record marked <em>Voided</em> — it is never
      deleted, because a money record should not vanish.</span></li>
</ol></div>
<div class="note">A sale cannot be voided twice, and voiding is recorded against your name with the
date and reason.</div>

<h2 id="delpurchase">Deleting a purchase</h2>
<p class="lead">Menu → <strong>Purchases</strong> → open it → <strong>Delete</strong>.</p>
<div class="card">
<p style="margin:0 0 10px">This reverses the stock the purchase added. <strong>Units already sold
are left alone</strong> — clawing those back would corrupt both the stock count and the recorded
cost of those sales.</p>
<p style="margin:0"><strong>The usual reason:</strong> a Store Manager saved a purchase with wrong
figures. Delete it, then have them record it correctly.</p>
</div>

<h2 id="audit">The audit log</h2>
<p class="lead">Menu → <strong>Audit Log</strong>. Restricted to you.</p>
<div class="card">
<p style="margin:0 0 10px">Every change is recorded with <strong>who, what, when and from which
network address</strong>. It is <strong>append-only</strong> — nobody, including you, can edit or
delete an entry. That is what makes it worth anything.</p>
<table>
 <tr><th>Filter</th><th>Use it to answer</th></tr>
 <tr><td>Action = Deleted</td><td>What has been removed recently, and by whom</td></tr>
 <tr><td>Action = Failed login</td><td>Is someone trying to guess a password? Repeated failures
     from one address deserve a look</td></tr>
 <tr><td>Record Type = medicine.Medicine</td><td>Who has been changing prices or products</td></tr>
 <tr><td>Search a username</td><td>Everything one person did, for a review or an investigation</td></tr>
</table>
<p class="mini" style="margin:10px 0 0">Failed logins record only the attempted username — never
the password.</p>
</div>
<div class="info"><strong>Make it a habit.</strong> Five minutes a week on the Deleted and Failed
login filters catches most problems while they are still small.</div>

<h2 id="ledger">The stock ledger</h2>
<p class="lead">Menu → <strong>Inventory</strong> → <strong>Manage</strong> →
<strong>Stock Ledger</strong>.</p>
""" + svg_ledger() + """
<div class="card">
<p style="margin:0 0 10px">The audit log records who changed a <em>record</em>.
The stock ledger records every change to <em>stock</em> — and the two answer
different questions. Use the ledger when a quantity is disputed.</p>
<p style="margin:0"><strong>It is complete by construction.</strong> Every path
that changes stock writes here: purchases, sales, voids, deleted purchases,
transfers (both sides), manual movements, stocktakes and opening balances. For
any product, the ledger entries sum exactly to the current stock figure — if
they ever did not, that would itself be the finding.</p>
</div>

<h2 id="settings">Settings</h2>
<p class="lead">Menu → <strong>Settings</strong>. These flow through to the interface, receipts and
labels.</p>
<table>
 <tr><th>Setting</th><th>Where it shows up / what it affects</th></tr>
 <tr><td>Pharmacy name, logo</td><td>Sidebar, login page, receipts, shelf labels</td></tr>
 <tr><td>Phone, email, address</td><td>Printed receipts</td></tr>
 <tr><td>Licence number, TIN</td><td>Printed receipts — required for a compliant invoice</td></tr>
 <tr><td>Currency</td><td>Every money figure in the system</td></tr>
 <tr><td>Default Tax Rate</td><td>Pre-fills new products. Existing products keep their own rate</td></tr>
 <tr><td>Invoice Prefix</td><td>Applied to <em>new</em> invoices only; existing numbers never change</td></tr>
 <tr><td>Invoice Footer</td><td>Bottom of every customer receipt</td></tr>
 <tr><td><strong>Large Sale Alert Threshold</strong></td><td>Sales at or above this raise a
     notification. Set it high enough to be meaningful, or it becomes noise</td></tr>
 <tr><td><strong>Currency per Loyalty Point</strong></td><td>How much a customer spends to earn one
     point</td></tr>
</table>

<h2 id="backup">Database backup and restore</h2>
<p class="lead">Menu → <strong>Settings</strong> → <strong>Download Backup</strong>.</p>
<div class="card">
<h4 style="margin-top:0">On SQLite (typical single-branch setup)</h4>
<p style="margin:0">The button downloads the database file — a complete, directly restorable
backup. Store it somewhere secure and off the machine: it contains every customer, sale and price
in the pharmacy.</p>
</div>
<div class="card">
<h4 style="margin-top:0">On PostgreSQL (larger deployments)</h4>
<p style="margin:0 0 8px">The button is <strong>deliberately disabled</strong>. A valid backup must
be taken on the database server, and a browser download would produce an incomplete file — more
dangerous than no backup, because you would trust it. The page shows the exact command:</p>
<p style="margin:0"><code>pg_dump -U &lt;user&gt; -d pharmacare -F c -f pharmacare-backup.dump</code></p>
</div>
<div class="warn"><strong>A backup you have never restored is not a backup.</strong> Once a quarter,
restore into a spare copy and check a few recent sales appear. Note how long it took — that is your
real recovery time.</div>
<div class="card"><ol class="steps">
  <li><strong>Daily</strong><span>Automated backup, kept off the machine</span></li>
  <li><strong>Weekly</strong><span>Verify the newest file opens and is a sensible size</span></li>
  <li><strong>Quarterly</strong><span>Full restore test into a spare environment</span></li>
  <li><strong>Before any upgrade</strong><span>Take one, and keep it until you are confident</span></li>
</ol></div>

<h2 id="notifications">Notifications and keeping alerts current</h2>
<div class="card">
<p style="margin:0 0 10px">Stock, expiry and pending-payment alerts recalculate when someone opens
the Notifications page and when <strong>Refresh</strong> is pressed. To keep them current overnight,
schedule this with Windows Task Scheduler:</p>
<p style="margin:0 0 10px"><code>python manage.py refresh_notifications</code></p>
<ul style="margin:0 0 0 18px" class="mini">
  <li>Program: <code>C:\\path\\to\\venv\\Scripts\\python.exe</code></li>
  <li>Arguments: <code>manage.py refresh_notifications</code></li>
  <li>Start in: <code>C:\\path\\to\\pharmacare</code></li>
</ul>
</div>
<div class="note">Condition-based alerts clear themselves when the situation is fixed. Event alerts
(new purchase, large sale) stay, because the event did happen.</div>

<h2 id="others">Everything the other roles do</h2>
<p class="lead">You can do all of it. The role guides cover each in detail — the essentials:</p>
""" + svg_batch_costing() + """
<div class="note"><strong>Above:</strong> why the profit figures can be trusted. Each delivery keeps
its own cost, soonest-expiry stock is dispensed first, and buying at a new price never rewrites the
profit on sales already made.</div>
<table>
 <tr><th>Task</th><th>Where</th><th>Watch out for</th></tr>
 <tr><td>Sell at the till</td><td>Point of Sale</td><td>Rx items prompt for confirmation</td></tr>
 <tr><td>Record a delivery</td><td>Purchases → Record Purchase</td><td>Cannot be edited after saving</td></tr>
 <tr><td>Add a product</td><td>Medicines → Add Medicine</td><td>Medicines must link to the
     Standard Catalogue first — non-medicine types don't need one</td></tr>
 <tr><td>Correct a stock count</td><td>Inventory → Record Stock Movement</td>
     <td>Stock Adjustment takes the <strong>counted total</strong>, not the difference</td></tr>
 <tr><td>Write off expired stock</td><td>Stock Out</td><td>Put the reason in</td></tr>
 <tr><td>Check batches and costs</td><td>Inventory → Batches</td><td>Shows the FEFO dispensing order</td></tr>
</table>

<h2 id="reports">Reports and exports</h2>
<div class="card">
<p style="margin:0 0 10px">All nine reports, all three formats. Access is per report — a Cashier
sees three, a Pharmacist seven, you and the Store Manager see nine.</p>
<ul style="margin:0 0 0 18px">
  <li><strong>PDF</strong> — send or file; renders Amharic correctly</li>
  <li><strong>Excel</strong> — numbers arrive as numbers, so totals and sorting work</li>
  <li><strong>CSV</strong> — for another system. Opens with Amharic intact in Excel</li>
</ul>
</div>
<div class="warn">Every export carries a small footer noting it's AI-assisted output and should be
verified before it leaves the pharmacy — check the figures against the screen before sending
anything to a customer, supplier or regulator.</div>

<h2 id="security">Security you are responsible for</h2>
<table>
 <tr><th>Control</th><th>State</th><th>Your job</th></tr>
 <tr><td>Account lockout</td><td>On — 5 failures locks account and address for 30 minutes</td>
     <td>Clear a genuine lockout; investigate repeats</td></tr>
 <tr><td>Forced password change</td><td>On for new and reset accounts</td><td>Never bypass it</td></tr>
 <tr><td>Password strength</td><td>10+ characters, mixed types</td><td>Do not relax it</td></tr>
 <tr><td>Role-based access</td><td>Enforced server-side, not just hidden menus</td>
     <td>Keep the Administrator list short</td></tr>
 <tr><td>Audit log</td><td>Append-only</td><td>Review weekly</td></tr>
 <tr><td>Secret key</td><td>Set in <code>.env</code></td>
     <td class="non">Rotate from the shipped default before going live</td></tr>
 <tr><td>HTTPS / secure cookies</td><td>Switch on automatically when <code>DEBUG=False</code></td>
     <td>Make sure production runs with <code>DJANGO_ENV=production</code></td></tr>
</table>
<div class="warn"><strong>Before going live, confirm three things:</strong> demo passwords changed,
<code>DJANGO_SECRET_KEY</code> rotated, and a tested backup exists.</div>
"""
    s += sec_language()
    s += sec_troubleshoot([
        ("A user is locked out", "5 failed sign-ins", "Wait for the 30 minutes, or clear the "
         "lockout. If it repeats, check the audit log for failed logins"),
        ("Someone cannot reach a page they need", "Their role does not include it",
         "Change their role in Staff &amp; Roles — do not work around it with a shared account"),
        ("Stock and batch totals disagree", "Stock changed outside the normal flow",
         "Check Inventory → Batches for that product, then correct with a Stock Adjustment"),
        ("A purchase was recorded wrongly", "Purchases are immutable",
         "Delete it (stock reverses), then have it re-entered"),
        ("Profit report and Dashboard disagree", "They should not — both use batch cost, net of VAT",
         "Check the date ranges match; report a bug if they still differ"),
        ("Amharic looks wrong in a CSV opened in Excel", "Excel guessed the encoding",
         "Use Data → From Text and choose UTF-8, or use the Excel/PDF export instead"),
        ("Alerts are out of date", "The refresh task is not running",
         "Press Refresh, then check the scheduled task"),
        ("Backup button disabled", "You are on PostgreSQL, by design",
         "Use the pg_dump command shown on the page"),
        ("Site shows a plain error page", "<code>DEBUG=False</code>, so details are hidden",
         "Check the server log. Never turn DEBUG on in production to diagnose"),
    ])
    return shell("PharmaCare — Administrator Guide", "Administrator",
                 "Setup, staff and roles, the audit log, settings, backups and the analytics only "
                 "you can see.", s, toc)


# ===========================================================================
# Build
# ===========================================================================
GUIDES = {
    "PharmaCare-Guide-1-Cashier": guide_cashier,
    "PharmaCare-Guide-2-Pharmacist": guide_pharmacist,
    "PharmaCare-Guide-3-Store-Manager": guide_store_manager,
    "PharmaCare-Guide-4-Administrator": guide_admin,
}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    written = []
    for name, fn in GUIDES.items():
        html_path = OUT / f"{name}.html"
        html_path.write_text(fn(), encoding="utf-8")
        written.append(html_path)
        print("HTML:", html_path.name)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("\nPlaywright not installed — HTML written, PDFs skipped.")
        return

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        for html_path in written:
            pdf_path = html_path.with_suffix(".pdf")
            page.goto(html_path.resolve().as_uri(), wait_until="networkidle")
            page.pdf(path=str(pdf_path), format="A4", print_background=True,
                     margin={"top": "13mm", "bottom": "15mm", "left": "0mm", "right": "0mm"},
                     display_header_footer=True,
                     header_template='<div></div>',
                     footer_template=(
                         '<div style="width:100%;font-size:8px;color:#8A8D95;'
                         'font-family:Inter,sans-serif;padding:0 16mm;display:flex;'
                         'justify-content:space-between;">'
                         '<span>PharmaCare Management System</span>'
                         '<span>Page <span class="pageNumber"></span> of '
                         '<span class="totalPages"></span></span></div>'))
            print("PDF: ", pdf_path.name)
        browser.close()


if __name__ == "__main__":
    main()
