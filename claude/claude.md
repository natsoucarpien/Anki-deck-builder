# Claude - Assistant IA

Ce dossier contient les notes et le journal de bord de Claude pour le projet **Anki Deck Builder**.

## Fichiers

| Fichier | Description |
|---------|-------------|
| `claude.md` | Ce fichier - informations générales |
| `journal.md` | Journal de bord des interventions |

## Projet

Suite d'outils Python pour créer et modifier des decks Anki (.apkg) à partir de LearnableMeta.

### Stack technique
- Python 3.8+
- Playwright (scraping headless)
- Requests (download images)
- Pillow (manipulation d'images)
- SQLite (format Anki)

### Fichiers principaux

| Fichier | Description |
|---------|-------------|
| `learnablemeta_to_anki.py` | Extrait les metas de LearnableMeta et crée un deck .apkg |
| `anki_image_cropper.py` | Modifie les images d'un deck existant (crop, masquage) |
| `run_builder.bat` | Lanceur Windows pour le convertisseur |
| `run_cropper.bat` | Lanceur Windows pour le cropper |
| `README.md` | Documentation utilisateur |

### Fonctionnalités du cropper

- **Crop** : Coupe les images depuis un bord (droite, gauche, haut, bas) selon un pourcentage
- **Masquage** : Cache un coin de l'image avec une couleur (blanc/noir) - utile pour masquer les minimaps GeoGuessr
