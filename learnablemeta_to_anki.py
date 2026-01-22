#!/usr/bin/env python3
"""
LearnableMeta to Anki Deck Converter (Version corrigée)
=======================================================
Crée un fichier .apkg (deck Anki) à partir des metas d'une page LearnableMeta.

INSTALLATION:
    pip install playwright requests
    playwright install chromium

UTILISATION:
    python learnablemeta_to_anki.py https://learnablemeta.com/maps/68d3d5bfbb462cc5f7bb6945
"""

import sys
import os
import re
import time
import json
import sqlite3
import zipfile
import hashlib
import tempfile
import shutil
from pathlib import Path

# Vérifier si playwright est installé
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("⚠️  Playwright non installé.")

# Vérifier si requests est installé  
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("⚠️  requests non installé.")


def generate_id(text):
    """Génère un ID numérique unique à partir d'un texte."""
    return int(hashlib.sha256(text.encode()).hexdigest()[:12], 16)


def download_image(url, folder):
    """Télécharge une image et retourne le chemin local."""
    if not REQUESTS_AVAILABLE:
        return None, None

    os.makedirs(folder, exist_ok=True)
    filename = url.split("/")[-1]
    # Décoder les caractères URL (%20 -> espace) et remplacer espaces par underscores
    from urllib.parse import unquote
    filename = unquote(filename).replace(' ', '_')
    if not any(filename.endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.avif']):
        filename += ".png"
    
    filepath = os.path.join(folder, filename)
    
    if os.path.exists(filepath):
        return filepath, filename
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, timeout=15, headers=headers)
        response.raise_for_status()
        with open(filepath, 'wb') as f:
            f.write(response.content)
        return filepath, filename
    except Exception as e:
        print(f"  ⚠️ Erreur image: {e}")
        return None, None


def clean_text(text):
    """Nettoie le texte et décode les entités."""
    if not text:
        return ""
    
    # D'abord, corriger l'encodage UTF-8 mal interprété
    try:
        # Tous les caractères français mal encodés en UTF-8 → Latin-1
        # Vérifier si on a des séquences suspectes
        if any(suspect in text for suspect in ['Ã', 'Å', 'Ã‚', 'Ãƒ']):
            text = text.encode('latin-1').decode('utf-8')
    except Exception as e:
        # Si ça échoue, essayer une autre méthode
        try:
            text = text.encode('cp1252').decode('utf-8')
        except:
            pass
    
    # Décoder les entités unicode échappées (\u003C -> <, etc.)
    # Utiliser une approche plus simple avec replace
    unicode_replacements = {
        r'\u003C': '<',
        r'\u003E': '>',
        r'\u003D': '=',
        r'\u0026': '&',
        r'\u0027': "'",
        r'\u0022': '"',
    }
    
    for pattern, replacement in unicode_replacements.items():
        text = text.replace(pattern, replacement)
    
    # Supprimer les balises HTML
    text = re.sub(r'<[^>]+>', '', text)
    
    # Nettoyer les espaces multiples
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text


