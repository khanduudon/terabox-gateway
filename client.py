import argparse
import requests

from pathlib import Path

from typing import Optional

DEFAULT_BASE = "https://terabox-api.vercel.app"


def load_base_url() -> str:
    """Try to read base API URL from apiurl.txt next to this script; fallback to default."""
    try:
        p = Path(__file__).with_name("apiurl.txt")
        if p.exists():
            content = p.read_text(encoding="utf-8").strip()
            if content:
                return content.rstrip("/")
    except Exception:
        pass
    return DEFAULT_BASE


def build_api_url(base: str, mode: str) -> str:
    """Return the full API prefix like: https://host/api?url="""

    endpoint = "/api2" if mode == "api2" else "/api"

    return f"{base.rstrip('/')}{endpoint}?url="


def extract_first_link(data):
    """Extract a direct link from different possible API response shapes."""
    try:
        if isinstance(data, dict):
            # Legacy shape
            if data.get("success") and data.get("downloadLink"):
                return data["downloadLink"]

            if data.get("link"):
                return data["link"]

            # Our Flask API shape
            files = data.get("files")
            if isinstance(files, list) and files:
                f0 = files[0] or {}
                for key in ("direct_link", "download_link", "link", "dlink"):
                    if f0.get(key):
                        return f0[key]
    except Exception:
        pass
    return None


def get_terabox_link(share_link: str, mode: str = "api", base: Optional[str] = None):
    api_base = base.rstrip("/") if base else load_base_url()
    api_url = build_api_url(api_base, mode)

    try:
        response = requests.get(api_url + share_link, timeout=30)
        print("📥 RAW Response:", response.text)  # Debugging
        data = response.json()
        return extract_first_link(data)
    except Exception as e:
        print(f"❌ API Error: {e}")

        return None


def main():
    parser = argparse.ArgumentParser(
        description="TeraBox direct link extractor via hosted API"
    )
    parser.add_argument("share_link", nargs="?", help="TeraBox share link")
    parser.add_argument(
        "--mode",
        choices=["api", "api2"],
        default="api",
        help="API endpoint to use: /api (file info) or /api2 (attempt direct links)",
    )
    parser.add_argument(
        "--base",
        help="Override base API URL (default is read from apiurl.txt or a built-in default)",
    )
    args = parser.parse_args()

    share_link = args.share_link
    if not share_link:
        print("🔸 TeraBox Direct Link Extractor")

        share_link = input("📥 Enter Terabox link: ").strip()

    base_in_use = args.base or load_base_url()
    print(f"⏳ Processing via {args.mode} at {base_in_use} ...")

    direct_link = get_terabox_link(share_link, mode=args.mode, base=args.base)

    if direct_link:
        print("✅ Direct Link:", direct_link)

    else:
        print("⚠️ Failed to get the direct link. Try again later.")


if __name__ == "__main__":
    main()
