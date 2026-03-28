import importlib.util
import threading
import time
import os

def loadScraper(path):
    spec = importlib.util.spec_from_file_location("scraper", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def runScraperLoop(path):
    mod = loadScraper(path)
    lastMtime = os.path.getmtime(path)
    interval = getattr(mod, "interval", 3600)

    while True:
        try:
            currentMtime = os.path.getmtime(path)
            if currentMtime != lastMtime:
                print(f"[scrapers] Reloading {os.path.basename(path)}")
                mod = loadScraper(path)
                lastMtime = currentMtime
                interval = getattr(mod, "interval", 3600)

            print(f"[scrapers] Running {os.path.basename(path)}")
            mod.run()
        except Exception as e:
            print(f"[scrapers] Error in {os.path.basename(path)}: {e}")

        time.sleep(interval)

def startScrapers():
    scraperDir = "./scrapers"
    os.makedirs(scraperDir, exist_ok=True)

    for filename in os.listdir(scraperDir):
        if filename.endswith(".py") and not filename.startswith("_"):
            path = os.path.join(scraperDir, filename)
            t = threading.Thread(target=runScraperLoop, args=(path,), daemon=True)
            t.start()
            print(f"[runScrapers.py] Started {filename}")