"""
Template sanity checks, run automatically by `manage.py check`.

These exist because of a bug that actually shipped: a `{# ... #}` comment was
written across three lines, and Django's inline comment tag is **single-line
only**. A multi-line `{# ... #}` is not recognised as a comment at all, so the
whole block was rendered as visible text at the top of the dashboard.

Nothing about that failure is loud — no exception, no warning, valid HTML.
The only way to catch it reliably is to look for the pattern, which is what
this does. Registered as a system check so it runs on every `manage.py check`
and in CI, rather than depending on someone remembering.
"""
import pathlib

from django.conf import settings
from django.core.checks import Error, Warning, register

TEMPLATE_SUFFIXES = (".html", ".txt")


def _template_dirs():
    dirs = []
    for engine in getattr(settings, "TEMPLATES", []):
        for directory in engine.get("DIRS", []):
            dirs.append(pathlib.Path(directory))
    # App template directories too, so an app-local template is covered.
    base = pathlib.Path(settings.BASE_DIR)
    apps_dir = base / "apps"
    if apps_dir.exists():
        dirs.extend(apps_dir.glob("*/templates"))
    return [d for d in dirs if d.exists()]


@register()
def check_single_line_template_comments(app_configs, **kwargs):
    """Flags `{# ... #}` comments whose closing tag is on a later line."""
    problems = []
    for directory in _template_dirs():
        for path in directory.rglob("*"):
            if path.suffix not in TEMPLATE_SUFFIXES or not path.is_file():
                continue
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except (OSError, UnicodeDecodeError):
                continue
            for number, line in enumerate(lines, start=1):
                if "{#" not in line:
                    continue
                after = line.split("{#", 1)[1]
                if "#}" in after:
                    continue  # properly closed on the same line
                problems.append(Error(
                    "Multi-line '{# ... #}' template comment renders as "
                    "visible text on the page.",
                    hint=("Django's '{# #}' comment is single-line only. Use "
                          "'{% comment %} ... {% endcomment %}' for anything "
                          "spanning more than one line."),
                    obj=f"{path}:{number}",
                    id="pharmacare.E001",
                ))
    return problems


@register()
def check_trans_before_load_i18n(app_configs, **kwargs):
    """Flags a `{% trans %}`/`{% blocktranslate %}` used before `{% load i18n %}`.

    Also learned the hard way: `{% load %}` takes effect from the point it
    appears onward, so prepending content above it turns every translation tag
    in that content into a TemplateSyntaxError — which only surfaces when the
    page is requested, not at startup.
    """
    problems = []
    for directory in _template_dirs():
        for path in directory.rglob("*.html"):
            if not path.is_file():
                continue
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except (OSError, UnicodeDecodeError):
                continue

            load_line = None
            for number, line in enumerate(lines, start=1):
                if "{% load" in line and "i18n" in line:
                    load_line = number
                    break

            first_trans = None
            for number, line in enumerate(lines, start=1):
                if "{% trans" in line or "{% blocktranslate" in line:
                    first_trans = number
                    break

            if first_trans is None:
                continue
            # A template that extends another may inherit the load via its own
            # {% load %}; only flag when this file uses a tag with no load at
            # all, or with the load appearing after first use.
            if load_line is None:
                problems.append(Warning(
                    "Template uses a translation tag but never loads i18n.",
                    hint="Add '{% load i18n %}' near the top of the file.",
                    obj=f"{path}:{first_trans}",
                    id="pharmacare.W002",
                ))
            elif load_line > first_trans:
                problems.append(Error(
                    "Translation tag used before '{% load i18n %}'.",
                    hint=("'{% load %}' applies from where it appears onward. "
                          "Move it above the first {% trans %} tag."),
                    obj=f"{path}:{first_trans}",
                    id="pharmacare.E003",
                ))
    return problems
