# Claude - Assistant IA

Ce dossier contient les notes et le journal de bord de Claude pour le projet **LearnableMeta → Anki Deck Converter**.

## Fichiers

| Fichier | Description |
|---------|-------------|
| `claude.md` | Ce fichier - informations générales |
| `journal.md` | Journal de bord des interventions |

## Projet

Convertisseur Python qui transforme les metas du site LearnableMeta.com en decks Anki (.apkg).

### Stack technique
- Python 3.8+
- Playwright (scraping headless)
- Requests (download images)
- SQLite (format Anki)

### Fichiers principaux
- `learnablemeta_to_anki.py` - Script principal
- `run.bat` - Lanceur Windows
- `README.md` - Documentation utilisateur
