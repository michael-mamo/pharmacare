"""
Imports a standard catalogue from CSV — the path to using the authority's own
list rather than the bundled starter set.

    python manage.py import_catalogue efda_register.csv --source EFDA

Expected columns (header row required; only `generic_name` is mandatory):

    generic_name, brand_name, strength, dosage_form, route, atc_code,
    category, schedule, product_type, default_unit, pack_size, manufacturer,
    country_of_origin, efda_registration_number, barcode, is_essential,
    requires_cold_chain, notes

Matching is on generic_name + strength + dosage_form + brand_name, so
re-importing an updated list revises rows in place rather than duplicating
them. Unknown dosage forms and schedules are reported rather than guessed:
silently mapping an unrecognised form to "Other" would quietly corrupt the
very standardisation this catalogue exists to provide.
"""
import csv

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.catalogue.models import (
    AdministrationRoute, CatalogueCategory, CatalogueProduct, DataSource,
    DosageForm, ScheduleClass,
)

TRUE_VALUES = {"1", "true", "yes", "y", "t"}


class Command(BaseCommand):
    help = "Import standard catalogue products from a CSV file."

    def add_arguments(self, parser):
        parser.add_argument("path", help="Path to the CSV file.")
        parser.add_argument(
            "--source", default=DataSource.EFDA,
            choices=[c[0] for c in DataSource.choices],
            help="Provenance to record against every imported row.",
        )
        parser.add_argument(
            "--deactivate-missing", action="store_true",
            help="Mark catalogue rows absent from this file as inactive. Use only "
                 "with a complete authority list, never a partial one.",
        )
        parser.add_argument("--dry-run", action="store_true",
                            help="Report what would change without writing.")

    def handle(self, *args, **options):
        path = options["path"]
        source = options["source"]
        dry_run = options["dry_run"]

        try:
            handle = open(path, newline="", encoding="utf-8-sig")
        except OSError as e:
            raise CommandError(f"Could not open {path}: {e}")

        forms = {c[0] for c in DosageForm.choices}
        routes = {c[0] for c in AdministrationRoute.choices}
        schedules = {c[0] for c in ScheduleClass.choices}

        created = updated = skipped = 0
        problems = []
        seen_ids = []

        with handle:
            reader = csv.DictReader(handle)
            if "generic_name" not in (reader.fieldnames or []):
                raise CommandError(
                    "CSV must have a 'generic_name' column. Found: "
                    f"{reader.fieldnames}"
                )
            for row_number, row in enumerate(reader, start=2):
                generic = (row.get("generic_name") or "").strip()
                if not generic:
                    problems.append(f"row {row_number}: no generic_name, skipped")
                    skipped += 1
                    continue

                form = (row.get("dosage_form") or "TABLET").strip().upper()
                if form not in forms:
                    problems.append(
                        f"row {row_number} ({generic}): unknown dosage_form "
                        f"'{form}' — row skipped rather than guessed"
                    )
                    skipped += 1
                    continue

                route = (row.get("route") or "ORAL").strip().upper()
                if route not in routes:
                    problems.append(f"row {row_number} ({generic}): unknown route '{route}'")
                    route = AdministrationRoute.NA

                schedule = (row.get("schedule") or "OTC").strip().upper()
                if schedule not in schedules:
                    problems.append(f"row {row_number} ({generic}): unknown schedule '{schedule}'")
                    schedule = ScheduleClass.OTC

                category = None
                category_name = (row.get("category") or "").strip()
                if category_name and not dry_run:
                    category, _c = CatalogueCategory.objects.get_or_create(
                        name=category_name, defaults={"sort_order": 500}
                    )

                lookup = {
                    "generic_name": generic,
                    "brand_name": (row.get("brand_name") or "").strip(),
                    "strength": (row.get("strength") or "").strip(),
                    "dosage_form": form,
                }
                defaults = {
                    "route": route,
                    "atc_code": (row.get("atc_code") or "").strip().upper(),
                    "category": category,
                    "schedule": schedule,
                    "product_type": (row.get("product_type") or "MEDICINE").strip().upper(),
                    "default_unit": (row.get("default_unit") or "TABLET").strip().upper(),
                    "pack_size": (row.get("pack_size") or "").strip(),
                    "manufacturer": (row.get("manufacturer") or "").strip(),
                    "country_of_origin": (row.get("country_of_origin") or "").strip(),
                    "efda_registration_number": (row.get("efda_registration_number") or "").strip(),
                    "barcode": (row.get("barcode") or "").strip(),
                    "is_essential": (row.get("is_essential") or "").strip().lower() in TRUE_VALUES,
                    "requires_cold_chain": (row.get("requires_cold_chain") or "").strip().lower() in TRUE_VALUES,
                    "notes": (row.get("notes") or "").strip(),
                    "data_source": source,
                    "is_active": True,
                }

                if dry_run:
                    exists = CatalogueProduct.objects.filter(**lookup).exists()
                    updated += 1 if exists else 0
                    created += 0 if exists else 1
                    continue

                with transaction.atomic():
                    obj, was_created = CatalogueProduct.objects.update_or_create(
                        **lookup, defaults=defaults
                    )
                seen_ids.append(obj.pk)
                created += 1 if was_created else 0
                updated += 0 if was_created else 1

        if options["deactivate_missing"] and not dry_run and seen_ids:
            stale = CatalogueProduct.objects.filter(
                data_source=source, is_active=True
            ).exclude(pk__in=seen_ids)
            count = stale.count()
            stale.update(is_active=False)
            self.stdout.write(self.style.WARNING(
                f"Marked {count} row(s) inactive as absent from this file."
            ))

        for problem in problems[:40]:
            self.stdout.write(self.style.WARNING(f"  {problem}"))
        if len(problems) > 40:
            self.stdout.write(self.style.WARNING(f"  ...and {len(problems) - 40} more"))

        verb = "would be" if dry_run else ""
        self.stdout.write(self.style.SUCCESS(
            f"{created} {verb} created, {updated} {verb} updated, {skipped} skipped. "
            f"Provenance recorded as {source}."
        ))
