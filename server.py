from http.server import HTTPServer, BaseHTTPRequestHandler
import os
import json
import subprocess
from pathlib import Path
from PIL import Image
from runScrapers import startScrapers
startScrapers()

import requests
from urllib.parse import unquote, quote_plus, urlparse, parse_qs

config = {
    "port": 8282,
    "imagesPath": "images", # Bug: If this is ANYTHING other than images, it will break
    "branding": "Image Viewer"
}

jsonPlaceholder = {
    "name": "unknown",
    "description": "No Description.",
    "tags": ["untagged"],
    "artist": "Unknown"
}

IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp")
VIDEO_EXTS = (".mp4", ".webm", ".ogg")
THUMB_HEIGHT = 512

imagesRoute   = "/api/" + config["imagesPath"] + "/"
metadataRoute = "/api/metadata/"

def sendError(self, code, note):
    self.send_response(code)
    self.end_headers()
    errorPage = open("error.html").read().replace("[ERRORCODE]", str(code)).replace("[NOTE]", note)
    self.wfile.write(bytes(errorPage, 'utf-8'))

def getImageMD(path):
    relative = path.lstrip("/")
    baseWithExt = relative.rsplit(".", 1)[0]
    baseNoExt = baseWithExt.rsplit(".", 1)[0]
    candidates = [
        config["imagesPath"] + "/" + baseWithExt + ".json",
        config["imagesPath"] + "/" + baseNoExt + ".json",
    ]

    data = {}
    resolvedPath = None

    for candidate in candidates:
        print(candidate)
        if os.path.exists(candidate):
            resolvedPath = candidate
            break

    if not resolvedPath:
        folderPath = config["imagesPath"] + "/" + str(Path(baseNoExt).parent)
        folderCandidate = folderPath + ".json"
        print(folderCandidate)
        if os.path.exists(folderCandidate):
            resolvedPath = folderCandidate

    if resolvedPath:
        with open(resolvedPath, "r") as f:
            try:
                print(resolvedPath)
                loaded = json.load(f)
                data = loaded if isinstance(loaded, dict) else {}
            except (json.JSONDecodeError, ValueError):
                data = {}

    fileName = Path(baseNoExt).name

    defaults = jsonPlaceholder.copy()
    defaults["name"] = fileName

    for key, value in defaults.items():
        if key not in data:
            data[key] = value

    return data

def jsonLs(path):
    items = []
    for entry in sorted(os.scandir(path), key=lambda e: (not e.is_dir(), e.name)):
        if entry.is_dir():
            items.append({
                "name": entry.name,
                "type": "folder",
                "content": jsonLs(entry.path)
            })
        else:
            ext = os.path.splitext(entry.name)[1].lstrip(".") or "file"
            items.append({
                "name": entry.name,
                "type": ext
            })
    return items


# Plugin repo raw bases to try (listing.json is under ivsPluginRepo/listing.json)
RAW_BASES = [
    "https://raw.githubusercontent.com/Pugsby/ivsPluginRepo/main/ivsPluginRepo",
    "https://raw.githubusercontent.com/Pugsby/ivsPluginRepo/main",
]

SCRAPER_SETTINGS = "scraperSettings.json"

