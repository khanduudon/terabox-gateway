# TeraBox API (terabot)

Lightweight Flask-based API and CLI for extracting file information and direct download links from TeraBox share URLs.

This project exposes:
- A web API with multiple endpoints for listing files and getting direct links
- A simple CLI helper to test a hosted API

The API internally uses `aiohttp` to call TeraBox endpoints and requires periodically updated browser cookies to work reliably.

---

## Features

- GET /api: List files with metadata (size in bytes and human-readable, thumbnails, path)
- GET /api2: Same as above, plus resolves direct download redirect targets when possible
- GET /help: Inline API documentation
- GET /health: Health check
- Async route handlers for better I/O throughput

---

## Directory structure

```
terabot/
├─ endpoints/           # reserved for future modularization of routes
├─ public/              # static assets (optional)
├─ api.py               # Flask app + HTTP client logic
├─ main.py              # small CLI to test a remote API
├─ apiurl.txt           # optional: store the base URL used by the CLI
└─ README.md            # this file
```

---

## Requirements

- Python 3.9+
- pip 21+
- Packages:
  - Flask (2.2+ recommended)
  - aiohttp
  - requests

Install them:

```
python -m venv .venv
.venv\Scripts\activate
pip install -U pip
pip install Flask aiohttp requests
```

Optional (for production/ASGI or Windows service wrappers):
- hypercorn or waitress

---

## Running the API locally

Option A: run the script directly

```
python terabot\api.py
```

Option B: use Flask runner (requires Flask 2.2+)

```
set FLASK_APP=terabot.api
flask run --host 0.0.0.0 --port 5000
```

The server will start on http://localhost:5000

---

## Updating cookies (important)

TeraBox protects its APIs and requires valid session cookies. The file `terabot/api.py` contains a `cookies` dictionary. You must refresh these values periodically from your browser:

1. Log in to https://www.terabox.com (or the regional domain you use).
2. Open DevTools (F12) → Application/Storage → Cookies.
3. Copy the following cookie keys and paste their current values into `api.py`:
   - `PANWEB`, `__bid_n`, `ndus`, `csrfToken`, `browserid`, `lang`, `ndut_fmt`
4. Restart the API.

Notes:
- Do not commit your personal cookies to a public repository.
- These values expire; when the API stops returning data, refresh them.

---

## API usage

Base URL (local): http://localhost:5000

- GET `/`  
  Returns API metadata.

- GET `/health`  
  Simple health check.

- GET `/help`  
  Returns structured documentation.

- GET `/api?url=<share_url>[&pwd=<password>]`  
  Lists files for a TeraBox share link. Use `pwd` for password-protected shares.

- GET `/api2?url=<share_url>`  
  Lists files and attempts to resolve direct download links via HEAD redirect.

Example requests:

```
curl "http://localhost:5000/api?url=https://teraboxshare.com/s/XXXXXXXX"
curl "http://localhost:5000/api?url=https://teraboxshare.com/s/XXXXXXXX&pwd=abcd"
curl "http://localhost:5000/api2?url=https://teraboxshare.com/s/XXXXXXXX"
```

Successful response shape (abbreviated):

```
{
  "status": "success",
  "url": "<requested url>",
  "files": [
    {
      "filename": "movie.mp4",
      "size": "1.23 GB",
      "size_bytes": 1321231234,
      "download_link": "https://dlink...",
      "is_directory": false,
      "thumbnails": {
        "320x180": "https://thumb..."
      },
      "path": "/path/in/share",
      "fs_id": "1234567890"
    }
  ],
  "total_files": 1,
  "timestamp": "2025-01-01T00:00:00Z"
}
```

Common error:

```
{
  "status": "error",
  "error": "Verification required",
  "errno": 400141,
  "requires_password": true
}
```

---

## CLI helper (terabot/main.py)

This small script calls a hosted API to quickly get a direct link.

Usage:

```
python terabot\main.py
# Then paste a share link when prompted
```

You can change the remote API base URL by editing `API_URL` in `main.py` or by storing it in `apiurl.txt` (and updating the script accordingly if you want to read from that file).

---

## Notes and caveats

- This project depends on upstream site behavior which can change without notice.
- If you receive empty results or HTTP errors, refresh the cookies in `api.py`.
- Endpoint `/api2` performs HEAD requests to resolve redirects; some hosts may rate-limit or block this.
- Respect TeraBox terms of service. Use this project for personal/educational purposes only.

---

## Troubleshooting

- 400141 errno: Provide the `pwd` query param (password required) or the link may require additional verification.
- HTTP 5xx from the API:
  - Check your cookies.
  - Verify the share link is valid and accessible in your region.
  - Reduce request rate to avoid rate limits.
- SSL or network errors:
  - Ensure your system date/time is correct.
  - Try again from another network.

Enable basic logging by watching the console output from `api.py`; it logs each step (token extraction, file listing, etc.).

---

## Development tips

- Keep asynchronous functions non-blocking; do network I/O with `aiohttp`.
- If you modularize routes, place blueprints in `terabot/endpoints/` and register them in `api.py`.
- For deployment behind a reverse proxy, set `X-Forwarded-*` headers appropriately and run a production server (e.g., `hypercorn terabot.api:app --bind 0.0.0.0:5000`).

---

## License

No license specified. If you plan to distribute, add a license file appropriate for your use.