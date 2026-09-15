# NOTE: Submit buttons are rendered in the templates, not via a crispy
# Submit() in the Layout. The `{{ form|crispy }}` *filter* renders fields
# only and silently ignores FormHelper.layout — a Submit() placed here
# would never appear on the page. (The `{% crispy form %}` *tag* honours
# the layout, but emits its own <form> element, which would nest inside
# the <form> our templates already provide.) Keep buttons in templates.
"""
ModelForms / Forms for the accounts app, styled with django-crispy-forms
(Bootstrap 5 template pack, configured in settings.CRISPY_TEMPLATE_PACK).
"""
from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordResetForm,
    SetPasswordForm,
    UserChangeForm,
    UserCreationForm,
)
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Field

from .models import Role, User


class StyledAuthenticationForm(AuthenticationForm):
    """Login form. Bootstrap classes are applied via widget attrs so it also
    renders correctly without crispy in case a template is customised."""

    username = forms.CharField(
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Username", "autofocus": True}
        )
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Password"})
    )


class StaffUserCreationForm(UserCreationForm):
    """Used by Administrators to create new staff accounts (Pharmacist,
    Cashier, Store Manager, or another Administrator)."""

    email = forms.EmailField(required=True)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "role",
            "branch",
            "profile_image",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # This form is reachable by any pharmacy Administrator — System
        # Administrator is a platform-wide role with no organization of its
        # own (see create_system_admin), so it must never be selectable
        # from inside one pharmacy's own staff screen. Restricting choices
        # here isn't just cosmetic: Django's ChoiceField validates a
        # submitted value against this list too, so a hand-crafted POST of
        # role=SYSTEM_ADMIN is rejected server-side, not merely hidden from
        # the dropdown.
        self.fields["role"].choices = [
            choice for choice in self.fields["role"].choices if choice[0] != Role.SYSTEM_ADMIN
        ]
        self._configure_branch_field()
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column("first_name", css_class="col-md-6"),
                Column("last_name", css_class="col-md-6"),
            ),
            Row(
                Column("username", css_class="col-md-6"),
                Column("email", css_class="col-md-6"),
            ),
            Row(
                Column("phone_number", css_class="col-md-6"),
                Column("role", css_class="col-md-6"), Column("branch", css_class="col-md-6"),
            ),
            "profile_image",
            Row(
                Column("password1", css_class="col-md-6"),
                Column("password2", css_class="col-md-6"),
            ),
        )


class StaffUserUpdateForm(UserChangeForm):
    """Used by Administrators to edit an existing staff member.
    Password is managed separately (change/reset), so it is excluded here."""

    password = None

    class Meta:
        model = User
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "role",
            "branch",
            "profile_image",
            "is_active_employee",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")
        self.fields["is_active_employee"].widget.attrs["class"] = "form-check-input"
        # Same restriction as StaffUserCreationForm, and just as necessary
        # here — without it, a pharmacy Administrator could promote an
        # existing member of their own staff (e.g. a Cashier) straight to
        # platform-wide System Administrator by editing them.
        self.fields["role"].choices = [
            choice for choice in self.fields["role"].choices if choice[0] != Role.SYSTEM_ADMIN
        ]
        self._configure_branch_field()
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column("first_name", css_class="col-md-6"),
                Column("last_name", css_class="col-md-6"),
            ),
            Row(
                Column("username", css_class="col-md-6"),
                Column("email", css_class="col-md-6"),
            ),
            Row(
                Column("phone_number", css_class="col-md-6"),
                Column("role", css_class="col-md-6"), Column("branch", css_class="col-md-6"),
            ),
            "profile_image",
            Field("is_active_employee"),
        )


class StyledPasswordResetForm(PasswordResetForm):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "you@pharmacy.com"})
    )


class StyledSetPasswordForm(SetPasswordForm):
    new_password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control"}), label="New password"
    )
    new_password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control"}), label="Confirm new password"
    )


class ForcedPasswordChangeForm(SetPasswordForm):
    """Shown to any user with force_password_change=True. Clears the flag
    once a new password is successfully set."""

    new_password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control", "autofocus": True}),
        label="New password",
    )
    new_password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control"}), label="Confirm new password"
    )

    def save(self, commit=True):
        user = super().save(commit=False)
        user.force_password_change = False
        if commit:
            user.save()
        return user


class ProfileUpdateForm(forms.ModelForm):
    """Any logged-in user can update their own basic profile info."""

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "phone_number", "profile_image", "preferred_language"]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "phone_number": forms.TextInput(attrs={"class": "form-control"}),
            "preferred_language": forms.Select(attrs={"class": "form-select"}),
        }


def _configure_branch_field(self):
    """Restricts the branch choice to active branches and explains the
    consequence of leaving it blank.

    A blank branch is meaningful, not missing: it is what gives an
    Administrator the cross-branch view. For every other role a blank branch
    means they cannot reach any stock, so the form says so plainly.
    """
    field = self.fields.get("branch")
    if field is None:
        return
    from apps.branches.models import Branch

    field.queryset = Branch.objects.filter(is_active=True).order_by("-is_main", "name")
    field.required = False
    field.empty_label = "— All branches (Administrators only) —"
    field.help_text = (
        "The branch this person works at. Leave blank only for Administrators, "
        "who work across every branch. Cashiers, Pharmacists and Store Managers "
        "must be assigned to a branch or they will have no stock to work with."
    )
    if hasattr(field.widget, "attrs"):
        field.widget.attrs.setdefault("class", "form-select")


# Attach to both staff forms so the behaviour cannot drift between them.
StaffUserCreationForm._configure_branch_field = _configure_branch_field
StaffUserUpdateForm._configure_branch_field = _configure_branch_field
