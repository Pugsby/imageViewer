import importlib.util
import threading
import time
import os
import json
import re
import sys
disableScrapers = False # use this when you don't wanna ratelimit yourself during development, (or when a scraper fucks up the server somehow)
if disableScrapers:
    print("! Scrapers are disabled. Turn them back on when pushing to the repo !")

def _camel_to_upper_snake(s: str) -> str:
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', s)
    s2 = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1)
    return s2.upper()


def inject_settings(mod, settings: dict):
    if not settings:
        return
    for k, v in settings.items():
        try:
            setattr(mod, k, v)
        except Exception:
            pass
        try:
            setattr(mod, _camel_to_upper_snake(k), v)
        except Exception:
            pass


def loadScraper(path, settings=None):
    base = os.path.splitext(os.path.basename(path))[0]
    module_name = f"scraper_{base}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    inject_settings(mod, settings or {})
    return mod

def runScraperLoop(path, settings=None):
    mod = loadScraper(path, settings)
    lastMtime = os.path.getmtime(path)
    interval = getattr(mod, "interval", 3600)

    while True:
        try:
            currentMtime = os.path.getmtime(path)
            if currentMtime != lastMtime:
                print(f"[scrapers] Reloading {os.path.basename(path)}")
                mod = loadScraper(path, settings)
                lastMtime = currentMtime
                interval = getattr(mod, "interval", 3600)

            print(f"[scrapers] Running {os.path.basename(path)}")
            mod.run()
        except Exception as e:
            print(f"[scrapers] Error in {os.path.basename(path)}: {e}")

        time.sleep(interval)

def startScrapers():
    if disableScrapers:
        return
    scraperDir = "./scrapers"
    os.makedirs(scraperDir, exist_ok=True)
    config_path = os.path.join('.', 'scraperSettings.json')
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except Exception:
        config = {}

    for filename in os.listdir(scraperDir):
        if filename.endswith(".py") and not filename.startswith("_"):
            path = os.path.join(scraperDir, filename)
            settings = config.get(filename, {})
            t = threading.Thread(target=runScraperLoop, args=(path, settings), daemon=True)
            t.start()
            print(f"[runScrapers.py] Started {filename}")