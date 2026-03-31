from http.server import HTTPServer, BaseHTTPRequestHandler
import os
import json
import subprocess
from pathlib import Path
from PIL import Image
import requests # the location of this exact import fixes a deadlock somehow, python is fucking awful :sob:
from runScrapers import startScrapers
startScrapers()

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

serverVersion = "13w26b vanilla"

imagesRoute   = "/api/" + config["imagesPath"] + "/"
metadataRoute = "/api/metadata/"

def search(query, searchType, limitTo="all"):
    results = []
    foldersToCheck = []
    if limitTo != "all":
        limitPath = config["imagesPath"] + "/" + limitTo
        if os.path.exists(limitPath) and os.path.isdir(limitPath):
            foldersToCheck.append(limitPath)
    else:
        for entry in os.scandir(config["imagesPath"]):
            if entry.is_dir():
                foldersToCheck.append(entry.path)
    
    for folder in foldersToCheck:
        folder_result = {"type": "folder", "name": folder.split("/")[-1], "content": []}
        results.append(folder_result)
        for entry in os.scandir(folder):
            if entry.is_file() and entry.name.lower().endswith(IMAGE_EXTS + VIDEO_EXTS):
                entryUrl = os.path.relpath(entry.path, config["imagesPath"]).replace("\\", "/")
                md = getImageMD("/" + entryUrl)
                match = False
                if searchType in ("name", "all") and query.lower() in md.get("name", "").lower():
                    match = True
                elif searchType in ("description", "all") and query.lower() in md.get("description", "").lower():
                    match = True
                elif searchType in ("artist", "all") and query.lower() in md.get("artist", "").lower():
                    match = True
                elif searchType in ("tags", "all") and any(query.lower() in tag.lower() for tag in md.get("tags", [])):
                    match = True
                
                if match:
                    ext = os.path.splitext(entry.name)[1].lstrip(".") or "file"
                    folder_result["content"].append({
                        "name": entry.name,
                        "type": ext
                    })
    results = [r for r in results if r["content"]]
    
    return results

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


RAW_BASES = [
    "https://raw.githubusercontent.com/Pugsby/ivsPluginRepo/main/ivsPluginRepo",
    "https://raw.githubusercontent.com/Pugsby/ivsPluginRepo/main",
]

SCRAPER_SETTINGS = "scraperSettings.json"


def parse_plugin_version(content):
    patterns = [
        r'__version__\s*=\s*["\']([^"\']+)["\']',
        r'VERSION\s*=\s*["\']([^"\']+)["\']',
        r'version\s*=\s*["\']([^"\']+)["\']',
    ]
    for pat in patterns:
        m = re.search(pat, content)
        if m:
            return m.group(1)
    return None


def get_local_plugin_version(fname):
    path = os.path.join('scrapers', fname)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return parse_plugin_version(f.read())
    except Exception:
        return None


def load_scraper_settings():
    try:
        with open(SCRAPER_SETTINGS, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def client_is_local(handler):
    try:
        ip = handler.client_address[0]
    except Exception:
        return False
    return ip == '127.0.0.1' or ip == '::1'

def save_scraper_settings(data):
    with open(SCRAPER_SETTINGS, "w") as f:
        json.dump(data, f, indent=4)

def fetch_remote(path):
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
            if self.path == "/api/serverVersion":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(bytes(json.dumps({"version": serverVersion}), 'utf-8'))
                return
            if self.path.startswith("/api/remotePlugins"):
                if not client_is_local(self):
                    sendError(self, 403, "Plugins are restricted to localhost")
                    return
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
                    remote_version = p.get("version")
                    local_version = get_local_plugin_version(fname) if installed else None
                    update_available = bool(installed and remote_version and local_version and remote_version != local_version)

                    # if there's no version metadata, allow manual update in UI for installed plugin
                    if installed and not remote_version:
                        update_available = True

                    plugins.append({
                        "file": fname,
                        "name": p.get("name"),
                        "description": p.get("description"),
                        "author": p.get("author"),
                        "installed": installed,
                        "config": cfg,
                        "thumbnail": "/api/pluginThumb?path=" + quote_plus(thumb),
                        "remoteVersion": remote_version,
                        "localVersion": local_version,
                        "updateAvailable": update_available,
                    })

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(bytes(json.dumps({"serverPlugins": plugins}), 'utf-8'))
                return

            elif self.path.startswith("/api/pluginThumb"):
                if not client_is_local(self):
                    sendError(self, 403, "Plugins are restricted to localhost")
                    return
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

            elif self.path.startswith("/api/pluginConfig"):
                if not client_is_local(self):
                    sendError(self, 403, "Plugins are restricted to localhost")
                    return
                parsed = urlparse(self.path)
                qs = parse_qs(parsed.query)
                fname = qs.get('file', [''])[0]
                if not fname:
                    sendError(self, 400, "Missing file parameter")
                    return
                settings = load_scraper_settings()
                cfg = settings.get(fname)
                if cfg is None:
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
                # sendError(self, 501, self.path + " is not yet implemented.")
                # self.path IS implemented :surprisedCat:
                # get the search query from url params "query" and "type"
                query = parse_qs(urlparse(self.path).query).get("q", [""])[0].lower()
                searchType = parse_qs(urlparse(self.path).query).get("type", [""])[0].lower()
                supportedQueryTypes = ["name", "tags", "artist", "description", "all"]
                limitTo = parse_qs(urlparse(self.path).query).get("limitTo", ["all"])[0].lower()
                if searchType not in supportedQueryTypes:
                    sendError(self, 400, "Invalid search type")
                    return
                print("Searching for '" + query + "' in " + searchType)
                results = search(query, searchType, limitTo)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(bytes(json.dumps(results), 'utf-8'))
                return

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

            elif self.path.startswith("/api/error/"):
                code = self.path[len("/api/error/"):]
                sendError(self, int(code), "Nothing is wrong. " + code)

            else:
                sendError(self, 501, "Unknown API endpoint " + self.path)
            
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
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length).decode('utf-8') if length > 0 else ''
        try:
            data = json.loads(body) if body else {}
        except Exception:
            data = {}

        if self.path.startswith('/api/installPlugin'):
            if not client_is_local(self):
                sendError(self, 403, "Plugins are restricted to localhost")
                return
            fname = data.get('file')
            if not fname:
                sendError(self, 400, 'Missing file')
                return
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
            settings = load_scraper_settings()
            if fname not in settings:
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

        if self.path.startswith('/api/updatePlugin'):
            if not client_is_local(self):
                sendError(self, 403, "Plugins are restricted to localhost")
                return
            fname = data.get('file')
            if not fname:
                sendError(self, 400, 'Missing file')
                return
            target = os.path.join('scrapers', fname)
            if not os.path.exists(target):
                sendError(self, 404, 'Plugin not installed')
                return
            r = fetch_remote('server/' + fname)
            if not r:
                sendError(self, 502, 'Could not fetch plugin source')
                return
            try:
                with open(target, 'wb') as f:
                    f.write(r.content)
            except Exception as e:
                sendError(self, 500, f'Could not write plugin: {e}')
                return
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(bytes(json.dumps({'ok': True, 'updated': fname}), 'utf-8'))
            return

        if self.path.startswith('/api/pluginConfig'):
            if not client_is_local(self):
                sendError(self, 403, "Plugins are restricted to localhost")
                return
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