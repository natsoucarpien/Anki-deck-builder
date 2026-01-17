#!/usr/bin/env python3
"""
Anki Image Cropper
==================
Modifie les images du champ "Question" d'un deck Anki (.apkg).

Operations disponibles:
- Crop depuis un bord (droite, gauche, haut, bas)
- Masquer un coin (remplir de blanc/noir)

INSTALLATION:
    pip install Pillow pillow-avif-plugin

UTILISATION:
    python anki_image_cropper.py
"""

import sys
import os
import re
import json
import sqlite3
import zipfile
import tempfile
import shutil
from pathlib import Path

# Vérifier si Pillow est installé
try:
    from PIL import Image
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False
    print("⚠️  Pillow non installé. Installez-le avec: pip install Pillow")

# Support AVIF
try:
    import pillow_avif
    AVIF_AVAILABLE = True
except ImportError:
    AVIF_AVAILABLE = False
    print("⚠️  Support AVIF non disponible. Installez: pip install pillow-avif-plugin")


def extract_apkg(apkg_path, extract_dir):
    """Extrait le contenu d'un fichier .apkg."""
    with zipfile.ZipFile(apkg_path, 'r') as zf:
        zf.extractall(extract_dir)
    return True


def get_question_images(db_path):
    """Récupère les noms des images utilisées dans le champ Question."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT flds FROM notes")
    rows = cursor.fetchall()
    conn.close()

    question_images = set()

    for row in rows:
        fields = row[0].split('\x1f')
        if len(fields) >= 2:
            question_field = fields[1]
            img_matches = re.findall(r'<img[^>]+src="([^"]+)"', question_field)
            for img_name in img_matches:
                question_images.add(img_name)

    return question_images


def crop_image(image_path, direction, percent):
    """Coupe une image depuis un bord selon le pourcentage donné."""
    try:
        with Image.open(image_path) as img:
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGBA')
            elif img.mode != 'RGB':
                img = img.convert('RGB')

            width, height = img.size

            if direction == 'droite':
                crop_pixels = int(width * percent / 100)
                new_width = width - crop_pixels
                if new_width <= 0:
                    return False
                cropped = img.crop((0, 0, new_width, height))

            elif direction == 'gauche':
                crop_pixels = int(width * percent / 100)
                new_width = width - crop_pixels
                if new_width <= 0:
                    return False
                cropped = img.crop((crop_pixels, 0, width, height))

            elif direction == 'haut':
                crop_pixels = int(height * percent / 100)
                new_height = height - crop_pixels
                if new_height <= 0:
                    return False
                cropped = img.crop((0, crop_pixels, width, height))

            elif direction == 'bas':
                crop_pixels = int(height * percent / 100)
                new_height = height - crop_pixels
                if new_height <= 0:
                    return False
                cropped = img.crop((0, 0, width, new_height))

            else:
                return False

            cropped.save(image_path, 'PNG')
            return True
    except Exception as e:
        print(f"  ⚠️ Erreur: {e}")
        return False


def mask_corner(image_path, corner, width_percent, height_percent, color='white'):
    """Masque un coin de l'image avec une couleur."""
    try:
        with Image.open(image_path) as img:
            # Convertir en RGBA pour supporter la transparence si nécessaire
            if img.mode != 'RGBA':
                img = img.convert('RGBA')

            width, height = img.size
            mask_width = int(width * width_percent / 100)
            mask_height = int(height * height_percent / 100)

            # Définir la couleur
            fill_color = (255, 255, 255, 255) if color == 'white' else (0, 0, 0, 255)

            # Créer une copie pour dessiner
            result = img.copy()

            # Calculer les coordonnées selon le coin
            if corner == 'bas-droite':
                x1, y1 = width - mask_width, height - mask_height
                x2, y2 = width, height
            elif corner == 'bas-gauche':
                x1, y1 = 0, height - mask_height
                x2, y2 = mask_width, height
            elif corner == 'haut-droite':
                x1, y1 = width - mask_width, 0
                x2, y2 = width, mask_height
            elif corner == 'haut-gauche':
                x1, y1 = 0, 0
                x2, y2 = mask_width, mask_height
            else:
                return False

            # Remplir la zone avec la couleur
            for x in range(x1, x2):
                for y in range(y1, y2):
                    result.putpixel((x, y), fill_color)

            # Convertir en RGB pour sauvegarder en PNG
            result = result.convert('RGB')
            result.save(image_path, 'PNG')
            return True
    except Exception as e:
        print(f"  ⚠️ Erreur: {e}")
        return False


def create_apkg(source_dir, output_path, media_map):
    """Recrée un fichier .apkg à partir des fichiers extraits."""
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        db_path = os.path.join(source_dir, 'collection.anki2')
        if os.path.exists(db_path):
            zf.write(db_path, 'collection.anki2')

        media_path = os.path.join(source_dir, 'media')
        if os.path.exists(media_path):
            zf.write(media_path, 'media')

        for idx in media_map.keys():
            media_file = os.path.join(source_dir, idx)
            if os.path.exists(media_file):
                zf.write(media_file, idx)


