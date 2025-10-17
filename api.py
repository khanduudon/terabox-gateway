from flask import Flask, request, jsonify
import aiohttp
import asyncio
import logging
from urllib.parse import parse_qs, urlparse
from datetime import datetime


app = Flask(__name__, static_folder="public", static_url_path="/public")


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
# Optional blueprint registration: if endpoints.bp exists, register it.
try:
    from endpoints import bp as endpoints_bp  # type: ignore

    app.register_blueprint(endpoints_bp)
except Exception:
    # No blueprint found or failed to import; continue with routes defined below
    pass


# WORKING COOKIES - Update these regularly from browser
cookies = {
    "PANWEB": "1",
    "__bid_n": "199f06ecf83c6517974207",
    "ndus": "YdPCtvYteHui3XC6demNk-M2HgRzVrnh0txZQG6X",
    "csrfToken": "af9aD-FiuCbvJkukHHhOA8XV",
    "browserid": "BNT7BllyBZJWHfvSoVw8hXcWCBzRNSUvSABzO7pq-zj9qWDBOBHoyz--pRg=",
    "lang": "en",
    "ndut_fmt": "808CED9ACB7ADD765BADAF30B1F8220BB41B8E2C016E523E3D37B486C74124DD",
}

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
}


def find_between(string, start, end):
    """Extract substring between two markers"""
    start_index = string.find(start)
    if start_index == -1:
        return None
    start_index += len(start)
    end_index = string.find(end, start_index)
    if end_index == -1:
        return None
    return string[start_index:end_index]


def extract_thumbnail_dimensions(url: str) -> str:
    """Extract dimensions from thumbnail URL's size parameter"""
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    size_param = params.get("size", [""])[0]

    if size_param:
        parts = size_param.replace("c", "").split("_u")
        if len(parts) == 2:
            return f"{parts[0]}x{parts[1]}"
    return "original"


async def get_formatted_size(size_bytes):
    """Convert bytes to human-readable format"""
    try:
        size_bytes = int(size_bytes)
        if size_bytes >= 1024 * 1024 * 1024:  # GB
            size = size_bytes / (1024 * 1024 * 1024)
            unit = "GB"
        elif size_bytes >= 1024 * 1024:  # MB
            size = size_bytes / (1024 * 1024)
            unit = "MB"
        elif size_bytes >= 1024:  # KB
            size = size_bytes / 1024
            unit = "KB"
        else:
            size = size_bytes
            unit = "bytes"

        return f"{size:.2f} {unit}"
    except Exception as e:
        logging.error(f"Error formatting size: {e}")
        return "Unknown"