def extract_metas_from_page(url):
    """Extrait toutes les metas via Playwright en attendant le chargement dynamique."""
    if not PLAYWRIGHT_AVAILABLE:
        print("❌ Playwright requis pour l'extraction")
        return [], ""

    metas = []
    deck_title = "LearnableMeta Deck"

    print(f"\n🌐 Chargement de la page...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = context.new_page()

        page.goto(url, wait_until='networkidle', timeout=90000)
        
        # Attendre que les metas se chargent (attendre l'élément de liste des metas)
        print("⏳ Attente du chargement des metas...")
        
        # Attendre l'apparition des boutons de metas
        try:
            page.wait_for_selector('button', timeout=10000)
            print("✓ Premiers éléments détectés")
        except:
            print("⚠️  Timeout en attendant les éléments")
        
        # Scroll pour forcer le lazy loading
        print("📜 Scroll pour charger toutes les metas...")
        
        # Scroll progressif plus lent et plus long
        last_height = page.evaluate('document.body.scrollHeight')
        scroll_attempts = 0
        max_attempts = 30
        
        while scroll_attempts < max_attempts:
            # Scroll vers le bas
            page.evaluate('window.scrollBy(0, window.innerHeight)')
            time.sleep(0.8)
            
            # Vérifier si on a atteint le bas
            new_height = page.evaluate('document.body.scrollHeight')
            current_pos = page.evaluate('window.pageYOffset + window.innerHeight')
            
            # Si on a atteint le bas ET que la hauteur n'a pas changé, on a tout chargé
            if current_pos >= new_height and new_height == last_height:
                scroll_attempts += 1
                if scroll_attempts >= 3:  # Confirmer 3 fois qu'on est vraiment au bout
                    print(f"✓ Fin du scroll détectée après {scroll_attempts} tentatives")
                    break
            else:
                scroll_attempts = 0  # Reset si on détecte du nouveau contenu
            
            last_height = new_height
        
        # Scroll final jusqu'en bas
        for _ in range(5):
            page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            time.sleep(0.5)
        
        # Attendre le chargement final
        time.sleep(2)
        
        # Retour en haut
        page.evaluate('window.scrollTo(0, 0)')
        time.sleep(1)

        # Récupérer le titre du deck
        try:
            title_elem = page.query_selector('h1')
            if title_elem:
                deck_title = title_elem.inner_text().strip()
                print(f"📖 Deck: {deck_title}")
        except:
            pass

        # Nouvelle méthode: extraire directement du DOM
        # Les metas sont dans des boutons avec des div contenant le nom et la description
        
        # D'abord, essayer l'ancienne méthode (parsing du JavaScript)
        page_content = page.content()
        
        print("🔍 Recherche du tableau metaList dans le code source...")
        
        # Chercher le bloc metaList:[ ... ] dans le HTML (format JavaScript)
        js_array = ""
        idx = page_content.find('metaList:[')
        if idx >= 0:
            start = idx + len('metaList:')
            depth = 0
            end = start
            for i, c in enumerate(page_content[start:start+500000]):  # Augmenter la limite
                if c == '[':
                    depth += 1
                elif c == ']':
                    depth -= 1
                    if depth == 0:
                        end = start + i + 1
                        break
            js_array = page_content[start:end]
            
            print(f"✓ Bloc metaList trouvé ({len(js_array)} caractères)")

        if js_array:
            # Parser chaque objet meta individuellement
            obj_pattern = re.finditer(
                r'\{id:(\d+),name:"([^"]+)",note:"([^"]*)",images:\[([^\]]*)\],locationsCount:"(\d+)"',
                js_array
            )

            for match in obj_pattern:
                meta_id = match.group(1)
                name = match.group(2)
                note_raw = match.group(3)
                images_raw = match.group(4)

                # Extraire l'URL de l'image
                img_match = re.search(r'"([^"]+)"', images_raw)
                image_url = img_match.group(1) if img_match else ""

                # Nettoyer la note - IMPORTANT: décoder d'abord l'encodage
                note = note_raw
                
                # Corriger l'encodage UTF-8 mal interprété AVANT de nettoyer
                try:
                    if any(suspect in note for suspect in ['Ã', 'Å']):
                        note = note.encode('latin-1').decode('utf-8')
                except:
                    pass
                
                # Puis nettoyer le HTML
                note = clean_text(note)
                
                # Corriger aussi le nom
                name_clean = name
                try:
                    if any(suspect in name_clean for suspect in ['Ã', 'Å']):
                        name_clean = name_clean.encode('latin-1').decode('utf-8')
                except:
                    pass

                metas.append({
                    'rule': name_clean,
                    'response': note,
                    'image_url': image_url
                })
                
            print(f"✓ {len(metas)} metas extraites du code source")

        print(f"📋 {len(metas)} metas trouvées sur 406 attendues")
        
        if len(metas) < 406:
            print(f"⚠️  Il manque {406 - len(metas)} metas - le site indique 406 au total")

        # Afficher les metas trouvées
        for i, meta in enumerate(metas):
            print(f"[{i+1}/{len(metas)}] {meta['rule']} ✓")

        browser.close()

    return metas, deck_title


def create_anki_package(metas, deck_name, output_path):
    """
    Crée un fichier .apkg (Anki package) à partir des metas.
    Format .apkg = ZIP contenant collection.anki2 (SQLite) + media
    """
    
    # Créer un dossier temporaire
    temp_dir = tempfile.mkdtemp()
    media_dir = os.path.join(temp_dir, 'media_files')
    os.makedirs(media_dir, exist_ok=True)
    
    # IDs uniques
    deck_id = generate_id(deck_name)
    model_id = generate_id(f"learnable_{deck_name}")
    
    # Créer la base de données SQLite
    db_path = os.path.join(temp_dir, 'collection.anki2')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Schéma Anki 2.1
    cursor.executescript('''
        CREATE TABLE col (
            id INTEGER PRIMARY KEY,
            crt INTEGER NOT NULL,
            mod INTEGER NOT NULL,
            scm INTEGER NOT NULL,
            ver INTEGER NOT NULL,
            dty INTEGER NOT NULL,
            usn INTEGER NOT NULL,
            ls INTEGER NOT NULL,
            conf TEXT NOT NULL,
            models TEXT NOT NULL,
            decks TEXT NOT NULL,
            dconf TEXT NOT NULL,
            tags TEXT NOT NULL
        );
        
        CREATE TABLE notes (
            id INTEGER PRIMARY KEY,
            guid TEXT NOT NULL,
            mid INTEGER NOT NULL,
            mod INTEGER NOT NULL,
            usn INTEGER NOT NULL,
            tags TEXT NOT NULL,
            flds TEXT NOT NULL,
            sfld TEXT NOT NULL,
            csum INTEGER NOT NULL,
            flags INTEGER NOT NULL,
            data TEXT NOT NULL
        );
        
        CREATE TABLE cards (
            id INTEGER PRIMARY KEY,
            nid INTEGER NOT NULL,
            did INTEGER NOT NULL,
            ord INTEGER NOT NULL,
            mod INTEGER NOT NULL,
            usn INTEGER NOT NULL,
            type INTEGER NOT NULL,
            queue INTEGER NOT NULL,
            due INTEGER NOT NULL,
            ivl INTEGER NOT NULL,
            factor INTEGER NOT NULL,
            reps INTEGER NOT NULL,
            lapses INTEGER NOT NULL,
            left INTEGER NOT NULL,
            odue INTEGER NOT NULL,
            odid INTEGER NOT NULL,
            flags INTEGER NOT NULL,
            data TEXT NOT NULL
        );
        
        CREATE TABLE revlog (
            id INTEGER PRIMARY KEY,
            cid INTEGER NOT NULL,
            usn INTEGER NOT NULL,
            ease INTEGER NOT NULL,
            ivl INTEGER NOT NULL,
            lastIvl INTEGER NOT NULL,
            factor INTEGER NOT NULL,
            time INTEGER NOT NULL,
            type INTEGER NOT NULL
        );
        
        CREATE TABLE graves (
            usn INTEGER NOT NULL,
            oid INTEGER NOT NULL,
            type INTEGER NOT NULL
        );
        
        CREATE INDEX ix_notes_csum ON notes (csum);
        CREATE INDEX ix_notes_usn ON notes (usn);
        CREATE INDEX ix_cards_nid ON cards (nid);
        CREATE INDEX ix_cards_sched ON cards (did, queue, due);
        CREATE INDEX ix_cards_usn ON cards (usn);
        CREATE INDEX ix_revlog_cid ON revlog (cid);
        CREATE INDEX ix_revlog_usn ON revlog (usn);
    ''')
    
    # Timestamp actuel
    now = int(time.time())
    now_ms = now * 1000
    
    # CSS pour les cartes
    card_css = '''.card {
    font-family: Arial, sans-serif;
    font-size: 18px;
    text-align: center;
    color: #333;
    background-color: #f5f5f5;
    padding: 20px;
}
.rule {
    font-size: 22px;
    font-weight: bold;
    color: #2c5282;
    margin-bottom: 15px;
}
.question img {
    max-width: 100%;
    max-height: 400px;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.2);
}
.response {
    font-size: 16px;
    margin-top: 15px;
    padding: 15px;
    background-color: #fff;
    border-radius: 8px;
    text-align: left;
    line-height: 1.5;
}
hr {
    border: none;
    height: 1px;
    background-color: #ddd;
    margin: 15px 0;
}'''
    
    # Modèle de carte
    model = {
        str(model_id): {
            "id": model_id,
            "name": "Learnable",
            "type": 0,
            "mod": now,
            "usn": -1,
            "sortf": 0,
            "did": deck_id,
            "tmpls": [{
                "name": "Card 1",
                "ord": 0,
                "qfmt": '<div class="question">{{Question}}</div>',
                "afmt": '{{Response}}',
                "bqfmt": "",
                "bafmt": "",
                "did": None,
                "bfont": "",
                "bsize": 0
            }],
            "flds": [
                {"name": "Rule", "ord": 0, "sticky": False, "rtl": False, "font": "Arial", "size": 20, "media": []},
                {"name": "Question", "ord": 1, "sticky": False, "rtl": False, "font": "Arial", "size": 20, "media": []},
                {"name": "Response", "ord": 2, "sticky": False, "rtl": False, "font": "Arial", "size": 20, "media": []}
            ],
            "css": card_css,
            "latexPre": "\\documentclass[12pt]{article}\n\\special{papersize=3in,5in}\n\\usepackage{amssymb,amsmath}\n\\pagestyle{empty}\n\\setlength{\\parindent}{0in}\n\\begin{document}\n",
            "latexPost": "\\end{document}",
            "latexsvg": False,
            "req": [[0, "any", [0, 1]]]
        }
    }
    
    # Deck
    decks = {
        str(deck_id): {
            "id": deck_id,
            "name": deck_name,
            "mod": now,
            "usn": -1,
            "lrnToday": [0, 0],
            "revToday": [0, 0],
            "newToday": [0, 0],
            "timeToday": [0, 0],
            "collapsed": False,
            "browserCollapsed": False,
            "desc": f"Deck généré depuis LearnableMeta",
            "dyn": 0,
            "conf": 1,
            "extendNew": 0,
            "extendRev": 0
        },
        "1": {
            "id": 1,
            "name": "Default",
            "mod": now,
            "usn": -1,
            "lrnToday": [0, 0],
            "revToday": [0, 0],
            "newToday": [0, 0],
            "timeToday": [0, 0],
            "collapsed": False,
            "browserCollapsed": False,
            "desc": "",
            "dyn": 0,
            "conf": 1,
            "extendNew": 0,
            "extendRev": 0
        }
    }
    
    # Configuration du deck
    dconf = {
        "1": {
            "id": 1,
            "name": "Default",
            "mod": 0,
            "usn": 0,
            "maxTaken": 60,
            "autoplay": True,
            "timer": 0,
            "replayq": True,
            "new": {"bury": False, "delays": [1, 10], "initialFactor": 2500, "ints": [1, 4, 0], "order": 1, "perDay": 20},
            "rev": {"bury": False, "ease4": 1.3, "ivlFct": 1, "maxIvl": 36500, "perDay": 200, "hardFactor": 1.2},
            "lapse": {"delays": [10], "leechAction": 1, "leechFails": 8, "minInt": 1, "mult": 0}
        }
    }
    
    conf = {
        "activeDecks": [1],
        "curDeck": deck_id,
        "newSpread": 0,
        "collapseTime": 1200,
        "timeLim": 0,
        "estTimes": True,
        "dueCounts": True,
        "curModel": str(model_id),
        "nextPos": 1,
        "sortType": "noteFld",
        "sortBackwards": False,
        "addToCur": True
    }
    
    # Insérer les métadonnées
    cursor.execute('''
        INSERT INTO col VALUES (1, ?, ?, ?, 11, 0, -1, 0, ?, ?, ?, ?, '{}')
    ''', (now, now, now_ms, json.dumps(conf), json.dumps(model), json.dumps(decks), json.dumps(dconf)))
    
    # Créer les notes et cartes
    media_map = {}
    media_index = 0
    
    print(f"\n📝 Création de {len(metas)} cartes...")
    
    for i, meta in enumerate(metas):
        # Afficher la progression
        progress = (i + 1) / len(metas) * 100
        bar_length = 40
        filled = int(bar_length * (i + 1) / len(metas))
        bar = '█' * filled + '░' * (bar_length - filled)
        print(f'\r  [{bar}] {progress:.1f}% ({i + 1}/{len(metas)})', end='', flush=True)
        
        note_id = now_ms + i
        card_id = now_ms + 1000000 + i
        guid = hashlib.md5(f"{deck_name}_{meta['rule']}_{i}".encode()).hexdigest()[:10]
        
        # Préparer les champs image (deux copies distinctes)
        question_image = ""
        response_image = ""
        if meta['image_url']:
            filepath, filename = download_image(meta['image_url'], media_dir)
            if filepath and os.path.exists(filepath):
                # Image pour Question
                name_base, ext = os.path.splitext(filename)
                filename_q = f"{name_base}_q{ext}"
                new_name_q = str(media_index)
                media_map[new_name_q] = filename_q
                shutil.copy(filepath, os.path.join(temp_dir, new_name_q))
                question_image = f'<img src="{filename_q}">'
                media_index += 1

                # Image pour Response (copie distincte)
                filename_r = f"{name_base}_r{ext}"
                new_name_r = str(media_index)
                media_map[new_name_r] = filename_r
                shutil.copy(filepath, os.path.join(temp_dir, new_name_r))
                response_image = f'<img src="{filename_r}">'
                media_index += 1

        # Champs séparés par \x1f (séparateur Anki)
        question_field = f"<div>{question_image}</div>" if question_image else "<div></div>"
        response_field = f"<div><b>{meta['rule']}</b><br><br>{response_image}<br><br><p style=\"text-align: justify;\">{meta['response']}</p></div>"
        fields = f"{meta['rule']}\x1f{question_field}\x1f{response_field}"
        
        # Checksum
        csum = int(hashlib.sha1(meta['rule'].encode()).hexdigest()[:8], 16)
        
        # Insérer la note
        cursor.execute('''
            INSERT INTO notes VALUES (?, ?, ?, ?, -1, '', ?, ?, ?, 0, '')
        ''', (note_id, guid, model_id, now, fields, meta['rule'], csum))
        
        # Insérer la carte
        cursor.execute('''
            INSERT INTO cards VALUES (?, ?, ?, 0, ?, -1, 0, 0, ?, 0, 0, 0, 0, 0, 0, 0, 0, '')
        ''', (card_id, note_id, deck_id, now, i))
    
    # Aller à la ligne après la barre de progression
    print()
    
    conn.commit()
    conn.close()
    
    # Créer le fichier media
    media_json_path = os.path.join(temp_dir, 'media')
    with open(media_json_path, 'w') as f:
        json.dump(media_map, f)
    
    # Créer l'archive ZIP
    print(f"\n📦 Création du fichier {output_path}...")
    print("  [████████████████████████████████████████] Compression...", end='', flush=True)
    
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.write(db_path, 'collection.anki2')
        zf.write(media_json_path, 'media')
        
        for idx in media_map.keys():
            media_file = os.path.join(temp_dir, idx)
            if os.path.exists(media_file):
                zf.write(media_file, idx)
    
    print(" ✓")  # Marquer la compression comme terminée
    
    # Nettoyage
    shutil.rmtree(temp_dir)
    
    print(f"\n✅ Deck créé avec succès!")
    print(f"   📁 Fichier: {output_path}")
    print(f"   📊 Cartes: {len(metas)}")
    print(f"   🖼️  Images: {len(media_map)}")
    print(f"\n💡 Pour importer dans Anki: Fichier > Importer > {output_path}")
    
    return output_path


def main():
    print("=" * 60)
    print("  LearnableMeta → Anki Deck Converter")
    print("=" * 60)
    
    if len(sys.argv) < 2:
        print(__doc__)
        print("\n❌ URL manquante!")
        print("\nUsage:")
        print("  python learnablemeta_to_anki.py <URL>")
        print("\nExemple:")
        print("  python learnablemeta_to_anki.py https://learnablemeta.com/maps/68d3d5bfbb462cc5f7bb6945")
        sys.exit(1)
    
    url = sys.argv[1]
    
    if not PLAYWRIGHT_AVAILABLE:
        print("\n❌ Playwright n'est pas installé!")
        print("\nInstallez-le avec ces commandes:")
        print("  pip install playwright requests")
        print("  playwright install chromium")
        sys.exit(1)
    
    # Valider l'URL
    if 'learnablemeta.com' not in url:
        print("\n⚠️  Attention: Cette URL ne semble pas être de learnablemeta.com")
        response = input("Continuer quand même? (o/n): ")
        if response.lower() != 'o':
            sys.exit(0)
    
    # Extraire les metas
    metas, deck_title = extract_metas_from_page(url)
    
    if not metas:
        print("\n❌ Aucune meta trouvée!")
        sys.exit(1)
    
    # Nom du fichier de sortie
    map_id = url.split('/')[-1][:12]
    safe_title = re.sub(r'[^\w\s-]', '', deck_title).strip()[:30]
    output_file = f"{safe_title}_{map_id}.apkg" if safe_title else f"learnablemeta_{map_id}.apkg"
    output_file = output_file.replace(' ', '_')
    
    # Créer le deck
    create_anki_package(metas, deck_title, output_file)


if __name__ == "__main__":
    main()