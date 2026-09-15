# Deploying PharmaCare

This walks you from a folder on your laptop to a live URL, for free.

**Read section 0 first.** Vercel can host this app, but it is not the natural
home for a Django system like this one, and knowing why up front will save you
a bad surprise later.

---

## 0. Read this before you choose Vercel

Vercel runs your code as **serverless functions**: a fresh, read-only copy of
the app starts up to handle a request and is thrown away afterwards. That model
suits a Next.js site. It collides with three things this app does.

| What breaks | Why | What to do |
|---|---|---|
| **SQLite database** | The filesystem is discarded after each request, so every sale you record would vanish | Use free managed Postgres (Neon). Covered in step 2 — this is mandatory, not optional |
| **File uploads** (pharmacy logo, product images) | Nowhere durable to write them | They save to `/tmp` and disappear. Fine for a demo. For real use, add object storage (section 8) |
| **Database backup button** | There is no database *file* to download on Postgres | Already handled: the Settings page detects Postgres and shows the `pg_dump` command instead |

Also worth knowing:

- **Cold starts.** After a few idle minutes the first request takes 2–5 seconds
  while Django boots. Subsequent requests are fast.
- **10-second function limit** on the free plan. Every page and export in this
  app finishes well inside that, but a report over years of data eventually
  would not.
- **Scheduled jobs.** `manage.py refresh_notifications` cannot run on a
  schedule. Section 7 covers the workaround.

### If this is going to be used by a real pharmacy

Vercel is a fine way to **show the system to people**. For something staff
depend on daily, a platform that runs a normal long-lived process is a better
fit and still has a free tier:

| Platform | Free tier | Fit |
|---|---|---|
| **Render** | Web service sleeps after 15 min idle; free Postgres for 90 days | Good — a real process, disks available, cron jobs. Closest to a normal server |
| **Railway** | Monthly usage credit | Good, same reasons |
| **Fly.io** | Small always-on allowance | Good, with persistent volumes |
| **PythonAnywhere** | One free web app, always on | Django-friendly, but no Postgres on free |
| **Vercel** | Generous, never sleeps | Works, with the caveats above |

Everything in steps 1–2 applies to all of them. Step 6 is Vercel-specific;
section 9 covers Render as the alternative.

---

## 1. Put the code on GitHub

### 1.1 Install the tools (once)

- **Git** — <https://git-scm.com/download/win>. Accept the defaults.
- **A GitHub account** — <https://github.com/signup>.

Check it worked, in PowerShell:

```powershell
git --version
```

### 1.2 Prepare the folder

Open PowerShell in the project folder (the one containing `manage.py`):

```powershell
cd C:\path\to\pharmacare
```

**Make sure your secrets are not about to be committed.** `.gitignore` already
excludes `.env`, `db.sqlite3` and `media/`. Confirm:

```powershell
type .gitignore
```

You should see `.env` and `*.sqlite3` listed. If `.env` does not exist yet:

```powershell
copy .env.example .env
```

> **Never commit `.env`.** It holds your secret key and database password.
> If you ever do so by accident, treat those values as compromised and
> generate new ones — deleting the file in a later commit does not remove it
> from the history.

### 1.3 Create the repository

```powershell
git init
git add .
git commit -m "PharmaCare pharmacy management system"
```

Check what went in — this is the moment to catch a mistake:

```powershell
git ls-files | Select-String -Pattern "\.env$|\.sqlite3$"
```

That should print **nothing**. If it prints a filename, stop and fix
`.gitignore`, then `git rm --cached <file>` before continuing.

### 1.4 Push it

On GitHub: **New repository** → name it `pharmacare` → **Private** (this is
business software; there is no reason for it to be public) → **do not** add a
README or .gitignore, since you already have both → **Create repository**.

Then copy the commands GitHub shows you, which look like:

```powershell
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/pharmacare.git
git push -u origin main
```

Your browser will ask you to sign in to GitHub the first time.

Refresh the GitHub page — your files should be there.

---

## 2. Create the database (Neon — free Postgres)

Do this before Vercel, because Vercel needs the connection string.

1. Go to <https://neon.com> and sign up (you can use your GitHub account).
2. **Create project.** Name it `pharmacare`. Pick the region closest to your
   users — for Ethiopia, `Europe (Frankfurt)` is usually the lowest latency.
3. On the dashboard, find **Connection string** and copy it. It looks like:

   ```
   postgresql://pharmacare_owner:AbC123xyz@ep-cool-name-123456.eu-central-1.aws.neon.tech/pharmacare?sslmode=require
   ```

4. Keep it somewhere safe for the next steps. **This is a password** — treat it
   like one.