def load_scraper_settings():
    try:
        with open(SCRAPER_SETTINGS, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def save_scraper_settings(data):
    with open(SCRAPER_SETTINGS, "w") as f:
        json.dump(data, f, indent=4)

def fetch_remote(path):
    # Try each base until we get a 200
    for base in RAW_BASES:
        url = base.rstrip("/") + "/" + path.lstrip("/")
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                return r
        except Exception:
            continue
    return None

class Serv(BaseHTTPRequestHandler):

    def do_GET(self):
        if self.path.startswith("/api"):
            # Remote plugins listing
            if self.path.startswith("/api/remotePlugins"):
                r = fetch_remote("listing.json")
                if not r:
                    sendError(self, 502, "Could not fetch plugin listing from remote repo")
                    return
                try:
                    listing = r.json()
                except Exception:
                    sendError(self, 502, "Invalid listing.json from remote repo")
                    return

                settings = load_scraper_settings()
                plugins = []
                for p in listing.get("serverPlugins", []):
                    fname = p.get("file")
                    installed = os.path.exists(os.path.join("scrapers", fname))
                    cfg = settings.get(fname, p.get("defaultConfig", {}))
                    thumb = p.get("image", "")
                    plugins.append({
                        "file": fname,
                        "name": p.get("name"),
                        "description": p.get("description"),
                        "author": p.get("author"),
                        "installed": installed,
                        "config": cfg,
                        "thumbnail": "/api/pluginThumb?path=" + quote_plus(thumb)
                    })

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(bytes(json.dumps({"serverPlugins": plugins}), 'utf-8'))
                return

            # Proxy a plugin thumbnail from remote repo
            elif self.path.startswith("/api/pluginThumb"):
                # parse ?path=...
                parsed = urlparse(self.path)
                qs = parse_qs(parsed.query)
                path = qs.get('path', [''])[0]
                path = unquote(path)
                if not path:
                    sendError(self, 400, "Missing path")
                    return
                r = fetch_remote(path)
                if not r:
                    sendError(self, 502, "Could not fetch thumbnail")
                    return
                content_type = r.headers.get('Content-Type', 'application/octet-stream')
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.end_headers()
                self.wfile.write(r.content)
                return

            # Get plugin config for installed plugin
            elif self.path.startswith("/api/pluginConfig"):
                parsed = urlparse(self.path)
                qs = parse_qs(parsed.query)
                fname = qs.get('file', [''])[0]
                if not fname:
                    sendError(self, 400, "Missing file parameter")
                    return
                settings = load_scraper_settings()
                cfg = settings.get(fname)
                if cfg is None:
                    # return empty or default
                    self.send_response(404)
                    self.end_headers()
                    self.wfile.write(bytes(json.dumps({}), 'utf-8'))
                    return
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(bytes(json.dumps(cfg), 'utf-8'))
                return
            if self.path.startswith("/api/search"):
                sendError(self, 501, self.path + " is not yet implemented.")

            elif self.path.startswith(imagesRoute):
                rawPath = self.path[len(imagesRoute):]

                queryString = ""
                if "?" in rawPath:
                    rawPath, queryString = rawPath.split("?", 1)

                if queryString == "thumbnail":
                    cacheDir = "./cache"
                    os.makedirs(cacheDir, exist_ok=True)
                    cacheFilename = rawPath.replace("/", "_") + ".thumb.jpg"
                    cachePath = os.path.join(cacheDir, cacheFilename)

                    if not os.path.exists(cachePath):
                        sourcePath = config["imagesPath"] + "/" + rawPath
                        lower = rawPath.lower()

                        if lower.endswith(VIDEO_EXTS):
                            subprocess.run([
                                "ffmpeg", "-i", sourcePath,
                                "-vframes", "1",
                                "-vf", f"scale=-1:{THUMB_HEIGHT}",
                                "-q:v", "2",
                                cachePath
                            ], check=True, capture_output=True)

                        elif lower.endswith(IMAGE_EXTS):
                            with Image.open(sourcePath) as img:
                                w, h = img.size
                                new_w = max(1, int(w * THUMB_HEIGHT / h))
                                img = img.convert("RGB")
                                img = img.resize((new_w, THUMB_HEIGHT), Image.LANCZOS)
                                img.save(cachePath, "JPEG", quality=85)

                    with open(cachePath, "rb") as f:
                        fileToOpen = f.read()
                    self.send_response(200)
                    self.send_header("Content-Type", "image/jpeg")
                    self.end_headers()
                    self.wfile.write(bytes(fileToOpen))
                    return

                else:
                    with open(config["imagesPath"] + "/" + rawPath, "rb") as f:
                        fileToOpen = f.read()

                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.end_headers()
                self.wfile.write(bytes(fileToOpen))

            elif self.path.startswith(metadataRoute):
                fileToOpen = getImageMD(self.path[len(metadataRoute):])
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(bytes(json.dumps(fileToOpen), 'utf-8'))

            elif self.path.startswith("/api/lsImages"):
                fileToOpen = jsonLs(config["imagesPath"])
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(bytes(json.dumps(fileToOpen), 'utf-8'))

            return

        filePath = "/html" + self.path

        if filePath == '/html/':
            filePath = '/html/index.html'
        try:
            with open(filePath[1:]) as f:
                fileToOpen = f.read()
            if filePath.endswith(".html"):
                fileToOpen = fileToOpen.replace("[BRANDING]", config["branding"])
            self.send_response(200)
            self.end_headers()
            self.wfile.write(bytes(fileToOpen, 'utf-8'))
        except:
            sendError(self, 404, filePath + " not found.")

    def do_POST(self):
        # Simple JSON body parser
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length).decode('utf-8') if length > 0 else ''
        try:
            data = json.loads(body) if body else {}
        except Exception:
            data = {}

        if self.path.startswith('/api/installPlugin'):
            fname = data.get('file')
            if not fname:
                sendError(self, 400, 'Missing file')
                return
            # fetch plugin source from remote server folder
            r = fetch_remote('server/' + fname)
            if not r:
                sendError(self, 502, 'Could not fetch plugin source')
                return
            os.makedirs('scrapers', exist_ok=True)
            target = os.path.join('scrapers', fname)
            try:
                with open(target, 'wb') as f:
                    f.write(r.content)
            except Exception as e:
                sendError(self, 500, f'Could not write plugin: {e}')
                return
            # Optionally add default config
            settings = load_scraper_settings()
            if fname not in settings:
                # try to fetch listing to find default config
                lr = fetch_remote('listing.json')
                if lr:
                    try:
                        listing = lr.json()
                        for p in listing.get('serverPlugins', []):
                            if p.get('file') == fname:
                                settings[fname] = p.get('defaultConfig', {})
                    except Exception:
                        pass
                save_scraper_settings(settings)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(bytes(json.dumps({'ok': True, 'installed': fname}), 'utf-8'))
            return

        if self.path.startswith('/api/pluginConfig'):
            fname = data.get('file')
            cfg = data.get('config')
            if not fname or cfg is None:
                sendError(self, 400, 'Missing file or config')
                return
            settings = load_scraper_settings()
            settings[fname] = cfg
            try:
                save_scraper_settings(settings)
            except Exception as e:
                sendError(self, 500, f'Could not save settings: {e}')
                return
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(bytes(json.dumps({'ok': True}), 'utf-8'))
            return

        # unknown POST
        sendError(self, 404, 'Unknown POST ' + self.path)

imagesAlreadyExisted = os.path.exists(config["imagesPath"])
os.makedirs(config["imagesPath"], exist_ok=True)
if not imagesAlreadyExisted:
    os.makedirs(config["imagesPath"] + "/collection", exist_ok=True)
os.makedirs("./cache", exist_ok=True)

httpd = HTTPServer(('0.0.0.0', config["port"]), Serv)
print("Server opened on port " + str(config["port"]))
httpd.serve_forever()

# cause a chud like me cries for a single fry
# and a chud like me really wants to fly
# cause a chud like me really needs to rise
# and a chud like me really wants to...

# cause a chud like me sometimes needs to cry
# and a chud like me wants to reach the sky
# and a chud like me really needs to...
# and a chud like me really wants to...
# and a chud like me will never get to...