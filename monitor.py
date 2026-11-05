
import os
import json
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

TOPIC = os.environ["NTFY_TOPIC"]
STATE_FILE = Path("state.json")
FEEDS_FILE = Path("feeds.txt")

state = json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}
first_run = not bool(state)

def notify(title, link):
    url = "https://ntfy.sh/" + TOPIC
    request = urllib.request.Request(
        url,
        data=link.encode("utf-8"),
        headers={
            "Title": title[:200],
            "Click": link,
            "Priority": "high"
        },
        method="POST"
    )
    urllib.request.urlopen(request, timeout=20).read()

for feed in FEEDS_FILE.read_text().splitlines():
    feed = feed.strip()
    if not feed or feed.startswith("#"):
        continue

    try:
        request = urllib.request.Request(
            feed,
            headers={"User-Agent": "MediaMonitor/1.0"}
        )
        xml = urllib.request.urlopen(request, timeout=25).read()
        root = ET.fromstring(xml)

        entries = root.findall(".//item")
        if not entries:
            entries = root.findall(
                ".//{http://www.w3.org/2005/Atom}entry"
            )

        known = set(state.get(feed, []))
        current = []

        for entry in entries[:50]:
            title = entry.findtext("title") or entry.findtext(
                "{http://www.w3.org/2005/Atom}title"
            ) or "Nouvel article"

            link = entry.findtext("link") or ""
            if not link:
                atom_link = entry.find(
                    "{http://www.w3.org/2005/Atom}link"
                )
                if atom_link is not None:
                    link = atom_link.attrib.get("href", "")

            guid = entry.findtext("guid") or entry.findtext(
                "{http://www.w3.org/2005/Atom}id"
            ) or link or title

            current.append(guid)

            if not first_run and guid not in known and link:
                notify(title, link)

        state[feed] = list(dict.fromkeys(
            current + list(known)
        ))[:300]

    except Exception as error:
        print("Erreur:", feed, str(error))

STATE_FILE.write_text(
    json.dumps(state, ensure_ascii=False, indent=2)
)
