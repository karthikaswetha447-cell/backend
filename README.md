# VelvetAura Beauty

Flask e-commerce demo with HTML templates, CSS/JavaScript assets, and an SQLite database.

## Run locally on Windows

Open PowerShell in this folder and run:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

Then open http://127.0.0.1:5000. Keep the PowerShell window open while using the site. Stop it with Ctrl+C.

The local database is `velvetaura.db`. It is intentionally excluded from Git so customer data is not published.

## What is included

- Product catalog API: `GET /api/products`
- Account creation and login: `/api/auth/register`, `/api/auth/login`
- Contact enquiries: `POST /api/contact`
- Orders: `POST /api/orders`; server looks up product prices before saving
- Health check: `GET /api/health`

Passwords are stored as hashes. The contact form saves enquiries to SQLite; it does not email or text the business owner yet.

## Publishing

GitHub Pages serves static HTML, CSS, and JavaScript; it does not run this Flask backend. To keep account, enquiry, and order features working, publish this project to GitHub as the source and deploy the Flask app to a Python web host.

For a Render web service, use:

- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn app:app --bind 0.0.0.0:$PORT`
- Health check: `/api/health`
- Set `VELVETAURA_SECRET_KEY` to a long random secret.
- If using HTTPS, set `FLASK_HTTPS=1`.
- For SQLite data to survive redeploys, attach persistent storage and set `DATABASE_PATH` to a file path on that storage. Without persistent storage, stored orders and enquiries can be lost when the service is replaced.

Do not publish `.env`, `.venv`, or `velvetaura.db`. The phone and Gmail in the contact page are sample details; replace them before publishing.
