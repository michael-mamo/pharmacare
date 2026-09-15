"""
Vercel entry point.

Vercel looks for a WSGI/ASGI callable in this file and turns it into a
serverless function. Everything else — routing, middleware, static files — is
handled by Django itself.
"""
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pharmacare.settings")

from pharmacare.wsgi import application  # noqa: E402

# Vercel accepts `app` or `application`; both are exported for clarity.
app = application
