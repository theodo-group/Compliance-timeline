#!/usr/bin/env python3
"""Diagnostic ponctuel — PAS utilisé par weekly_watch.py.

Compare, pour chacune des 12 FIXED_SOURCES, ce que récupère le fetch simple
actuel (requests.get + BeautifulSoup, la méthode réellement utilisée en prod)
et ce que récupérerait un navigateur headless (Playwright/Chromium) à la
même adresse. Objectif : vérifier qu'aucune des 12 sources n'a besoin d'un
navigateur (elles sont toutes confirmées server-rendues, voir le commentaire
de fetch_fixed_sources() dans weekly_watch.py) avant de clore l'audit lancé
suite au raté sur EN 18286.

Ne modifie rien à la config ni au pipeline — résultat écrit dans un fichier
pour inspection manuelle.

À lancer en local (nécessite playwright + chromium installés, voir
check_standards_status.py pour la marche à suivre) :

    python3 automation/tools/compare_fixed_sources_playwright.py

Sortie : automation/state/debug_fixed_sources_playwright_comparison.txt
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests
from bs4 import BeautifulSoup

from weekly_watch import FIXED_SOURCES, STATE_DIR, log  # noqa: E402

OUTPUT_PATH = STATE_DIR / "debug_fixed_sources_playwright_comparison.txt"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,fr;q=0.8",
}


def fetch_plain(url: str) -> str:
    """Même logique que fetch_fixed_sources() dans weekly_watch.py, mais sans
    troncature ni extraction de liens — juste le texte brut, pour comparer
    des volumes équivalents avec la version Playwright ci-dessous."""
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def fetch_playwright(browser, url: str) -> str:
    page = browser.new_page()
    try:
        page.goto(url, wait_until="networkidle", timeout=30000)
        text = page.inner_text("body")
        return re.sub(r"\n{3,}", "\n\n", text).strip()
    finally:
        page.close()


def main() -> None:
    from playwright.sync_api import sync_playwright

    sections = []
    with sync_playwright() as p:
        log("Lancement de Chromium (headless)...")
        browser = p.chromium.launch()

        for i, url in enumerate(FIXED_SOURCES, start=1):
            log(f"[{i}/{len(FIXED_SOURCES)}] {url}")

            try:
                plain_text = fetch_plain(url)
                plain_status = f"OK — {len(plain_text)} caractères"
            except Exception as e:  # noqa: BLE001
                plain_text = ""
                plain_status = f"ÉCHEC — {e}"

            try:
                pw_text = fetch_playwright(browser, url)
                pw_status = f"OK — {len(pw_text)} caractères"
            except Exception as e:  # noqa: BLE001
                pw_text = ""
                pw_status = f"ÉCHEC — {e}"

            diff_note = ""
            if plain_text and pw_text:
                delta = len(pw_text) - len(plain_text)
                diff_note = f"\nÉcart de longueur (Playwright - simple) : {delta:+d} caractères"

            section = (
                f"===== SOURCE {i}/{len(FIXED_SOURCES)} : {url} =====\n"
                f"Fetch simple (requests.get, methode actuelle en prod) : {plain_status}\n"
                f"Fetch Playwright (navigateur headless)                : {pw_status}"
                f"{diff_note}\n\n"
                f"--- Premiers 1000 caracteres (fetch simple) ---\n{plain_text[:1000]}\n\n"
                f"--- Premiers 1000 caracteres (Playwright) ---\n{pw_text[:1000]}\n"
            )
            sections.append(section)

        browser.close()

    STATE_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text("\n\n".join(sections), encoding="utf-8")
    log(f"Terminé — comparaison des {len(FIXED_SOURCES)} sources écrite dans {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