> Neon's free tier suspends the database after a few minutes of inactivity and
> wakes it on the next connection, which adds about a second to the first
> request. That is normal, not a fault.

---

## 3. Create the tables and your admin account

Run this **from your laptop**, pointed at Neon. Vercel's build step cannot do
it reliably, and doing it by hand means you see any error clearly.

```powershell
# Activate your virtual environment first
.\venv\Scripts\Activate.ps1

# Point this shell at the Neon database (paste your own string)
$env:DATABASE_URL = "postgresql://pharmacare_owner:AbC123xyz@ep-cool-name-123456.eu-central-1.aws.neon.tech/pharmacare?sslmode=require"
$env:DJANGO_ENV = "production"
$env:DJANGO_SECRET_KEY = "temporary-value-just-for-this-command"

# Create every table
python manage.py migrate

# Create your own administrator account (choose a real password)
python manage.py createsuperuser
```

Optionally load the sample catalogue so the system is not empty while you
explore it:

```powershell
python manage.py seed_catalog
```

> **Do not run `seed_accounts` against a live database.** It creates four demo
> users who all share a publicly documented password.

`migrate` should end with a list of `... OK` lines. If it hangs or refuses to
connect, check the connection string is complete, including `?sslmode=require`.

---

## 4. Generate a real secret key

Django uses this to sign sessions and password-reset links. The shipped value
is a placeholder and must be replaced.

```powershell
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Copy the output. Keep it with your Neon string for the next step.

---

## 5. Deploy to Vercel

### 5.1 Sign up and import

1. Go to <https://vercel.com/signup> and choose **Continue with GitHub**.
2. **Add New… → Project**.
3. Find `pharmacare` in the list and press **Import**. You may need to press
   **Adjust GitHub App Permissions** and grant access to the repository, since
   it is private.
4. Leave the framework preset as **Other**. `vercel.json` in the repository
   already tells Vercel what to do.
5. **Do not press Deploy yet** — open **Environment Variables** first.

### 5.2 Environment variables

Add each of these. Set them for **Production, Preview and Development** so
preview deployments work too.

| Name | Value |
|---|---|
| `DATABASE_URL` | Your full Neon connection string from step 2 |
| `DJANGO_SECRET_KEY` | The key you generated in step 4 |
| `DJANGO_ENV` | `production` |
| `DJANGO_DEBUG` | `False` |
| `DJANGO_ALLOWED_HOSTS` | `.vercel.app` (leading dot = all subdomains) |
| `PHARMACY_NAME` | Your pharmacy's name |
| `PHARMACY_CURRENCY` | `ETB` |
| `PHARMACY_INVOICE_PREFIX` | `INV-` |

> `DJANGO_DEBUG` **must** be `False`. With it on, Django shows your settings
> and database credentials on any error page, to anyone who visits.

You do not need to set `CSRF_TRUSTED_ORIGINS` — it already defaults to
`https://*.vercel.app`.

### 5.3 Deploy

Press **Deploy** and wait — the first build takes 2–4 minutes while it installs
Django, Pillow and ReportLab.

When it finishes you get a URL like `https://pharmacare-abc123.vercel.app`.

### 5.4 Check it

1. Open the URL. You should see the **sign-in page**, styled correctly. If the
   page loads but looks unstyled, static files are not being served — see
   section 10.
2. Sign in with the superuser you created in step 3.
3. Walk through: **Settings** (fill in your pharmacy details), **Medicines**,
   **Point of Sale**, **Reports → Profit → Export PDF**.
4. Open the URL on your phone and confirm the menu button works.

---

## 6. After the first deploy

### Pushing changes

Vercel redeploys automatically on every push to `main`:

```powershell
git add .
git commit -m "Describe what changed"
git push
```

### When you change a model

Migrations are **not** applied automatically. Run them yourself, against Neon,
exactly as in step 3:

```powershell
$env:DATABASE_URL = "postgresql://..."
python manage.py migrate
```

Do this **before or immediately after** pushing code that needs the new
columns, or the live site will error until you do.

### Your own domain

Vercel project → **Settings → Domains** → add e.g. `pharmacy.example.com`, then
create the DNS record Vercel shows you. Afterwards, add the domain to
`DJANGO_ALLOWED_HOSTS`:

```
.vercel.app,pharmacy.example.com
```

---

## 7. Keeping alerts current

Low-stock, expiry and pending-payment alerts recalculate when someone opens the
Notifications page or presses **Refresh**. On a serverless host you cannot run
`manage.py refresh_notifications` on a timer.

**Option A — do nothing.** Alerts refresh whenever a manager opens the page.
For a single-branch pharmacy this is usually enough.

