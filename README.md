# TeraBox API (terabot)

A lightweight Flask-based API and command-line client for extracting file information and direct download links from TeraBox share URLs.

This project includes:
- A web API with endpoints for listing files and retrieving direct links.
- A command-line client (`client.py`) for interacting with the API from the terminal.

The API uses `aiohttp` for asynchronous requests to TeraBox and relies on browser cookies for authentication. These cookies are now managed in a separate `cookies.json` file for easier updates.

---

## Features

- **Web API**:
  - `GET /api`: Lists files with metadata, including file size, thumbnails, and paths.
  - `GET /api2`: In addition to file metadata, it resolves direct download links.
  - `GET /help`: Provides inline documentation for the API.
  - `GET /health`: A simple health check endpoint.
- **Command-Line Client**:
  - A user-friendly CLI for generating direct download links from Terabox URLs.
  - Supports configurable API endpoints.

---

## Directory Structure

```
terabot/
├─ endpoints/           # Reserved for future route modularization
├─ public/              # Static assets (optional)
├─ api.py               # The main Flask application and API logic
├─ client.py            # Command-line client for the API
├─ main.py              # Entry point for running the Flask app
├─ cookies.json         # Stores browser cookies for authentication
├─ .gitignore           # Git ignore file
└─ README.md            # This file
```

---

## Requirements

- Python 3.9+
- The following Python packages:
  - `Flask`
  - `aiohttp`
  - `requests`

You can install the required packages using pip:

```bash
pip install Flask aiohttp requests
```

---

## Running the API Locally

You can run the API by executing the `main.py` script:

```bash
python terabot/main.py
```

The server will be accessible at `http://localhost:5000`.

---

## Updating Cookies (Important)

The API requires valid browser cookies to interact with TeraBox. These are now stored in `cookies.json`. To update them:

1.  Log in to [terabox.com](https://www.terabox.com).
2.  Open your browser's developer tools (usually F12) and go to the "Application" (or "Storage") tab.
3.  Find the cookies for `terabox.com` and copy the values for the keys already present in `cookies.json`.
4.  Paste the new values into `cookies.json`.
5.  Restart the API for the changes to take effect.

You can also configure cookies using environment variables:
- `TERABOX_COOKIES_JSON`: A JSON string of cookie key-value pairs.
- `TERABOX_COOKIES_FILE`: The path to a JSON file containing the cookies.

---

## API Usage

The API validates that the provided URL is a valid TeraBox share link.

- **GET `/`**: Returns metadata about the API.
- **GET `/health`**: Performs a simple health check.
- **GET `/help`**: Displays API documentation.
- **GET `/api?url=<share_url>[&pwd=<password>]`**: Retrieves file information for a given TeraBox link.
- **GET `/api2?url=<share_url>`**: Retrieves file information and resolves direct download links.

**Example Request:**

```bash
curl "http://localhost:5000/api2?url=https://teraboxshare.com/s/XXXXXXXX"
```

---

## Command-Line Client (`client.py`)

The `client.py` script provides a simple way to get a direct download link from a Terabox URL.

**Usage:**

```bash
python terabot/client.py
```

The script will prompt you to enter a Terabox link. You can also provide the link as a command-line argument:

```bash
python terabot/client.py https://teraboxshare.com/s/XXXXXXXX
```

By default, the client uses a public API, but you can configure it to use your local instance by creating an `apiurl.txt` file in the same directory with the URL of your local server (e.g., `http://localhost:5000`).

---

## Troubleshooting

- **400141 Error**: This means the link is password-protected. Use the `&pwd=` query parameter to provide the password.
- **HTTP 5xx Errors**: This could indicate that your cookies have expired. Follow the steps in the "Updating Cookies" section to refresh them.
- **No Direct Link**: If the API fails to return a direct link, the cookies may be invalid, or the link may have expired.

---

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.