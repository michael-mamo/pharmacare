"""
Standard product catalogue.

Why this exists
---------------
Until now every pharmacy typed its own product names. That produces
"Paracetamol 500mg", "paracetamol 500 mg", "PCM 500" and "Panadol 500mg" as
four unrelated products, which makes group reporting, price comparison and
regulatory returns impossible. A shared reference catalogue fixes that: a
pharmacy *registers* stock against a standard record rather than inventing a
name.

What is standardised and what is not
------------------------------------
The catalogue holds the **identity** of a product — its international
non-proprietary name (INN), strength, dosage form, route, ATC code,
manufacturer and registration number. It deliberately holds no prices and no
stock: those are commercial and per-pharmacy, and live on `Medicine` as
before. A `Medicine` gains an optional link to its catalogue record, so a
pharmacy that wants to add something unusual can still do so unlinked.

About the seed data — read this before relying on it
----------------------------------------------------
The bundled starter set is built from well-established INN medicines and
dosage forms (the WHO Model List of Essential Medicines is the usual basis
for such a list). **It is not an extract of the EFDA register**, and the
`efda_registration_number` field is left blank rather than guessed. Before
this is used for anything regulatory, the catalogue must be loaded from, or
reconciled against, the Ethiopian Food and Drug Authority's own published
list, and `data_source` set accordingly. `import_catalogue` accepts a CSV so
that can be done without code changes.
"""
from django.core.validators import RegexValidator
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

atc_validator = RegexValidator(
    regex=r"^[A-Z]\d{2}[A-Z]{2}\d{2}$|^[A-Z]\d{2}[A-Z]{0,2}$|^$",
    message=_("Enter a valid ATC code, e.g. N02BE01 or a partial code like N02BE."),
)


class DosageForm(models.TextChoices):
    """How the product is presented. Kept as a fixed list because free text
    here is exactly what the catalogue exists to prevent."""

    TABLET = "TABLET", _("Tablet")
    CAPSULE = "CAPSULE", _("Capsule")
    SYRUP = "SYRUP", _("Syrup")
    SUSPENSION = "SUSPENSION", _("Suspension")
    SOLUTION = "SOLUTION", _("Solution")
    INJECTION = "INJECTION", _("Injection")
    INFUSION = "INFUSION", _("Infusion")
    CREAM = "CREAM", _("Cream")
    OINTMENT = "OINTMENT", _("Ointment")
    GEL = "GEL", _("Gel")
    DROPS = "DROPS", _("Drops")
    INHALER = "INHALER", _("Inhaler")
    SUPPOSITORY = "SUPPOSITORY", _("Suppository")
    PESSARY = "PESSARY", _("Pessary")
    PATCH = "PATCH", _("Patch")
    POWDER = "POWDER", _("Powder")
    SACHET = "SACHET", _("Sachet")
    DEVICE = "DEVICE", _("Device")
    DRESSING = "DRESSING", _("Dressing")
    OTHER = "OTHER", _("Other")


class AdministrationRoute(models.TextChoices):
    ORAL = "ORAL", _("Oral")
    TOPICAL = "TOPICAL", _("Topical")
    IV = "IV", _("Intravenous")
    IM = "IM", _("Intramuscular")
    SC = "SC", _("Subcutaneous")
    OPHTHALMIC = "OPHTHALMIC", _("Eye")
    OTIC = "OTIC", _("Ear")
    NASAL = "NASAL", _("Nasal")
    INHALED = "INHALED", _("Inhaled")
    RECTAL = "RECTAL", _("Rectal")
    VAGINAL = "VAGINAL", _("Vaginal")
    NA = "NA", _("Not applicable")


class DataSource(models.TextChoices):
    """Where a catalogue record came from. This matters: a record a pharmacy
    typed itself carries much less authority than one loaded from the EFDA
    register, and reports should be able to tell them apart."""

    EFDA = "EFDA", _("EFDA register")
    WHO_EML = "WHO_EML", _("WHO Essential Medicines List")
    STARTER = "STARTER", _("Bundled starter set (verify before regulatory use)")
    LOCAL = "LOCAL", _("Added locally")


class ScheduleClass(models.TextChoices):
    OTC = "OTC", _("Over the counter")
    POM = "POM", _("Prescription only")
    CONTROLLED = "CONTROLLED", _("Controlled substance")


