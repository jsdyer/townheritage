#!/usr/bin/env python3
"""Bounded manual Europeana capture. Never save raw API responses."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit, parse_qsl
from urllib.request import Request, build_opener, HTTPRedirectHandler
ROOT = Path(__file__).resolve().parents[1]
ENDPOINT = "https://api.europeana.eu/record/v2/search.json"
MAX_BYTES = 8_000_000


def strings(value):
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, list):
        return [s for v in value for s in strings(v)]
    if isinstance(value, dict):
        return [s for v in value.values() for s in strings(v)]
    return []


def safe_url(value, key=""):
    if not isinstance(value, str) or len(value) > 4000 or (key and key in value):
        return ""
    try:
        p = urlsplit(value)
        if p.scheme != "https" or not p.hostname or p.username or p.password or any(c.isspace() for c in value):
            return ""
        if any(k.lower() in {"wskey", "apikey", "api_key", "access_token", "token", "key"} for k, _ in parse_qsl(p.query)):
            return ""
        return value
    except ValueError:
        return ""


def right_label(uri):
    p = urlsplit(uri)
    if p.scheme not in {"http", "https"} or p.username or p.password or p.hostname not in {"creativecommons.org", "www.creativecommons.org"}:
        return None
    path = p.path.rstrip("/").lower()
    if path == "/publicdomain/mark/1.0":
        return "Public Domain Mark"
    if path == "/publicdomain/zero/1.0":
        return "CC0"
    m = re.fullmatch(r"/licenses/(by|by-sa)/(1\.0|2\.0|2\.5|3\.0|4\.0)(?:/[a-z]{2})?", path)
    return f"CC {m[1].upper()} {m[2]}" if m else None


def normalize(item, key=""):
    identity = item.get("id", "")
    if not isinstance(identity, str) or not re.fullmatch(r"/[A-Za-z0-9_.-]+/[A-Za-z0-9_./~-]+", identity):
        return None
    rights = []
    for uri in strings(item.get("rights")):
        label = right_label(uri)
        if not label:
            return None
        rights.append({"label":label, "url":"https://creativecommons.org" + urlsplit(uri).path})
    if not rights:
        return None
    def text(field, default=""):
        return strings(item.get(field))[:20] or ([default] if default else [])
    def url(field):
        return next((u for v in strings(item.get(field)) if (u := safe_url(v, key))), "")
    years = sorted(set(int(v) for v in text("year") if re.fullmatch(r"\d{4}", v) and 1 <= int(v) <= 2100))
    record = {
        "id":identity, "title":text("title", "Untitled record")[0],
        "creators":text("dcCreator"), "description":text("dcDescription"),
        "institutions":text("dataProvider", "Institution not supplied"),
        "aggregators":text("provider"), "providerCountries":text("country"),
        "places":text("dctermsSpatial"), "dateText":text("dcDate"), "years":years,
        "type":str(item.get("type", "IMAGE")), "rights":rights,
        "thumbnail":url("edmPreview"), "original":url("edmIsShownBy"),
        "source":url("edmIsShownAt"), "europeana":"https://www.europeana.eu/item" + identity,
        "collections":[]
    }
    if key and key in json.dumps(record, ensure_ascii=False):
        raise ValueError("Credential material found in record fields; capture stopped")
    return record


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("Unexpected API redirect; no credentials forwarded")


def fetch(query, rows, key):
    params = {"query":query,"qf":"TYPE:IMAGE","reusability":"open","thumbnail":"true","profile":"rich","rows":rows}
    request = Request(ENDPOINT + "?" + urlencode(params), headers={"X-Api-Key":key,"Accept":"application/json","User-Agent":"TownHeritagePrototype/1.0 (+https://github.com/jsdyer/townheritage)"})
    try:
        with build_opener(NoRedirect()).open(request, timeout=35) as response:
            payload = response.read(MAX_BYTES + 1)
            if len(payload) > MAX_BYTES:
                raise ValueError("API response exceeded the capture limit")
            data = json.loads(payload)
    except HTTPError as exc:
        raise ValueError(f"Europeana returned HTTP {exc.code}; previous deployment preserved") from None
    except (URLError, TimeoutError, json.JSONDecodeError):
        raise ValueError("Europeana could not provide valid JSON; previous deployment preserved") from None
    if not isinstance(data, dict) or data.get("success") is not True or not isinstance(data.get("items", []), list):
        raise ValueError("Europeana reported an unsuccessful or malformed search")
    return data


def validate_config(config):
    collections = config.get("collections", [])
    if not isinstance(collections, list) or not 1 <= len(collections) <= 12:
        raise ValueError("Configure 1–12 collections per manual capture")
    ids = set()
    for c in collections:
        if not isinstance(c, dict) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", c.get("id", "")) or c["id"] in ids:
            raise ValueError("Each collection needs a unique lowercase slug")
        ids.add(c["id"])
        if not all(isinstance(c.get(k), str) and 1 <= len(c[k]) <= 500 for k in ("title", "query", "note")):
            raise ValueError("Each collection needs title, query and note (1–500 characters)")
    rows = config.get("rows_per_collection", 60)
    interval = config.get("request_interval_seconds", 2)
    if type(rows) is not int or not 1 <= rows <= 100 or not isinstance(interval, (int, float)) or not 2 <= interval <= 30:
        raise ValueError("Rows must be 1–100; request spacing must be 2–30 seconds")
    return collections, rows, interval


def collect(config, key, fetcher=fetch, sleeper=time.sleep):
    collections, rows, interval = validate_config(config)
    records, captures = {}, []
    for index, collection in enumerate(collections):
        if index:
            sleeper(interval)
        payload = fetcher(collection["query"], rows, key)
        kept = 0
        for item in payload.get("items", []):
            if not isinstance(item, dict):
                continue
            record = normalize(item, key)
            if record:
                existing = records.setdefault(record["id"], record)
                if collection["id"] not in existing["collections"]:
                    existing["collections"].append(collection["id"])
                    kept += 1
        total = payload.get("totalResults", 0)
        if type(total) is not int or total < 0:
            raise ValueError("Invalid totalResults")
        captures.append({**collection,"totalMatches":total,"returned":len(payload.get("items", [])),"included":kept})
        print(f"Captured {collection['id']}: {kept} reusable records")
    if not records:
        raise ValueError("No reusable records passed validation; previous deployment preserved")
    result = {"version":1,"capturedAt":datetime.now(timezone.utc).isoformat(),"source":"Europeana Search API","mode":"manual-review-prototype","filters":{"type":"IMAGE","reusability":"open","thumbnail":True},"requests":len(collections),"rowsPerCollection":rows,"collections":captures,"records":list(records.values())}
    if key and key in json.dumps(result, ensure_ascii=False):
        raise ValueError("Credential detected in output; nothing written")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=ROOT / "config/collections.json")
    parser.add_argument("--output", type=Path, default=ROOT / "data/europeana.json")
    parser.add_argument("--query", default="", help="Append one custom query to this capture")
    args = parser.parse_args()
    key = os.environ.get("EUROPEANA_API_KEY", "").strip()
    if not key:
        raise ValueError("Set Actions secret EUROPEANA_API_KEY before collecting")
    config = json.loads(args.config.read_text())
    if args.query:
        config["collections"].append({"id":"custom-query","title":args.query[:80],"query":args.query,"note":"Custom keyword matches are not verified geographic identifications."})
    result = collect(config, key)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(".tmp")
    temporary.write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n")
    temporary.replace(args.output)
    print(f"Saved {len(result['records'])} unique records from {result['requests']} real API requests")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError) as exc:
        raise SystemExit(str(exc)) from None
