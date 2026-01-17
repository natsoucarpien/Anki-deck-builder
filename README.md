# LearnableMeta → Anki Deck Converter

Script Python qui convertit les metas d'une page LearnableMeta en deck Anki (.apkg).

## 📋 Prérequis

- Python 3.8 ou supérieur
- Connexion internet

## 🔧 Installation

1. **Installer Python** (si pas déjà installé) :
   - Windows : [python.org/downloads](https://python.org/downloads)
   - Mac : `brew install python`
   - Linux : `sudo apt install python3 python3-pip`

2. **Installer les dépendances** :
   ```bash
   pip install playwright requests
   ```

3. **Installer le navigateur Chromium** :
   ```bash
   playwright install chromium
   ```

## 🚀 Utilisation

```bash
python learnablemeta_to_anki.py <URL>
```

### Exemple

```bash
python learnablemeta_to_anki.py https://learnablemeta.com/maps/695ef651a450338d7979829f
```

Le script va :
1. Ouvrir la page dans un navigateur invisible
2. Cliquer sur chaque meta pour extraire les informations
3. Télécharger toutes les images
4. Créer un fichier `.apkg` importable dans Anki

## 📚 Structure des cartes

Le deck utilise un type de carte "Learnable" avec 3 champs :

| Champ | Contenu | Exemple |
|-------|---------|---------|
| **Rule** | Nom de la meta | "Architecture - Sandstone" |
| **Question** | Image de la meta | [image du bâtiment] |
| **Response** | Description | "Many buildings in the Nevşehir Province are built by large, light and unevenly coloured, sandstone bricks." |

### Affichage

- **Recto** : Rule + Image
- **Verso** : Rule + Image + Response

## 📁 Fichier généré

Le script crée un fichier `.apkg` avec le format :
```
NomDuDeck_idcourt.apkg
```

Exemple : `A_Major_Bajor_Turkey_695ef651a450.apkg`

## 📥 Importer dans Anki

1. Ouvrir Anki
2. Fichier → Importer
3. Sélectionner le fichier `.apkg`
4. Cliquer sur "Importer"

## ⚠️ Notes

- Le script met environ 1-2 secondes par meta (41 metas ≈ 1-2 minutes)
- Les images sont téléchargées et embarquées dans le fichier .apkg
- Le script fonctionne avec n'importe quelle URL de learnablemeta.com

## 🐛 Problèmes courants

### "Playwright not installed"
```bash
pip install playwright
playwright install chromium
```

### "requests not installed"
```bash
pip install requests
```

### Le script ne trouve pas de metas
- Vérifiez que l'URL est correcte
- Assurez-vous que la page contient bien des metas

## 📄 Licence

Script libre d'utilisation pour usage personnel.