def main():
    print("=" * 60)
    print("  Anki Image Cropper")
    print("=" * 60)

    if not PILLOW_AVAILABLE:
        print("\n❌ Pillow n'est pas installé!")
        print("   pip install Pillow pillow-avif-plugin")
        input("\nAppuyez sur Entrée pour quitter...")
        sys.exit(1)

    # Demander le fichier .apkg
    print()
    apkg_path = input("Chemin du fichier .apkg: ").strip().strip('"')

    if not apkg_path or not os.path.exists(apkg_path):
        print(f"\n❌ Fichier non trouvé: {apkg_path}")
        input("\nAppuyez sur Entrée pour quitter...")
        sys.exit(1)

    # Menu d'opération
    print("\n" + "-" * 40)
    print("Operations disponibles:")
    print("  1. Crop depuis un bord")
    print("  2. Masquer un coin")
    print("-" * 40)

    op_choice = input("Choix (1 ou 2): ").strip()

    if op_choice == '1':
        # Crop depuis un bord
        print("\nDirection du crop:")
        print("  1. Droite")
        print("  2. Gauche")
        print("  3. Haut")
        print("  4. Bas")

        dir_choice = input("Choix (1-4, defaut: 1): ").strip() or '1'
        directions = {'1': 'droite', '2': 'gauche', '3': 'haut', '4': 'bas'}
        direction = directions.get(dir_choice, 'droite')

        percent_input = input(f"Pourcentage a couper depuis {direction} (defaut: 35): ").strip()
        percent = 35
        if percent_input:
            try:
                percent = float(percent_input)
                if percent <= 0 or percent >= 100:
                    percent = 35
            except ValueError:
                percent = 35

        operation = ('crop', direction, percent)
        print(f"\n📐 Crop: {percent}% depuis {direction}")

    elif op_choice == '2':
        # Masquer un coin
        print("\nCoin a masquer:")
        print("  1. Bas-droite")
        print("  2. Bas-gauche")
        print("  3. Haut-droite")
        print("  4. Haut-gauche")

        corner_choice = input("Choix (1-4, defaut: 1): ").strip() or '1'
        corners = {'1': 'bas-droite', '2': 'bas-gauche', '3': 'haut-droite', '4': 'haut-gauche'}
        corner = corners.get(corner_choice, 'bas-droite')

        width_input = input("Largeur du masque en % (defaut: 40): ").strip()
        width_percent = 40
        if width_input:
            try:
                width_percent = float(width_input)
                if width_percent <= 0 or width_percent >= 100:
                    width_percent = 40
            except ValueError:
                width_percent = 40

        height_input = input("Hauteur du masque en % (defaut: 50): ").strip()
        height_percent = 50
        if height_input:
            try:
                height_percent = float(height_input)
                if height_percent <= 0 or height_percent >= 100:
                    height_percent = 50
            except ValueError:
                height_percent = 50

        print("\nCouleur du masque:")
        print("  1. Blanc")
        print("  2. Noir")
        color_choice = input("Choix (1 ou 2, defaut: 1): ").strip() or '1'
        color = 'white' if color_choice == '1' else 'black'

        operation = ('mask', corner, width_percent, height_percent, color)
        print(f"\n🎭 Masque: {corner} ({width_percent}% x {height_percent}%) en {color}")

    else:
        print("\n❌ Choix invalide.")
        input("\nAppuyez sur Entrée pour quitter...")
        sys.exit(1)

    # Créer un dossier temporaire
    temp_dir = tempfile.mkdtemp()

    try:
        # Extraire le .apkg
        print(f"\n📦 Extraction de {os.path.basename(apkg_path)}...")
        extract_apkg(apkg_path, temp_dir)

        # Lire le fichier media
        media_json_path = os.path.join(temp_dir, 'media')
        media_map = {}
        if os.path.exists(media_json_path):
            with open(media_json_path, 'r') as f:
                media_map = json.load(f)

        name_to_idx = {v: k for k, v in media_map.items()}

        # Récupérer les images du champ Question
        db_path = os.path.join(temp_dir, 'collection.anki2')
        question_images = get_question_images(db_path)

        print(f"\n🖼️  {len(question_images)} images trouvées dans le champ Question")

        # Appliquer l'opération
        processed_count = 0
        for img_name in question_images:
            if img_name in name_to_idx:
                idx = name_to_idx[img_name]
                img_path = os.path.join(temp_dir, idx)

                if os.path.exists(img_path):
                    print(f"  ✂️ {img_name}", end="")

                    if operation[0] == 'crop':
                        success = crop_image(img_path, operation[1], operation[2])
                    else:  # mask
                        success = mask_corner(img_path, operation[1], operation[2], operation[3], operation[4])

                    if success:
                        print(" ✓")
                        processed_count += 1
                    else:
                        print(" ✗")

        # Créer le nouveau fichier .apkg
        base_name = os.path.splitext(apkg_path)[0]
        if operation[0] == 'crop':
            output_path = f"{base_name}_cropped.apkg"
        else:
            output_path = f"{base_name}_masked.apkg"

        print(f"\n📦 Création de {os.path.basename(output_path)}...")
        create_apkg(temp_dir, output_path, media_map)

        print(f"\n✅ Terminé!")
        print(f"   📁 Fichier: {output_path}")
        print(f"   🖼️  Images traitées: {processed_count}")

    finally:
        shutil.rmtree(temp_dir)

    input("\nAppuyez sur Entrée pour quitter...")


if __name__ == "__main__":
    main()
