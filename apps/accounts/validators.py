"""
Extra password validator enforcing character-class complexity, on top of
Django's built-in length/similarity/common-password/numeric validators.
Required for NBE-regulated environments where a simple 10-character
passphrase policy is not considered sufficient.
"""
import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class ComplexityValidator:
    """Requires at least one uppercase letter, one lowercase letter, one
    digit, and one special character."""

    def validate(self, password, user=None):
        errors = []
        if not re.search(r"[A-Z]", password):
            errors.append(_("Password must contain at least one uppercase letter."))
        if not re.search(r"[a-z]", password):
            errors.append(_("Password must contain at least one lowercase letter."))
        if not re.search(r"[0-9]", password):
            errors.append(_("Password must contain at least one digit."))
        if not re.search(r"[^A-Za-z0-9]", password):
            errors.append(_("Password must contain at least one special character (e.g. !@#$%)."))
        if errors:
            raise ValidationError(errors)

    def get_help_text(self):
        return _(
            "Your password must include an uppercase letter, a lowercase letter, "
            "a digit, and a special character."
        )
