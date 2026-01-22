# Journal de bord

## 2026-01-17

### Session 1

**Contexte :** Prise en main du projet.

**Actions effectuees :**
1. Exploration du repertoire de travail
2. Lecture et analyse des fichiers existants :
   - `README.md` - Documentation utilisateur
   - `learnablemeta_to_anki.py` - Script principal (582 lignes)
3. Creation de `run.bat` - Lanceur batch pour executer le script Python facilement
4. Creation du dossier `claude/` avec :
   - `claude.md` - Informations generales
   - `journal.md` - Ce journal de bord

**Etat du projet :**
- Script fonctionnel pour convertir les metas LearnableMeta en decks Anki
- Dependencies : playwright, requests
- Format de sortie : .apkg (SQLite + images en ZIP)

**Prochaines etapes possibles :**
- Tests du script
- Ameliorations eventuelles selon les besoins utilisateur

---

### Session 2

**Probleme signale :** Le batch `run.bat` ne fonctionnait pas correctement.

**Besoin utilisateur :** Un prompt interactif pour entrer l'URL (pas en argument).

**Correction :**
- Refonte du batch avec `set /p` pour demander l'URL a l'utilisateur
- Ajout d'un en-tete visuel
- `cd /d "%~dp0"` pour se placer dans le bon repertoire

**Fichier modifie :** `run.bat`

---

### Session 3

**Test du batch :** Succes - le batch se lance et demande l'URL correctement.

**Probleme detecte :** Les dependances Python ne sont pas installees :
- Playwright non installe
- requests non installe

**Action requise :** Installer les dependances :
```
pip install playwright requests
playwright install chromium
```

---

### Session 4

**Action :** Installation des dependances.

**Packages installes :**
- playwright 1.57.0, requests 2.32.5
- Chromium 143.0.7499.4

**Statut :** Pret a l'utilisation.

---

### Session 5

**Probleme :** Le script trouve 0 metas.

**Diagnostic :** Les donnees sont dans un JSON JavaScript embarque (`metaList:[...]`), pas dans des boutons HTML.

**Correction :** Refonte de `extract_metas_from_page()` pour parser le format JavaScript.

---

### Session 6

**Probleme :** 125 metas trouvees au lieu de 41 (doublons), donnees incorrectes.

**Diagnostic :** Le regex s'arretait au premier `]` (celui de `images:[]`).

**Correction :** Utilisation du comptage de crochets pour extraire le tableau complet.

**Resultat :** 41 metas correctement extraites.

---

### Session 7

**Modifications des cartes Anki :**
1. Image presente dans Question ET Response
2. Nom de la meta (Rule) en gras `<b>` au debut de Response
3. Champs enveloppes dans `<div>...</div>`
4. Batch renomme en `run_builder.bat`

---

### Session 8

**Modifications supplementaires :**
1. Recto = Question seule (sans Rule ni separateur)
2. Verso = `{{Response}}` uniquement
3. Description justifiee (`text-align: justify`)
4. Espaces (`<br><br>`) avant et apres l'image

---

### Session 9

**Probleme :** Image "Infrastructure - European Poleplate" cassee.

**Diagnostic :** URL avec `%20` (espaces encodes) causait des problemes de nom de fichier.

**Correction :** Ajout de `urllib.parse.unquote()` + remplacement des espaces par underscores.

---

### Session 10

**Modification :** Images Question et Response separees.

Deux fichiers distincts pour chaque carte :
- `image_q.png` pour Question
- `image_r.png` pour Response

Permet de modifier l'une sans affecter l'autre.

---

### Session 11

**Nouveau script :** `anki_image_cropper.py`

**Objectif :** Cropper les images du champ Question depuis le bord droit.

**Fonctionnalites :**
- Demande le fichier .apkg
- Demande le % a couper (defaut: 35%)
- Coupe uniquement les images du champ Question
- Cree un nouveau fichier `_cropped.apkg`

**Batch associe :** `run_cropper.bat`

**Probleme detecte :** Erreurs sur certaines images :
- "unknown file extension" - fichiers .png qui sont en fait des AVIF/WEBP
- "cannot identify image file" - format non reconnu par Pillow

**Cause :** Certaines images sont telechargees avec extension .png mais sont en realite des AVIF ou WEBP (le serveur renvoie un format different).

---

### Session 12

**Amélioration du script** `learnablemeta_to_anki.py`

**Objectif :** méthode de détéction 

**Fonctionnalites :**
- méthode de détéction de la liste de méta plus robuste
- barre de progression visuelle lors de la création du deck
- prise en charge des caractères spéciaux francocphones
