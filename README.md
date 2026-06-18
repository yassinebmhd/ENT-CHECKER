# Surveillance des notes ENT → notification WhatsApp (gratuit, 24/7, sans PC allumé)

## Ce qui a changé par rapport à ton script original

- WhatsApp (via Green API)** : les notifications passent par [Green API](https://green-api.com), qui propose un plan "Developer" gratuit à vie (jusqu'à 3 chats — largement suffisant pour s'envoyer des messages à soi-même). C'est un vrai service avec une infrastructure dédiée, pas un projet personnel d'un seul développeur — donc plus fiable dans le temps.
- **Boucle infinie → exécution unique** : le script ne fait plus `while True` + `sleep(300)`. Il fait une vérification puis s'arrête. C'est GitHub Actions qui le relance automatiquement toutes les ~10 minutes, même quand ton PC est éteint.
- **Identifiants en dur → variables d'environnement** : plus de mot de passe écrit dans le code. Tout passe par des "Secrets" GitHub, chiffrés et jamais affichés, même si le repo est public.
- **État fusionné au lieu d'écrasé** : si un passage de scraping a un souci ponctuel, une note déjà détectée n'est plus perdue.

## Étape 1 — Active Green API (WhatsApp)

1. Va sur https://green-api.com et crée un compte gratuit.
2. Dans la console, crée une instance avec le plan **Developer** (gratuit, limité à 3 chats — parfait pour toi-même).
3. La console affiche un **QR code** : scanne-le depuis WhatsApp sur ton téléphone (Réglages → Appareils connectés → Connecter un appareil), exactement comme pour WhatsApp Web. Ton instance est alors liée à ton propre numéro WhatsApp.
4. Dans la console, note 3 valeurs : `idInstance`, `apiTokenInstance`, et `apiUrl` (l'URL est spécifique à ton instance, copie-la exactement comme affichée).
5. Note aussi ton propre numéro de téléphone au format international sans `+` ni espaces, ex. `212612345678` — c'est le numéro à qui le message sera envoyé (toi-même).

## Étape 2 — Crée un repo GitHub (public)

1. Crée un compte sur https://github.com si tu n'en as pas.
2. Crée un nouveau repository, **public** (pour profiter des minutes GitHub Actions illimitées et gratuites — tes secrets resteront privés même en public).
3. Mets-y ces 4 fichiers en gardant l'arborescence :
   - `verifier_notes.py`
   - `requirements.txt`
   - `etat_notes.json`
   - `.github/workflows/check_notes.yml`

## Étape 3 — Configure les secrets

Dans le repo : **Settings → Secrets and variables → Actions → New repository secret**, ajoute :

| Nom du secret | Valeur |
|---|---|
| `ENT_IDENTIFIANT` | ton identifiant ENT (ex. `YASSINE.BOUMAHDI2-ETU`) |
| `ENT_MOT_DE_PASSE` | ton mot de passe ENT |
| `WHATSAPP_PHONE` | ton numéro international, ex. `212612345678` |
| `GREENAPI_ID_INSTANCE` | la valeur `idInstance` de la console Green API |
| `GREENAPI_API_TOKEN` | la valeur `apiTokenInstance` de la console Green API |
| `GREENAPI_API_URL` | la valeur `apiUrl` de la console Green API |

## Étape 4 — Teste manuellement

1. Onglet **Actions** du repo → workflow "Verification notes ENT" → bouton **Run workflow** (à droite).
2. Regarde les logs : tu dois voir "Connecté", puis la liste des modules.
3. Si tout est bon, tu reçois un message WhatsApp dès qu'une nouvelle note apparaît, et un message de statut toutes les 3 vérifications (~30 min).

## Étape 5 — C'est tout

Une fois le test validé, le workflow se déclenche seul toutes les 10 minutes (`.github/workflows/check_notes.yml`), 24h/24, sans que ton PC soit allumé. Chaque exécution committe `etat_notes.json` à jour — ce qui a un effet bonus : ça garde le repo "actif", ce qui évite que GitHub désactive automatiquement les workflows planifiés après 60 jours sans activité.

## Réglages possibles

- **Fréquence** : dans `check_notes.yml`, remplace la ligne `cron` par `'*/5 * * * *'` pour viser 5 minutes (le minimum technique chez GitHub). Attendu : des décalages occasionnels de quelques minutes en période de forte charge — ce n'est pas garanti à la seconde, mais largement suffisant pour des notes.
- **Fréquence des messages de statut** : modifie `ENVOYER_STATUT_TOUS_LES` dans `verifier_notes.py`.
- **Modules surveillés** : modifie la liste `MODULES_A_SURVEILLER` dans `verifier_notes.py`.

## Limites à connaître

- Green API fonctionne en émulant une session WhatsApp Web liée à ton numéro : c'est non-officiel (pas l'API Business de Meta), donc en théorie WhatsApp pourrait restreindre un usage trop intensif — mais pour quelques messages par jour, le risque est négligeable.
- Le plan Developer gratuit limite à 3 chats actifs, ce qui te suffit largement puisque tu t'envoies des messages à toi-même.
- Pas d'envoi à un groupe WhatsApp avec cette config (le `chatId` actuel cible ton propre numéro). Si tu veux notifier aussi un groupe, le plan Developer de Green API peut en théorie gérer un `@g.us` en plus — dis-moi si tu veux que je l'ajoute.
- Pas de screenshot envoyé (la capture d'écran a été retirée du script — Green API peut techniquement envoyer des fichiers, mais ça complexifie le script pour un gain limité ; dis-moi si tu la veux malgré tout).
- GitHub Actions planifié n'est pas garanti à la minute près (délais possibles en cas de forte charge sur l'infrastructure GitHub) — pour un usage comme le suivi de notes, ce n'est pas un problème.
- Si jamais Green API pose aussi problème, l'alternative la plus robuste à long terme est l'API officielle WhatsApp Cloud de Meta (gratuite via un "numéro de test" limité à 5 destinataires vérifiés) — plus longue à mettre en place (création d'une app Meta, validation d'un modèle de message), mais garantie par Meta elle-même plutôt que par un tiers.