async def fetch_download_link(url, password=""):
    """Fetch file information from TeraBox share link"""
    try:
        async with aiohttp.ClientSession(cookies=cookies, headers=headers) as session:
            # Step 1: Get the share page and extract tokens
            logging.info(f"Fetching share page: {url}")
            async with session.get(url) as response1:
                response1.raise_for_status()
                response_data = await response1.text()

                # Extract required tokens
                js_token = find_between(response_data, "fn%28%22", "%22%29")
                log_id = find_between(response_data, "dp-logid=", "&")

                if not js_token or not log_id:
                    logging.error("Failed to extract required tokens")
                    return {
                        "error": "Failed to extract authentication tokens",
                        "errno": -1,
                    }

                request_url = str(response1.url)

                # Extract surl from URL
                if "surl=" in request_url:
                    surl = request_url.split("surl=")[1].split("&")[0]
                elif "/s/" in request_url:
                    surl = request_url.split("/s/")[1].split("?")[0]
                else:
                    logging.error("Could not extract surl from URL")
                    return {"error": "Invalid URL format", "errno": -1}

                logging.info(f"Extracted surl: {surl}, logid: {log_id}")

                # Update headers with the actual referer
                session_headers = headers.copy()
                session_headers["Referer"] = request_url

                # Step 2: Fetch file list
                params = {
                    "app_id": "250528",
                    "web": "1",
                    "channel": "dubox",
                    "clienttype": "0",
                    "jsToken": js_token,
                    "dplogid": log_id,
                    "page": "1",
                    "num": "20",
                    "order": "time",
                    "desc": "1",
                    "site_referer": request_url,
                    "shorturl": surl,
                    "root": "1",
                }

                list_url = "https://www.terabox.app/share/list"
                logging.info(f"Fetching file list from: {list_url}")

                async with session.get(
                    list_url, params=params, headers=session_headers
                ) as response2:
                    response_data2 = await response2.json()

                    errno = response_data2.get("errno", -1)

                    # Handle verification required
                    if errno == 400141:
                        logging.warning("Link requires verification")
                        return {
                            "error": "Verification required",
                            "errno": 400141,
                            "message": "This link requires password or captcha verification",
                            "surl": surl,
                            "requires_password": True,
                        }

                    # Handle other errors
                    if errno != 0:
                        error_msg = response_data2.get("errmsg", "Unknown error")
                        logging.error(f"API error {errno}: {error_msg}")
                        return {"error": error_msg, "errno": errno}

                    # Check if we got the file list
                    if "list" not in response_data2:
                        logging.error("No file list in response")
                        return {"error": "No files found in response", "errno": -1}

                    files = response_data2["list"]
                    logging.info(f"Found {len(files)} items")

                    # Step 3: If it's a directory, fetch its contents
                    if files and files[0].get("isdir") == "1":
                        logging.info("Fetching directory contents")
                        params.update(
                            {
                                "dir": files[0]["path"],
                                "order": "asc",
                                "by": "name",
                                "dplogid": log_id,
                            }
                        )
                        params.pop("desc", None)
                        params.pop("root", None)

                        async with session.get(
                            list_url, params=params, headers=session_headers
                        ) as response3:
                            response_data3 = await response3.json()

                            if "list" not in response_data3:
                                return {
                                    "error": "Failed to fetch directory contents",
                                    "errno": -1,
                                }

                            files = response_data3["list"]
                            logging.info(f"Found {len(files)} files in directory")

                    return files

    except aiohttp.ClientResponseError as e:
        logging.error(f"HTTP error: {e.status} - {e.message}")
        return {"error": f"HTTP error: {e.status}", "errno": -1}
    except Exception as e:
        logging.error(f"Unexpected error: {e}", exc_info=True)
        return {"error": str(e), "errno": -1}


async def format_file_info(file_data):
    """Format file information for API response"""
    thumbnails = {}
    if "thumbs" in file_data:
        for key, url in file_data["thumbs"].items():
            if url:
                dimensions = extract_thumbnail_dimensions(url)
                thumbnails[dimensions] = url

    return {
        "filename": file_data.get("server_filename", "Unknown"),
        "size": await get_formatted_size(file_data.get("size", 0)),
        "size_bytes": file_data.get("size", 0),
        "download_link": file_data.get("dlink", ""),
        "is_directory": file_data.get("isdir") == "1",
        "thumbnails": thumbnails,
        "path": file_data.get("path", ""),
        "fs_id": file_data.get("fs_id", ""),
    }


async def fetch_direct_links(url):
    """Fetch files with direct download links (alternative method)"""

    try:
        files = await fetch_download_link(url)

        if isinstance(files, dict) and "error" in files:
            return files

        async with aiohttp.ClientSession(cookies=cookies, headers=headers) as session:
            results = []
            for item in files or []:
                # Ensure each item is a dict; skip otherwise

                if not isinstance(item, dict):
                    logging.warning(f"Skipping non-dict item in files: {type(item)}")

                    continue

                # Get direct link by following redirect

                dlink = item.get("dlink") or ""

                direct_link = None

                if dlink:
                    try:
                        async with session.head(
                            dlink, allow_redirects=False
                        ) as response:
                            direct_link = response.headers.get("Location")

                    except Exception as e:
                        logging.error(f"Error getting direct link: {e}")

                results.append(
                    {
                        "filename": item.get("server_filename", "Unknown"),
                        "size": await get_formatted_size(item.get("size", 0)),
                        "size_bytes": item.get("size", 0),
                        "link": dlink,
                        "direct_link": direct_link,
                        "thumbnail": (item.get("thumbs") or {}).get("url3", ""),
                    }
                )

            return results

    except Exception as e:
        logging.error(f"Error in fetch_direct_links: {e}")

        return {"error": str(e), "errno": -1}


# =============== API ROUTES ===============


@app.route("/")
def index():
    """API information endpoint"""
    return jsonify(
        {
            "name": "TeraBox API",
            "version": "2.0",
            "status": "operational",
            "endpoints": {
                "/": "API information",
                "/api": "Fetch file information from TeraBox link",
                "/api2": "Fetch files with direct download links",
                "/help": "Detailed usage instructions",
                "/health": "Health check",
            },
            "contact": "@Saahiyo",
            "timestamp": datetime.utcnow().isoformat(),
        }
    )


