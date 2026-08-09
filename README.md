# MERCA FRUIT SEC

Site e-commerce leger pour une boutique locale, avec panier cote navigateur et commande finale sur WhatsApp.

## Ce que le projet fait

- Accueil plus propre et plus professionnel
- Catalogue de produits avec recherche et filtre par categorie
- Panier avec quantites, total automatique et suppression d'articles
- Envoi de la commande sur WhatsApp
- Dashboard administrateur
- Ajout, modification et suppression des categories
- Ajout, modification, suppression et activation/desactivation des produits
- Gestion d'une quantite stocke optionnelle par produit
- Upload d'images
- Base SQLite
- Design responsive desktop et mobile

## Installation

1. Creer un environnement virtuel :

```bash
python -m venv venv
```

2. Activer l'environnement :

Windows :

```bash
venv\Scripts\activate
```

Linux/macOS :

```bash
source venv/bin/activate
```

3. Installer les dependances :

```bash
pip install -r requirements.txt
```

4. Initialiser la base de donnees :

```bash
python app.py init-db
```

5. Lancer l'application en local :

```bash
copy .env.example .env
python app.py
```

Puis ouvrir :

http://127.0.0.1:5000

---

## Mode production

1. Copier l'exemple d'environnement :

```bash
copy .env.example .env
```

2. Modifier `.env` :
- `FLASK_ENV=production`
- `FLASK_DEBUG=0`
- `SECRET_KEY` avec une valeur forte
- `ADMIN_PASSWORD_HASH` avec un hash sécurisé
- `DATABASE` si vous souhaitez utiliser un fichier sqlite personnalisé

3. Installer les dépendances de production :

```bash
pip install -r requirements.txt
```

4. Lancer avec un serveur WSGI :

```bash
waitress-serve --listen=0.0.0.0:8000 app:app
```

Optionnel sur Linux :

```bash
gunicorn app:app
```

5. Servir l'application derriere HTTPS et appliquer des sauvegardes régulières de `database/database.db`.

---

## Variables d'environnement

- `SECRET_KEY` (requis)
- `ADMIN_PASSWORD_HASH` (requis)
- `ADMIN_USERNAME`
- `WHATSAPP_NUMBER`
- `FACEBOOK_URL`
- `INSTAGRAM_URL`
- `SHOP_NAME`
- `SHOP_ADDRESS`
- `FLASK_ENV`
- `FLASK_DEBUG`
- `PORT`
- `DATABASE`

### Generer un hash de mot de passe

```bash
python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('votre-mot-de-passe'))"
```

## Administration

URL :

http://127.0.0.1:5000/admin/login

Identifiants par defaut :

- utilisateur : `admin`
- mot de passe : `admin123`

Change ces valeurs avant la mise en production via les variables d'environnement `ADMIN_USERNAME` et `ADMIN_PASSWORD_HASH`.

## Variables utiles

- `SECRET_KEY`
- `SHOP_NAME`
- `SHOP_ADDRESS`
- `WHATSAPP_NUMBER`
- `ADMIN_USERNAME`
- `ADMIN_PASSWORD_HASH`

## WhatsApp

Le numero utilise par defaut est :

`212622135964`

Le panier est stocke cote client dans le navigateur. Quand le client clique sur "Commander sur WhatsApp", le message est genere automatiquement avec les produits, les quantites et le total.

## Notes de production

- Utiliser une vraie `SECRET_KEY`
- Utiliser un mot de passe admin fort et hashé
- Servir l'application derriere HTTPS
- Ajouter des sauvegardes regulieres de `database/database.db`
- Utiliser `waitress`, `gunicorn` ou un autre serveur WSGI en production
- Ne jamais committer `.env` dans le dépôt
