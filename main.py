import os

# Attempt relative import if executed as a module, otherwise fall back to direct import
try:
    from .api import app  # type: ignore
except Exception:
    from api import app  # type: ignore

# Expose WSGI-compatible callable for production servers (gunicorn, waitress, etc.)
application = app


def main():
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    main()
