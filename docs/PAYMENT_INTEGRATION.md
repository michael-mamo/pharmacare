# Wiring up real payment processing (Chapa)

This describes what's already built, and the small, contained piece of
work that's left whenever you're ready to actually connect Chapa (or any
other provider — the design isn't Chapa-specific).

## What already exists (built, tested, working today)

- **`Payment` model** (`apps/organizations/models.py`) — one row per
  payment, provider-agnostic (`provider` + `provider_reference` are
  generic, not Chapa-specific fields).
- **`record_payment()`** — the single function that takes a payment
  effect: creates the `Payment` row, extends
  `Organization.subscription_ends_at`, updates the plan, and
  reactivates a suspended organization. Called today by a human through
  the manual **Record Payment** screen (Pharmacies → open a pharmacy →
  Record Payment); called tomorrow by a webhook. Identical either way.
- **`expire_lapsed_subscriptions`** management command — suspends any
  organization whose `subscription_ends_at` has passed. Safe to run
  daily via any scheduler (Vercel Cron, a plain cron job, whatever).
  Works today with nothing but manually recorded payments.
- **Suspension enforcement** — already real (not cosmetic): a suspended
  organization's staff are signed out immediately, mid-session, and
  can't log back in until reactivated.

None of this needed Chapa to exist first. It's usable right now as a
manual invoicing workflow — you record a bank transfer or a verified
Telebirr screenshot, the system extends the subscription and reactivates
the account.

## What Chapa integration actually adds

Two things, both additive — nothing above needs to change:

### 1. A "Pay Now" flow for pharmacy Administrators

Currently, extending a subscription requires a platform staff member to
manually visit Record Payment. A real integration adds a **self-service**
version: a pharmacy Administrator clicks something like "Renew
Subscription" inside their own account, which:

```python
# apps/organizations/services.py (new file)
import requests

def start_chapa_checkout(*, organization, amount, plan, period_end):
    resp = requests.post(
        "https://api.chapa.co/v1/transaction/initialize",
        headers={"Authorization": f"Bearer {CHAPA_SECRET_KEY}"},
        json={
            "amount": str(amount),
            "currency": organization.currency,
            "email": organization.email or "billing@pharmacare.local",
            "tx_ref": f"org-{organization.pk}-{period_end.isoformat()}",
            "callback_url": "https://.../organizations/chapa/webhook/",
            "return_url": f"https://.../organizations/{organization.pk}/",
            "meta": {"organization_id": organization.pk, "plan": plan,
                     "period_end": period_end.isoformat()},
        },
    )
    return resp.json()["data"]["checkout_url"]  # redirect the user here
```

### 2. A webhook endpoint that calls `record_payment()`

```python
# apps/organizations/views.py (new view)
class ChapaWebhookView(View):
    def post(self, request):
        # 1. Verify the signature (Chapa docs: Webhooks) — reject anything
        #    that doesn't match before trusting the payload.
        # 2. Re-query Chapa's Verify Transaction endpoint using the
        #    tx_ref — never act on the webhook payload alone (Chapa's own
        #    docs say the same: always re-verify server-side).
        # 3. Pull organization_id / plan / period_end back out of `meta`.
        # 4. Call record_payment(
        #        organization=organization, amount=..., plan=...,
        #        period_end=..., provider=PaymentProvider.CHAPA,
        #        provider_reference=tx_ref, status=PaymentStatus.SUCCESSFUL,
        #    )
        # 5. Return 200 quickly — Chapa retries on non-2xx.
        ...
```

That's the entire integration. Everything downstream — the subscription
date, the plan, reactivation, the payment ledger shown on the
organization page — already works, because it's the same function the
manual screen already calls successfully today.

## Before starting that work

1. A Chapa merchant account (business registration / KYC — see
   chapa.co) and, to start, a **test/sandbox secret key** — no need for
   a live key until this is actually tested end-to-end.
2. `CHAPA_SECRET_KEY` and `CHAPA_WEBHOOK_SECRET` as environment
   variables (same pattern as `DATABASE_URL` — never committed to git).
3. Decide the actual plan prices in ETB — `SubscriptionPlan` (TRIAL,
   BASIC, STANDARD, PREMIUM) already exists as the shape; it doesn't yet
   have prices attached anywhere, since that's a business decision, not
   a technical one.

Chapa's own docs, for reference when that time comes:
<https://developer.chapa.co/docs/accept-payments> (initializing a
transaction) and <https://developer.chapa.co/docs/webhooks> (webhook
setup and signature verification).
