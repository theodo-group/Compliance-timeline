#!/usr/bin/env python3
"""Diagnostic ponctuel — PAS utilisé par weekly_watch.py.

Compare la méthode actuelle (requests + BeautifulSoup) à un fetch via
Playwright/Chromium, sur les deux sources qui échouaient en run réel
(IMDRF timeout, FDA bloqué par un pare-feu applicatif / bot-detection).

À lancer en local (ce sandbox n'a pas accès à PyPI/Chromium) :

    pip install playwright beautifulsoup4 requests
    playwright install chromium
    python3 automation/tools/test_playwright_fetch.py

Objectif : voir si un vrai navigateur headless passe là où une requête HTTP
simple échoue, avant de décider si ça vaut la complexité de l'ajouter au
pipeline (temps d'install Chromium en CI, dépendance supplémentaire).
"""

import sys

import requests
from bs4 import BeautifulSoup

URLS = [
    "https://www.imdrf.org/",
    "https://www.fda.gov/medical-devices/digital-health-center-excellence",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,fr;q=0.8",
}


def try_requests(url: str):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style"]):
            tag.decompose()
        text = soup.get_text(separator="\n").strip()
        return True, len(text), text[:300].replace("\n", " ")
    except Exception as e:  # noqa: BLE001
        return False, 0, str(e)


def try_playwright(url: str):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return False, 0, "playwright non installé (pip install playwright && playwright install chromium)"

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(user_agent=HEADERS["User-Agent"])
            page.goto(url, timeout=30000, wait_until="networkidle")
            html = page.content()
            browser.close()
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style"]):
            tag.decompose()
        text = soup.get_text(separator="\n").strip()
        return True, len(text), text[:300].replace("\n", " ")
    except Exception as e:  # noqa: BLE001
        return False, 0, str(e)


def main() -> None:
    for url in URLS:
        print(f"\n=== {url} ===")
        ok, length, sample = try_requests(url)
        print(f"requests   : {'OK' if ok else 'ECHEC'} ({length} car.)")
        if not ok:
            print(f"             {sample}")

        ok2, length2, sample2 = try_playwright(url)
        print(f"playwright : {'OK' if ok2 else 'ECHEC'} ({length2} car.)")
        if not ok2:
            print(f"             {sample2}")


if __name__ == "__main__":
    sys.exit(main())
