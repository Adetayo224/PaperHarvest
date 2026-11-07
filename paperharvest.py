#!/usr/bin/env python3
"""
PaperHarvest: download recent open access research papers on any topic.

Run it inside any folder:
    python3 paperharvest.py
A page opens in your browser. Type your name, your research topic, how many
papers you want and the earliest year. Papers are saved in a "Papers" folder
next to where you launched it.

No installs needed. Uses only the Python standard library and the free
OpenAlex index (covers IEEE, Elsevier, Springer, MDPI, Wiley, arXiv and more).
Only legally open access PDFs are downloaded.
"""

import csv
import datetime as dt
import json
import os
import re
import sys
import threading
import time
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
WORK_DIR = os.getcwd()
PORT = int(os.environ.get("PAPERHARVEST_PORT", "8765"))
API = "https://api.openalex.org/works"
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

JOB = {"running": False, "stop": False, "done": 0, "target": 0, "checked": 0,
       "log": [], "folder": "", "finished": False, "message": ""}
LOCK = threading.Lock()


# ---------------------------------------------------------------- helpers
def log(msg, kind="info"):
    with LOCK:
        JOB["log"].append({"t": time.strftime("%H:%M:%S"), "msg": msg, "kind": kind})
        JOB["log"] = JOB["log"][-400:]


def clean_name(text, limit=110):
    text = re.sub(r"<[^>]+>", "", text or "Untitled")
    text = re.sub(r"[^A-Za-z0-9 ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()[:limit].strip() or "Untitled"


def norm(t):
    return re.sub(r"[^a-z0-9]", "", (t or "").lower())


def http_get(url, timeout=40, accept="application/json"):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def search(topic, from_year, page, peer_only):
    types = "article|review" if peer_only else "article|review|preprint"
    params = {
        "search": topic,
        "filter": f"from_publication_date:{from_year}-01-01,is_oa:true,type:{types}",
        "per_page": 50,
        "page": page,
        "select": "id,doi,display_name,publication_year,cited_by_count,authorships,"
                  "primary_location,best_oa_location,locations,type",
    }
    url = API + "?" + urllib.parse.urlencode(params)
    for attempt in range(3):
        try:
            return json.loads(http_get(url)).get("results", [])
        except Exception:
            time.sleep(2 * (attempt + 1))
    return []


def pdf_links(work):
    links = []
    for loc in [work.get("best_oa_location")] + (work.get("locations") or []):
        if loc and loc.get("pdf_url") and loc["pdf_url"] not in links:
            links.append(loc["pdf_url"])
    for loc in work.get("locations") or []:
        m = re.search(r"arxiv\.org/abs/([\w./]+)", (loc or {}).get("landing_page_url") or "")
        if m:
            links.append(f"https://arxiv.org/pdf/{m.group(1)}")
    return links


def fetch_pdf(url, path):
    try:
        data = http_get(url, timeout=60, accept="application/pdf,*/*")
        if data[:5] == b"%PDF-" and len(data) > 50_000:
            with open(path, "wb") as f:
                f.write(data)
            return True
    except Exception:
        pass
    return False


# ---------------------------------------------------------------- worker
def run_job(name, topic, count, from_year, peer_only):
    folder = os.path.join(WORK_DIR, "Papers", clean_name(topic, 60))
    os.makedirs(folder, exist_ok=True)
    with LOCK:
        JOB.update(running=True, stop=False, done=0, target=count, checked=0,
                   log=[], folder=folder, finished=False, message="")
    log(f"Hello {name}. Looking for papers on \"{topic}\" from {from_year} onward.")
    log(f"Saving to {folder}")

    seen, rows, page = set(), [], 1
    while JOB["done"] < count and not JOB["stop"] and page <= 40:
        results = search(topic, from_year, page, peer_only)
        if not results:
            break
        for w in results:
            if JOB["done"] >= count or JOB["stop"]:
                break
            title = w.get("display_name") or ""
            key = norm(title)
            if not title or key in seen:
                continue
            seen.add(key)
            with LOCK:
                JOB["checked"] += 1
            num = JOB["done"] + 1
            fname = f"{num:03d} {w.get('publication_year')} {clean_name(title)}.pdf"
            path = os.path.join(folder, fname)
            for url in pdf_links(w):
                if fetch_pdf(url, path):
                    src = ((w.get("primary_location") or {}).get("source") or {})
                    rows.append({
                        "No": num, "Title": title,
                        "Authors": ", ".join(a["author"]["display_name"]
                                             for a in (w.get("authorships") or [])[:6]),
                        "Year": w.get("publication_year"),
                        "Venue": src.get("display_name", ""),
                        "Type": w.get("type"), "Citations": w.get("cited_by_count"),
                        "DOI": w.get("doi") or "", "File": fname,
                    })
                    with LOCK:
                        JOB["done"] += 1
                    log(f"{title} ({w.get('publication_year')})", "ok")
                    break
        page += 1

    if rows:
        with open(os.path.join(folder, "Paper List.csv"), "w", newline="", encoding="utf-8") as f:
            wr = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            wr.writeheader()
            wr.writerows(rows)

    msg = ("Stopped. " if JOB["stop"] else "Finished. ") + \
          f"{JOB['done']} of {count} papers saved."
    if JOB["done"] < count and not JOB["stop"]:
        msg += " No more open access papers matched; try a broader topic or earlier year."
    log(msg, "done")
    with LOCK:
        JOB.update(running=False, finished=True, message=msg)


# ---------------------------------------------------------------- server
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            with open(os.path.join(HERE, "index.html"), "rb") as f:
                self.send(200, f.read(), "text/html; charset=utf-8")
        elif self.path.startswith("/api/status"):
            with LOCK:
                self.send(200, json.dumps(JOB))
        else:
            self.send(404, "{}")

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            body = {}
        if self.path == "/api/start":
            if JOB["running"]:
                return self.send(409, json.dumps({"error": "A download is already running."}))
            topic = (body.get("topic") or "").strip()
            if not topic:
                return self.send(400, json.dumps({"error": "Please enter a research topic."}))
            name = (body.get("name") or "Researcher").strip()
            count = max(1, min(int(body.get("count") or 20), 500))
            year = max(1900, min(int(body.get("from_year") or dt.date.today().year - 5),
                                 dt.date.today().year))
            threading.Thread(target=run_job,
                             args=(name, topic, count, year, bool(body.get("peer_only"))),
                             daemon=True).start()
            self.send(200, json.dumps({"ok": True}))
        elif self.path == "/api/stop":
            JOB["stop"] = True
            self.send(200, json.dumps({"ok": True}))
        else:
            self.send(404, "{}")


def main():
    try:
        server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    except OSError:
        sys.exit(f"Port {PORT} is busy. Run: PAPERHARVEST_PORT=8800 python3 paperharvest.py")
    url = f"http://127.0.0.1:{PORT}"
    print(f"PaperHarvest is running at {url}")
    print(f"Papers will be saved under: {os.path.join(WORK_DIR, 'Papers')}")
    print("Press Ctrl+C to quit.")
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nBye.")


if __name__ == "__main__":
    main()
