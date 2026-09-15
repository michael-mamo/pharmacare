"""
Django settings for the PharmaCare Management System.

Environment-driven configuration:
    - Development defaults to SQLite (zero-config).
    - Production is enabled by setting DJANGO_ENV=production and DATABASE_*
      environment variables (PostgreSQL).

See: https://docs.djangoproject.com/en/6.1/topics/settings/
"""
from pathlib import Path
from decouple import config, Csv

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Core / Security
# ---------------------------------------------------------------------------
SECRET_KEY = config(
    "DJANGO_SECRET_KEY",
    default="django-insecure-CHANGE-ME-IN-PRODUCTION-8vdhj3jxl@encycc5yzw",
)

DJANGO_ENV = config("DJANGO_ENV", default="development")  # development | production

DEBUG = config("DJANGO_DEBUG", default=(DJANGO_ENV != "production"), cast=bool)

ALLOWED_HOSTS = config(
    "DJANGO_ALLOWED_HOSTS", default="127.0.0.1,localhost", cast=Csv()
)

# Vercel gives every deployment its own subdomain, so the wildcards cover
# preview deployments as well as production. Django requires the scheme here.
CSRF_TRUSTED_ORIGINS = config(
    "DJANGO_CSRF_TRUSTED_ORIGINS",
    default="https://*.vercel.app,https://*.onrender.com",
    cast=Csv(),
)

# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
]

THIRD_PARTY_APPS = [
    "crispy_forms",
    "crispy_bootstrap5",
    "axes",  # brute-force login protection (account lockout after repeated failures)
]

# Local apps are added incrementally, phase by phase.
# Phase 1: accounts (auth + RBAC), dashboard (KPI dashboard + charts)
LOCAL_APPS = [
    "apps.organizations",
    "apps.core",
    "apps.catalogue",
    "apps.branches",
    "apps.accounts",
    "apps.dashboard",
    "apps.suppliers",  # Phase 2 (loaded before medicine: Medicine FKs to Supplier)
    "apps.medicine",
    "apps.customers",
    "apps.purchases",  # Phase 3
    "apps.inventory",
    "apps.sales",  # Phase 4
    "apps.reports",  # Phase 5
    "apps.notifications",  # Phase 6
    "apps.audit",
    "apps.settings_app",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # Serves collected static files without a separate web server. Must sit
    # directly after SecurityMiddleware and before everything else.
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    # LocaleMiddleware must come after Session (reads language from session/
    # cookie) and before Common (so translated URLs/prefixes are respected).
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Custom middleware: exposes request.user to signals/models for the
    # Phase 6 Audit Log.
    "apps.accounts.middleware.CurrentUserMiddleware",
    # Resolves request.branch for every authenticated request. Must run
    # after AuthenticationMiddleware, since it depends on request.user.
    # Organization first: branches are scoped to an organization, so the
    # tenant must be known before the branch is resolved.
    "apps.organizations.context.OrganizationContextMiddleware",
    "apps.branches.context.BranchContextMiddleware",
    # Forces a password change for accounts flagged force_password_change=True
    # (new staff accounts, or accounts an Administrator has just reset).
    "apps.accounts.middleware.ForcePasswordChangeMiddleware",
    # django-axes: must be last so it sees the final response/exception
    # and can enforce lockouts on repeated failed logins.
    "axes.middleware.AxesMiddleware",
]

AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",  # checked first: blocks locked-out users
    "django.contrib.auth.backends.ModelBackend",
]

ROOT_URLCONF = "pharmacare.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.i18n",
                "apps.dashboard.context_processors.pharmacy_settings",
            ],
        },
    },
]

WSGI_APPLICATION = "pharmacare.wsgi.application"

# ---------------------------------------------------------------------------
# Database
#   Development (default): SQLite — zero configuration.
#   Production: set DJANGO_ENV=production and the DATABASE_* variables below
#   to point to PostgreSQL (recommended for NBE-regulated production use).
# ---------------------------------------------------------------------------
DATABASE_URL = config("DATABASE_URL", default="")

if DATABASE_URL:
    # Managed Postgres providers (Neon, Supabase, Render, Railway) hand you a
    # single connection URL, so prefer it when present. `conn_max_age=0` is
    # deliberate on serverless platforms such as Vercel: each request may run
    # in a fresh instance, so a pooled connection cannot be reused and holding
    # one open just exhausts the database's connection limit.
    import dj_database_url

    # `ssl_require` injects an `sslmode` option, which SQLite rejects outright
    # ("'sslmode' is an invalid keyword argument"). Managed Postgres needs it;
    # a sqlite:// URL (handy for a local production-mode smoke test) must not
    # get it. So decide from the URL scheme rather than forcing it on.
    _is_postgres = DATABASE_URL.startswith(("postgres://", "postgresql://", "postgis://"))
    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=config("DATABASE_CONN_MAX_AGE", default=0, cast=int),
            ssl_require=(
                _is_postgres
                and config("DATABASE_SSL_REQUIRE", default=True, cast=bool)
            ),
        )
    }
