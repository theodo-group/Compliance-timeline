#!/usr/bin/env python3
"""Lance UNIQUEMENT le fetch Playwright des pages "Standards Evolution and
Forecast" de CEN et CENELEC (voir fetch_standards_status_pages() dans
weekly_watch.py), sans toucher à Sonar, aux sources fixes, ni appeler le LLM.

Objectif : pouvoir vérifier ce que le pipeline va réellement récupérer sur ce
site, à la demande, sans lancer tout le run (coût, temps, envoi de mail).
Écrit le résultat brut dans un fichier intermédiaire inspectable.

À lancer en local :
    pip install playwright --break-system-packages
    playwright install chromium
    python3 automation/tools/check_standards_status.py

Sortie : automation/state/debug_last_standards_status_output.txt
(même convention de nommage que les autres fichiers debug_last_*_output.txt
produits par weekly_watch.py, voir save_debug_output())
"""

import sys
from pathlib import Path

# Permet d'importer weekly_watch.py (dossier parent) sans l'installer en package.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from weekly_watch import STANDARDS_EVOLUTION_URLS, STATE_DIR, fetch_standards_status_pages, log  # noqa: E402

OUTPUT_PATH = STATE_DIR / "debug_last_standards_status_output.txt"


def main() -> None:
    urls_desc = ", ".join(f"{org} ({url})" for org, url in STANDARDS_EVOLUTION_URLS)
    log(f"Test isolé — fetch de {urls_desc} (aucun autre appel, aucun LLM)...")
    result = fetch_standards_status_pages()

    STATE_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(result, encoding="utf-8")

    log(f"Terminé — {len(result)} caractères écrits dans {OUTPUT_PATH}")

    # Petit résumé lisible tout de suite dans le terminal, sans avoir à ouvrir
    # le fichier si on veut juste un premier coup d'œil rapide.
    has_table = "Standard reference" in result
    has_18286 = "18286" in result
    log(f"Contient le tableau attendu (\"Standard reference\") : {has_table}")
    log(f"Mentionne 18286 (repère de sanité, pas garanti à chaque run) : {has_18286}")
    log(f"Aperçu (300 premiers caractères) :\n{result[:300]}")


if __name__ == "__main__":
    main()
