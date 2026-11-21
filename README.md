# MV Mowers — Advanced Business Website

A responsive Flask + SQLite starter website for MV Mowers with:
- Home and services pages
- Service search
- Contact form stored in SQLite
- Customer registration, sign-in, and account page
- Admin dashboard for messages, orders, and gallery uploads
- Photo gallery
- Optional Stripe Checkout integration (test mode first)

## Project structure

```text
mv_mowers_website/
├── app.py
├── requirements.txt
├── .env.example
├── config.py
├── mv_mowers.db             # created automatically at first run
├── static/
│   ├── css/style.css
│   ├── js/main.js
│   └── uploads/             # admin-uploaded photos
└── templates/
    ├── base.html
    ├── index.html
    ├── services.html
    ├── search.html
    ├── contact.html
    ├── login.html
    ├── register.html
    ├── account.html
    ├── gallery.html
    ├── payments.html
    ├── admin.html
    └── 403.html
```

## Local setup

1. Install Python 3.11 or newer.
2. Open a terminal in this folder.
3. Create a virtual environment:
   - macOS/Linux: `python3 -m venv .venv && source .venv/bin/activate`
   - Windows: `py -m venv .venv` then `.venv\\Scripts\\activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Copy `.env.example` to `.env`, then replace `SECRET_KEY` with a long random value.
6. Run: `flask --app app run`
7. Open `http://127.0.0.1:5000`.

The database is created automatically.

## Create the first administrator

For a local first-run setup, register a normal customer account at `/register`.
Then open a Python shell in the project folder:

```bash
python
>>> import sqlite3
>>> conn = sqlite3.connect("mv_mowers.db")
>>> conn.execute("UPDATE users SET is_admin=1 WHERE email=?", ("YOUR_EMAIL_HERE",))
>>> conn.commit()
>>> conn.close()
>>> exit()
```

Sign out and back in, then visit `/admin`. Do not expose this one-time promotion method publicly.
For a real deployment, use a controlled admin-provisioning script and remove public registration if it is not needed.

## Online payments

The payment page uses Stripe Checkout so card numbers are handled by Stripe, not stored on this website.
1. Create a Stripe account with the responsible business owner.
2. Start in Stripe test mode.
3. Put the Stripe **test secret key** in `.env` as `STRIPE_SECRET_KEY`.
4. Restart the server and test with Stripe's published test card details from its official documentation.
5. Before accepting real payments, have the business owner complete Stripe identity/business verification, configure live keys, set up verified webhooks, refunds, receipts, tax handling, and clear service-payment terms.

The included success redirect checks the Checkout Session, but a production system should treat signed Stripe webhooks as the authoritative payment confirmation. Do not switch to live payments until the responsible account owner has completed all required checks.

## Production checklist

- Set a strong random `SECRET_KEY`; never use the example value.
- Set `FLASK_DEBUG=0`; run behind HTTPS with Gunicorn and a reverse proxy.
- Add CSRF protection (e.g. Flask-WTF), rate limiting, email verification, password reset, and login throttling.
- Add signed Stripe webhooks and idempotency for payment state.
- Back up SQLite or migrate to PostgreSQL for multi-worker production use.
- Restrict admin creation, use least privilege, and review uploaded files.
- Add a privacy notice, terms, cancellation/refund policy, and contact details.
- Configure email delivery for contact-form notifications.
- Replace placeholder content and add only photos the business has permission to use.

## Customization

Edit the `SERVICES` list near the top of `app.py` to update service descriptions.
Replace the brand mark and colors in `templates/base.html` and `static/css/style.css`.
The current contact numbers are the two business numbers supplied for the MV Mowers design.
