# README.md

# 🎓 Automatisation : Alertes de Notes Universitaires

Ce projet permet de surveiller automatiquement vos notes sur le portail universitaire et de recevoir une alerte immédiate sur **Telegram** (pour le groupe) et **WhatsApp** (pour vous personnellement) dès qu'une nouvelle note est publiée.

---

## 🛠️ Installation (Étape par étape)

Suivez ces instructions pour configurer votre propre système :

### 1. Prérequis
* Avoir un compte **GitHub**.
* Avoir un bot **Telegram** (créé via @BotFather).
* Avoir un accès **GREEN-API** pour WhatsApp.

### 2. Configuration sur GitHub
Pour que le programme fonctionne, vous devez enregistrer vos informations de manière sécurisée.
1. Allez dans votre dépôt sur GitHub.
2. Cliquez sur l'onglet **Settings** (Paramètres).
3. Dans la colonne de gauche, allez dans **Secrets and variables** > **Actions**.
4. Cliquez sur **New repository secret** et ajoutez les informations suivantes une par une :

| Nom du Secret | Description |
| :--- | :--- |
| `CAS_URL` | L'adresse de la page de connexion de votre université. |
| `CAS_USERNAME` | Votre identifiant étudiant. |
| `CAS_PASSWORD` | Votre mot de passe. |
| `TELEGRAM_BOT_TOKEN` | Le jeton de votre bot Telegram. |
| `TELEGRAM_CHAT_ID` | L'ID du groupe Telegram. |
| `GREEN_API_INSTANCE_ID` | Votre ID d'instance GREEN-API. |
| `GREEN_API_TOKEN_INSTANCE` | Votre jeton d'instance GREEN-API. |
| `TARGET_PHONE_NUMBER` | Votre numéro de téléphone au format international (ex: 2126XXXXXXXX). |

### 3. Activer le système
* **Manuellement :** Allez dans l'onglet **Actions** de votre dépôt, cliquez sur "Check University Marks", puis sur le bouton **Run workflow**.
* **Automatiquement :** Le système est configuré pour être déclenché par un outil externe (comme *cron-job.org*) via l'URL de l'API fournie par GitHub.

---

## 💡 Comment ça marche ?
1. Le programme se connecte au site de l'université.
2. Il vérifie la liste des modules.
3. Si une nouvelle note est trouvée :
    * Il envoie une alerte simple sur **Telegram**.
    * Il vous envoie le détail complet (Note + Statut) sur **WhatsApp**.
4. Il enregistre la note pour ne pas vous renvoyer la même alerte la prochaine fois.

---