@app.route("/health")
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "timestamp": datetime.utcnow().isoformat()})


@app.route("/api", methods=["GET"])
async def api():
    """Main API endpoint - fetch file information"""
    try:
        url = request.args.get("url")
        if not url:
            return jsonify(
                {
                    "status": "error",
                    "message": "Missing required parameter: url",
                    "example": "/api?url=https://teraboxshare.com/s/...",
                }
            ), 400

        password = request.args.get("pwd", "")
        logging.info(f"API request for URL: {url}")

        # Fetch file data
        link_data = await fetch_download_link(url, password)

        # Check if error occurred
        if isinstance(link_data, dict) and "error" in link_data:
            status_code = 400 if link_data.get("requires_password") else 500
            return jsonify(
                {
                    "status": "error",
                    "url": url,
                    "error": link_data["error"],
                    "errno": link_data.get("errno"),
                    "message": link_data.get("message", ""),
                    "requires_password": link_data.get("requires_password", False),
                }
            ), status_code

        # Format file information
        if link_data:
            tasks = [format_file_info(item) for item in link_data]
            formatted_files = await asyncio.gather(*tasks)

            return jsonify(
                {
                    "status": "success",
                    "url": url,
                    "files": formatted_files,
                    "total_files": len(formatted_files),
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )
        else:
            return jsonify(
                {"status": "error", "message": "No files found", "url": url}
            ), 404

    except Exception as e:
        logging.error(f"API error: {e}", exc_info=True)
        return jsonify(
            {"status": "error", "message": str(e), "url": request.args.get("url", "")}
        ), 500


@app.route("/api2", methods=["GET"])
async def api2():
    """Alternative API endpoint - with direct download links"""
    try:
        url = request.args.get("url")
        if not url:
            return jsonify(
                {
                    "status": "error",
                    "message": "Missing required parameter: url",
                    "example": "/api2?url=https://teraboxshare.com/s/...",
                }
            ), 400

        logging.info(f"API2 request for URL: {url}")

        # Fetch file data with direct links
        link_data = await fetch_direct_links(url)

        # Check if error occurred
        if isinstance(link_data, dict) and "error" in link_data:
            return jsonify(
                {
                    "status": "error",
                    "url": url,
                    "error": link_data["error"],
                    "errno": link_data.get("errno"),
                }
            ), 500

        if link_data:
            return jsonify(
                {
                    "status": "success",
                    "url": url,
                    "files": link_data,
                    "total_files": len(link_data),
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )
        else:
            return jsonify(
                {"status": "error", "message": "No files found", "url": url}
            ), 404

    except Exception as e:
        logging.error(f"API2 error: {e}", exc_info=True)
        return jsonify(
            {"status": "error", "message": str(e), "url": request.args.get("url", "")}
        ), 500


@app.route("/help", methods=["GET"])
def help_page():
    """Help and documentation endpoint"""
    return jsonify(
        {
            "TeraBox API Documentation": {
                "version": "2.0",
                "description": "Extract file information from TeraBox share links",
                "Endpoints": {
                    "/api": {
                        "method": "GET",
                        "description": "Fetch file information",
                        "parameters": {
                            "url": "Required - TeraBox share link",
                            "pwd": "Optional - Password for protected links",
                        },
                        "example": "/api?url=https://teraboxshare.com/s/1ABC...",
                    },
                    "/api2": {
                        "method": "GET",
                        "description": "Fetch files with direct download links",
                        "parameters": {"url": "Required - TeraBox share link"},
                        "example": "/api2?url=https://teraboxshare.com/s/1ABC...",
                    },
                },
                "Error Codes": {
                    "0": "Success",
                    "-1": "General error",
                    "400141": "Verification required (password/captcha)",
                },
                "Response Format": {
                    "success": {
                        "status": "success",
                        "url": "The requested URL",
                        "files": "Array of file objects",
                        "total_files": "Number of files",
                        "timestamp": "ISO timestamp",
                    },
                    "error": {
                        "status": "error",
                        "message": "Error description",
                        "errno": "Error code",
                    },
                },
                "Notes": [
                    "Cookies must be updated regularly (they expire)",
                    "Links requiring passwords need pwd parameter",
                    "Some links may require captcha verification",
                    "Rate limiting may apply",
                ],
                "Contact": "@Saahiyo",
            }
        }
    )


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
