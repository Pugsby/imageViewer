from http.server import HTTPServer, BaseHTTPRequestHandler
import os
import json
import subprocess
from pathlib import Path

config = {
    "port": 8282,
    "imagesPath": "images" # Bug: If this is ANYTHING other than images, it will break
}

jsonPlaceholder = {
    "name": "unknown",
    "description": "No Description.",
    "tags": ["untagged"],
    "artist": "Unknown"
}

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

class Serv(BaseHTTPRequestHandler):

    def do_GET(self):
        if self.path.startswith("/api"):
            if self.path.startswith("/api/search"):
                sendError(self, 501, self.path + " is not yet implemented.")

            elif self.path.startswith(imagesRoute):
                rawPath = self.path[len(imagesRoute):]

                queryString = ""
                if "?" in rawPath:
                    rawPath, queryString = rawPath.split("?", 1)

                if queryString == "thumbnail" and rawPath.lower().endswith((".mp4", ".webm", ".ogg")):
                    cacheDir = "./cache"
                    os.makedirs(cacheDir, exist_ok=True)

                    cacheFilename = rawPath.replace("/", "_") + ".jpg"
                    cachePath = os.path.join(cacheDir, cacheFilename)

                    if not os.path.exists(cachePath):
                        subprocess.run([
                            "ffmpeg", "-i", config["imagesPath"] + "/" + rawPath,
                            "-vframes", "1",
                            "-q:v", "2",
                            cachePath
                        ], check=True, capture_output=True)

                    with open(cachePath, "rb") as f:
                        fileToOpen = f.read()
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
            fileToOpen = open(filePath[1:]).read()
            self.send_response(200)
            self.end_headers()
            self.wfile.write(bytes(fileToOpen, 'utf-8'))
        except:
            sendError(self, 404, filePath + " not found.")

os.makedirs(config["imagesPath"], exist_ok=True)
os.makedirs(config["imagesPath"] + "/collection", exist_ok=True)
os.makedirs("./cache", exist_ok=True)

httpd = HTTPServer(('0.0.0.0', config["port"]), Serv)
print("Server opened on port " + str(config["port"]))
httpd.serve_forever()