**Option B — Vercel Cron.** Add a small protected endpoint that calls the same
service function, then in `vercel.json`:

```json
"crons": [{ "path": "/api/cron/refresh", "schedule": "0 2 * * *" }]
```

Protect it with a shared secret in the query string or a header, so it is not
world-callable. Free plans allow one cron job per day.

**Option C — Render or Railway** instead, which run real scheduled jobs.

---

## 8. Making uploads persist (optional)

Product images and the pharmacy logo currently save to `/tmp` and disappear.
Everything else works fine without this — the logo simply falls back to the
text name.

To fix it properly, add Cloudinary (free tier):

```powershell
pip install cloudinary django-cloudinary-storage
```

Then add `cloudinary_storage` and `cloudinary` to `INSTALLED_APPS`, point the
`default` entry in `STORAGES` at Cloudinary's backend, and set
`CLOUDINARY_URL` as an environment variable. Nothing else in the app needs
changing, because all image fields go through Django's storage API.

---

## 9. Alternative: Render (closer to a normal server)

If the caveats in section 0 bother you, Render is a better fit and the repo
needs no extra files.

1. <https://render.com> → sign up with GitHub.
2. **New → Postgres**, name it `pharmacare-db`, free plan. Copy the **Internal
   Database URL**.
3. **New → Web Service** → pick your repo. Settings:
   - **Build Command:**
     `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate`
   - **Start Command:** `gunicorn pharmacare.wsgi:application`
4. Add the same environment variables as section 5.2, with
   `DJANGO_ALLOWED_HOSTS` set to `.onrender.com`.
5. Deploy.

Note that migrations **do** run automatically here, and `gunicorn` is already
in `requirements.txt`.

Render's free web service sleeps after 15 minutes idle, so the first visit
afterwards takes ~30 seconds. Its free Postgres expires after 90 days, so take
a backup before then.

---

## 10. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `DisallowedHost at /` | Your domain is not in `DJANGO_ALLOWED_HOSTS` | Add `.vercel.app` (or your domain), then redeploy |
| Page loads but has no styling | Static files not served | Confirm `whitenoise.middleware.WhiteNoiseMiddleware` is second in `MIDDLEWARE` and `WHITENOISE_USE_FINDERS = True` |
| `no such table: accounts_user` | You skipped step 3 | Run `migrate` against `DATABASE_URL` |
| `'sslmode' is an invalid keyword argument` | A `sqlite://` URL with SSL forced on | Already handled — SSL is applied only to `postgres://` URLs |
| CSRF verification failed | Origin not trusted | Add your domain to `DJANGO_CSRF_TRUSTED_ORIGINS`, **including** `https://` |
| Redirect loop | HTTPS not detected behind the proxy | Already handled by `SECURE_PROXY_SSL_HEADER`; make sure you did not override it |
| First request very slow, then fast | Cold start plus Neon waking up | Normal on free tiers |
| `FUNCTION_INVOCATION_TIMEOUT` | Over 10 seconds | Narrow the report's date range |
| Uploaded logo vanishes | Ephemeral filesystem | Expected — see section 8 |
| One failed login locks out everyone | Proxy IP seen for all users | Already handled by `AXES_IPWARE_META_PRECEDENCE_ORDER` |
| Amharic shows as boxes in a PDF | `static/fonts/` missing from the deploy | Confirm `static/fonts/*.ttf` is committed (`git ls-files static/fonts`) |

### Reading the logs

Vercel project → **Logs**, or:

```powershell
npx vercel logs <your-deployment-url>
```

With `DJANGO_DEBUG=False` the browser shows only a generic error page, and the
detail is in these logs. **Never turn `DEBUG` on in production to diagnose a
problem** — read the logs instead.

---

## 11. Before real patients depend on it

Hosting it is not the same as being ready to use it.

- [ ] Demo accounts deleted or their passwords changed (`admin`,
      `pharmacist1`, `cashier1`, `storemanager1` ship with a documented password)
- [ ] `DJANGO_SECRET_KEY` is your own generated value, not the shipped one
- [ ] `DJANGO_DEBUG=False` confirmed on the live site
- [ ] Repository is **private**, and `.env` is not in its history
- [ ] Settings page filled in: pharmacy name, licence number, TIN
- [ ] One real account per member of staff — never a shared login, or the audit
      log becomes meaningless
- [ ] A backup taken **and restored** into a test database at least once
- [ ] Someone other than you knows how to reach the logs and take a backup
- [ ] Data-residency and patient-confidentiality requirements checked against
      where your database physically lives — Neon's Frankfurt region means
      Ethiopian pharmacy data sits in Germany, which may need approval