class CatalogueCategory(models.Model):
    """Therapeutic grouping, independent of any pharmacy's own categories.

    A pharmacy's `medicine.Category` is theirs to arrange as they like (by
    shelf, by supplier, however they work). This is the clinical grouping,
    which has to stay stable for reporting to mean anything.
    """

    name = models.CharField(max_length=120, unique=True, verbose_name=_("Name"))
    code = models.CharField(max_length=20, blank=True, verbose_name=_("Code"))
    description = models.CharField(max_length=255, blank=True, verbose_name=_("Description"))
    sort_order = models.PositiveIntegerField(default=100, verbose_name=_("Sort Order"))

    class Meta:
        verbose_name = _("Catalogue Category")
        verbose_name_plural = _("Catalogue Categories")
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class CatalogueProduct(models.Model):
    """One standard product identity.

    Uniqueness is on (generic_name, strength, dosage_form, brand_name) rather
    than on name alone: "Amoxicillin 250mg Capsule" and "Amoxicillin 500mg
    Capsule" are genuinely different products, and two brands of the same
    molecule are different pack identities a pharmacy may stock separately.
    """

    generic_name = models.CharField(
        max_length=200, db_index=True, verbose_name=_("Generic Name (INN)"),
        help_text=_("International non-proprietary name, e.g. Paracetamol. This is "
                    "the name reporting groups by, so it must not carry a brand."),
    )
    brand_name = models.CharField(
        max_length=200, blank=True, db_index=True, verbose_name=_("Brand Name"),
        help_text=_("Leave blank for a generic entry."),
    )
    strength = models.CharField(
        max_length=200, blank=True, verbose_name=_("Strength"),
        help_text=_(
            "Include units, e.g. 500mg, 125mg/5ml, 0.9%. Can hold several "
            "strengths for the same form (e.g. a source list's 100mg, "
            "200mg, 400mg for one tablet) rather than forcing one row per "
            "strength."
        ),
    )
    dosage_form = models.CharField(
        max_length=20, choices=DosageForm.choices, default=DosageForm.TABLET,
        db_index=True, verbose_name=_("Dosage Form"),
    )
    route = models.CharField(
        max_length=12, choices=AdministrationRoute.choices,
        default=AdministrationRoute.ORAL, verbose_name=_("Route"),
    )
    atc_code = models.CharField(
        max_length=12, blank=True, db_index=True, validators=[atc_validator],
        verbose_name=_("ATC Code"),
        help_text=_("WHO Anatomical Therapeutic Chemical code, e.g. N02BE01."),
    )
    category = models.ForeignKey(
        CatalogueCategory, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="products", verbose_name=_("Therapeutic Category"),
    )
    schedule = models.CharField(
        max_length=12, choices=ScheduleClass.choices, default=ScheduleClass.OTC,
        db_index=True, verbose_name=_("Legal Class"),
        help_text=_("Drives the prescription warning at the till when a pharmacy "
                    "registers this product."),
    )
    product_type = models.CharField(
        max_length=12, default="MEDICINE", verbose_name=_("Product Type"),
        help_text=_("Matches the pharmacy product types: MEDICINE, COSMETIC, "
                    "SUPPLY, DEVICE, SUPPLEMENT, BABY, OTHER."),
    )
    default_unit = models.CharField(
        max_length=20, default="TABLET", verbose_name=_("Default Unit"),
        help_text=_("Pre-fills the unit when a pharmacy registers this product."),
    )
    pack_size = models.CharField(
        max_length=60, blank=True, verbose_name=_("Pack Size"),
        help_text=_("As sold, e.g. 'Box of 100', 'Bottle of 100ml'."),
    )
    manufacturer = models.CharField(max_length=200, blank=True, verbose_name=_("Manufacturer"))
    country_of_origin = models.CharField(max_length=80, blank=True, verbose_name=_("Country of Origin"))
    efda_registration_number = models.CharField(
        max_length=60, blank=True, db_index=True,
        verbose_name=_("EFDA Registration Number"),
        help_text=_("Left blank unless taken from the EFDA register — never guessed."),
    )
    barcode = models.CharField(
        max_length=64, blank=True, db_index=True, verbose_name=_("Barcode (GTIN)"),
        help_text=_("Manufacturer barcode, if the pack carries one."),
    )
    is_essential = models.BooleanField(
        default=False, db_index=True, verbose_name=_("Essential Medicine"),
        help_text=_("On the essential medicines list, so shortages matter more."),
    )
    requires_cold_chain = models.BooleanField(
        default=False, verbose_name=_("Requires Cold Chain"),
        help_text=_("Must be kept refrigerated — shown as a warning on stock pages."),
    )
    data_source = models.CharField(
        max_length=12, choices=DataSource.choices, default=DataSource.LOCAL,
        db_index=True, verbose_name=_("Data Source"),
    )
    notes = models.TextField(blank=True, verbose_name=_("Notes"))
    is_active = models.BooleanField(default=True, db_index=True, verbose_name=_("Active"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Catalogue Product")
        verbose_name_plural = _("Catalogue Products")
        ordering = ["generic_name", "strength", "brand_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["generic_name", "strength", "dosage_form", "brand_name"],
                name="unique_catalogue_identity",
            )
        ]
        indexes = [
            models.Index(fields=["generic_name", "strength"]),
            models.Index(fields=["schedule"]),
            models.Index(fields=["data_source"]),
        ]

    def __str__(self):
        return self.display_name

    def get_absolute_url(self):
        return reverse("catalogue:product_detail", kwargs={"pk": self.pk})

    @property
    def display_name(self):
        """The canonical way to write this product, used everywhere so the
        same identity always reads the same."""
        parts = [self.generic_name]
        if self.strength:
            parts.append(self.strength)
        parts.append(self.get_dosage_form_display())
        name = " ".join(str(p) for p in parts)
        if self.brand_name:
            name = f"{name} ({self.brand_name})"
        return name

    @property
    def short_name(self):
        parts = [self.brand_name or self.generic_name]
        if self.strength:
            parts.append(self.strength)
        return " ".join(str(p) for p in parts)

    @property
    def requires_prescription(self):
        return self.schedule in (ScheduleClass.POM, ScheduleClass.CONTROLLED)

    @property
    def is_verified_source(self):
        """Whether this record came from an authority rather than being typed
        in locally. Reports should be able to say how much of a catalogue is
        actually verified."""
        return self.data_source in (DataSource.EFDA, DataSource.WHO_EML)

    @property
    def registration_count(self):
        """How many pharmacy stock items are registered against this record."""
        return self.medicines.count()