elif DJANGO_ENV == "production":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": config("DATABASE_NAME"),
            "USER": config("DATABASE_USER"),
            "PASSWORD": config("DATABASE_PASSWORD"),
            "HOST": config("DATABASE_HOST", default="localhost"),
            "PORT": config("DATABASE_PORT", default="5432"),
            "CONN_MAX_AGE": 60,
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# ---------------------------------------------------------------------------
# Custom User Model & Authentication
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
    {"NAME": "apps.accounts.validators.ComplexityValidator"},
]

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "dashboard:landing"  # role-aware; dashboard is admin-only
LOGOUT_REDIRECT_URL = "accounts:login"

# ---------------------------------------------------------------------------
# Internationalization
#   The interface ships in English and Amharic from Phase 1 onward. Every
#   later phase must wrap user-facing strings in {% trans %} / {% blocktrans %}
#   (templates) or gettext_lazy (Python) — see LANGUAGES below and the
#   language switcher in templates/partials/navbar.html.
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "en"
LANGUAGES = [
    ("en", "English"),
    ("am", "አማርኛ"),
]
LOCALE_PATHS = [BASE_DIR / "locale"]
TIME_ZONE = config("DJANGO_TIME_ZONE", default="Africa/Addis_Ababa")
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static & Media files
# ---------------------------------------------------------------------------
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

# CompressedStaticFilesStorage (not the *Manifest* variant) on purpose: the
# manifest version raises a 500 if any template references a file missing
# from the manifest, which is a poor failure mode on a platform where you
# cannot easily inspect the build output.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

# Serve static files straight from the app directories, without requiring a
# `collectstatic` step first. This matters on Vercel: its Python builder does
# not run management commands, so STATIC_ROOT would otherwise be empty and
# every stylesheet would 404. Finders are consulted in addition to
# STATIC_ROOT, so running collectstatic (on Render, Railway, a VM) still
# works and takes priority.
WHITENOISE_USE_FINDERS = True
WHITENOISE_AUTOREFRESH = DEBUG
WHITENOISE_MAX_AGE = 0 if DEBUG else 60 * 60 * 24 * 30

MEDIA_URL = "media/"
# On Vercel (and most serverless hosts) the application directory is
# read-only and every instance is discarded after the request, so uploads
# must go to /tmp. They will NOT persist — see DEPLOYMENT.md for how to wire
# up object storage if you need the pharmacy logo and product images to stick.
ON_SERVERLESS = bool(config("VERCEL", default="")) or bool(config("AWS_LAMBDA_FUNCTION_NAME", default=""))
MEDIA_ROOT = Path("/tmp/media") if ON_SERVERLESS else BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Email (used for password reset & invoice emailing in later phases)
# ---------------------------------------------------------------------------
if DJANGO_ENV == "production":
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = config("EMAIL_HOST", default="")
    EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
    EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)
    EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
    EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
    DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default=EMAIL_HOST_USER)
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
    DEFAULT_FROM_EMAIL = "no-reply@pharmacare.local"

# ---------------------------------------------------------------------------
# Crispy Forms (Bootstrap 5 styling for all ModelForms)
# ---------------------------------------------------------------------------
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# ---------------------------------------------------------------------------
# Security hardening
# ---------------------------------------------------------------------------
# Cookies: enforced in every environment, not just production.
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"

# Baseline headers, enforced in every environment.
SECURE_CONTENT_TYPE_NOSNIFF = True

# Platforms like Vercel, Render and Railway terminate TLS at their edge and
# forward plain HTTP, so Django must be told the original request was secure —
# otherwise SECURE_SSL_REDIRECT would loop forever.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True

SECURE_BROWSER_XSS_FILTER = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

# TLS-dependent hardening: only safe to force once the site is actually
# served over HTTPS, i.e. in production.
if not DEBUG:
    SECURE_SSL_REDIRECT = config("DJANGO_SECURE_SSL_REDIRECT", default=True, cast=bool)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# ---------------------------------------------------------------------------
# django-axes: account lockout after repeated failed login attempts
# (brute-force / credential-stuffing protection).
# ---------------------------------------------------------------------------
AXES_FAILURE_LIMIT = config("AXES_FAILURE_LIMIT", default=5, cast=int)
AXES_COOLOFF_TIME = config("AXES_COOLOFF_TIME", default=0.5, cast=float)  # hours (30 min)
AXES_LOCKOUT_PARAMETERS = ["username", "ip_address"]
# Behind a proxy the real client address arrives in X-Forwarded-For. Without
# this, django-axes sees the proxy's address for everyone, so one person's
# failed logins would lock out every user of the site.
AXES_IPWARE_META_PRECEDENCE_ORDER = [
    "HTTP_X_FORWARDED_FOR",
    "HTTP_X_REAL_IP",
    "REMOTE_ADDR",
]
AXES_IPWARE_PROXY_COUNT = config("AXES_PROXY_COUNT", default=None, cast=lambda v: int(v) if v else None)
AXES_RESET_ON_SUCCESS = True
AXES_LOCKOUT_TEMPLATE = "accounts/locked_out.html"
AXES_VERBOSE = False

# ---------------------------------------------------------------------------
# PharmaCare brand palette (used by templates; matches organization branding)
# ---------------------------------------------------------------------------
BRAND_COLORS = {
    "primary": "#F1AB15",  # brand yellow
    "dark": "#000000",
    "light": "#FFFFFF",
}

# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------
SESSION_COOKIE_AGE = config("SESSION_COOKIE_AGE", default=28800, cast=int)  # 8 hours
SESSION_SAVE_EVERY_REQUEST = True
