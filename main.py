import os
from typing import Callable


# Lazy WSGI application loader
# Vercel's function runtime imports this module in an isolated environment
# where preinstalled or vendored packages may temporarily be incompatible
# with the Flask version. To avoid importing Flask at module import time
# (which caused the werkzeug LocalProxy error), delay importing `api` until
# the WSGI callable is invoked.
_app: Callable | None = None


def _load_app() -> Callable:
    global _app
    if _app is None:
        # Import here so it happens at request time rather than module import
        from api import app as real_app  # type: ignore

        _app = real_app
    return _app


def application(environ, start_response):
    """WSGI entrypoint used by Vercel / WSGI servers.

    This function lazily imports and returns the real Flask app.
    """
    app = _load_app()
    return app(environ, start_response)


def main():
    # Provide a local dev runner that imports the app synchronously.
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    app = _load_app()
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    main()
