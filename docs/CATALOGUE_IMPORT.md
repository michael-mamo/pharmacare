# Loading the real EFDA product registry

The bundled catalogue (`seed_catalogue`) is a WHO Model List of Essential
Medicines-aligned starter set (~500 generics, tagged `WHO_EML`) — genuinely
real medicines, but not the *complete* set of everything registered for sale
in Ethiopia. That complete list exists — EFDA runs a live public registry at
**<https://www.eris.efda.gov.et/products>**, reportedly covering ~12,000
registered items — but it's a JavaScript web app with no static export
Claude (or a plain `curl`/`requests` script) can read directly.

The importer for that real data already exists and needs no changes:

```
python manage.py import_catalogue efda_register.csv --source EFDA
```

It's idempotent (re-importing an updated file revises rows in place rather
than duplicating them) and refuses to guess an unrecognised dosage form or
schedule rather than silently mis-filing it — see the command's own
docstring (`apps/catalogue/management/commands/import_catalogue.py`) for the
exact CSV column list.

## Getting the real data into that CSV

Pick whichever of these you can actually do:

1. **Check eRIS itself for an export button.** Regulatory portals like this
   often have one even when the main page doesn't show product data
   directly (I could only fetch the page's raw HTML, not click around it
   — an actual browser session may show an "Export" or "Download" option
   I couldn't see). Worth five minutes of looking before anything else.

2. **Ask EFDA directly.** Public regulators sometimes provide data extracts
   on request for legitimate business use — worth an email to EFDA before
   assuming you need to scrape anything.

3. **Have a developer capture the underlying API.** Open eRIS in a browser,
   open DevTools → Network tab, filter to `Fetch/XHR`, and browse the
   product list — the JSON responses that appear are what the page itself
   is reading from. Save those responses and write a short script to
   convert them to the CSV columns above. This is a real but small
   engineering task — happy to write that conversion script once someone
   has a sample JSON response in hand to work from.

4. **A third-party copy surfaced in search** ("Registered Products -
   Ethiopia", circulating as an .xlsx/.pdf) claiming to be an EFDA export.
   Unverified — check it against eRIS itself for a few known products
   before trusting it, since there's no way to confirm its authenticity or
   currency from search results alone.

Whichever route gets you a real file, the importer handles the rest.
