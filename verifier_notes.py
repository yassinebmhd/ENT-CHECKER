import time
import json
import os
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import requests

# --- Configuration (lue depuis les variables d'environnement / GitHub Secrets) ---
IDENTIFIANT = os.environ.get("ENT_IDENTIFIANT")
MOT_DE_PASSE = os.environ.get("ENT_MOT_DE_PASSE")

WHATSAPP_PHONE = os.environ.get("WHATSAPP_PHONE")            # ex: "212612345678" (sans + ni espaces)
GREENAPI_ID_INSTANCE = os.environ.get("GREENAPI_ID_INSTANCE")        # copié depuis la console green-api.com
GREENAPI_API_TOKEN = os.environ.get("GREENAPI_API_TOKEN")            # copié depuis la console green-api.com
GREENAPI_API_URL = os.environ.get("GREENAPI_API_URL")                # copié depuis la console green-api.com

if not all([IDENTIFIANT, MOT_DE_PASSE, WHATSAPP_PHONE, GREENAPI_ID_INSTANCE, GREENAPI_API_TOKEN, GREENAPI_API_URL]):
    raise SystemExit(
        "Variables d'environnement manquantes. "
        "Vérifie que ENT_IDENTIFIANT, ENT_MOT_DE_PASSE, WHATSAPP_PHONE, GREENAPI_ID_INSTANCE, "
        "GREENAPI_API_TOKEN et GREENAPI_API_URL sont bien définies (en local via export, "
        "ou dans les Secrets GitHub Actions)."
    )

MODULES_A_SURVEILLER = [
    "Programmation Objet  avec C++",
    "Bases de données relationnelles",
    "Système d'exploitation  2",
    "Programmation Web 2",
    "Structures de données",
    "Analyse Numérique",
    "Français"
]

FICHIER_ETAT = "etat_notes.json"
ENVOYER_STATUT_TOUS_LES = 3  # envoie un message de statut WhatsApp tous les N checks réussis


def charger_etat():
    if os.path.exists(FICHIER_ETAT):
        with open(FICHIER_ETAT, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"notes": {}, "total_verifications": 0}


def sauvegarder_etat(etat):
    with open(FICHIER_ETAT, 'w', encoding='utf-8') as f:
        json.dump(etat, f, ensure_ascii=False, indent=2)


def envoyer_whatsapp(message):
    """Envoie un message WhatsApp via Green API (plan Developer gratuit, instance liée à ton WhatsApp)."""
    try:
        url = f"{GREENAPI_API_URL}/waInstance{GREENAPI_ID_INSTANCE}/sendMessage/{GREENAPI_API_TOKEN}"
        payload = {"chatId": f"{WHATSAPP_PHONE}@c.us", "message": message}
        response = requests.post(url, json=payload, timeout=20)
        ok = response.status_code == 200
        if not ok:
            print(f"Green API a répondu {response.status_code}: {response.text[:300]}")
        return ok
    except Exception as e:
        print(f"Erreur envoi WhatsApp: {e}")
        return False


def initialiser_navigateur():
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')

    # Selenium Manager (intégré depuis Selenium 4.6+) détecte/télécharge automatiquement
    # le chromedriver compatible avec le Chrome installé, en local comme sur GitHub Actions.
    driver = webdriver.Chrome(options=options)
    return driver


def se_connecter(driver):
    try:
        print("Connexion...")

        driver.get("https://ent.univcasa.ma")
        time.sleep(5)

        bouton_connexion = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.LINK_TEXT, "Connexion"))
        )
        bouton_connexion.click()
        time.sleep(5)

        champ_identifiant = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "username"))
        )
        champ_identifiant.clear()
        champ_identifiant.send_keys(IDENTIFIANT)

        champ_mdp = driver.find_element(By.ID, "password")
        champ_mdp.clear()
        champ_mdp.send_keys(MOT_DE_PASSE)

        bouton_submit = driver.find_element(By.NAME, "submitBtn")
        bouton_submit.click()
        time.sleep(5)

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.LINK_TEXT, "Notes et résultats"))
        )

        print("Connecté")
        return True

    except Exception as e:
        print(f"Erreur connexion: {e}")
        return False


def verifier_notes(driver):
    try:
        print("Vérification des notes...")

        lien_notes = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.LINK_TEXT, "Notes et résultats"))
        )
        lien_notes.click()
        time.sleep(3)

        lien_2eme_annee = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "2ème année Informatique"))
        )
        lien_2eme_annee.click()
        time.sleep(3)

        notes_modules_surveilles = {}

        # On récupère toutes les lignes du tableau pour pouvoir les analyser dans l'ordre
        lignes = driver.find_elements(By.CSS_SELECTOR, "tr")

        print(f"\n{len(lignes)} lignes de tableau trouvées")
        print("=" * 50)

        dans_semestre_4 = False

        for ligne in lignes:
            try:
                champs_texte = ligne.text.strip()
                
                # Activation du filtre dès qu'on croise l'en-tête du Semestre 4
                if "semestre 4 informatique (mi)" in champs_texte.lower():
                    dans_semestre_4 = True
                    print("📌 Entrée dans la section : Semestre 4 Informatique (MI)")
                    continue  # Passe à la ligne suivante (les modules)
                
                # Si on croise un AUTRE semestre après avoir activé le S4, on peut arrêter la recherche
                if dans_semestre_4 and ("semestre" in champs_texte.lower() or "etape" in champs_texte.lower()) and "semestre 4 informatique" not in champs_texte.lower():
                    # Optionnel : casser la boucle si d'autres semestres suivent plus bas
                    break

                # On ne traite les modules que si la ligne appartient à la zone Semestre 4
                if dans_semestre_4:
                    cellules = ligne.find_elements(By.TAG_NAME, "td")
                    if len(cellules) >= 5:
                        libelle = cellules[2].text.strip()
                        session1_note = cellules[3].text.strip()
                        session1_resultat = cellules[4].text.strip()

                        # Si la cellule libellé est vide, ce n'est pas un module valide
                        if not libelle:
                            continue

                        if session1_note and session1_note not in ["", "COR", "ADM"]:
                            print(f"✓ [S4] {libelle}: {session1_note} ({session1_resultat})")
                        else:
                            print(f"⏳ [S4] {libelle}: Pas de note")

                        for module in MODULES_A_SURVEILLER:
                            # Utilisation d'une égalité stricte (==) au lieu de (in) pour éviter les faux positifs comme "Français"
                            if module.lower() == libelle.lower():
                                if session1_note and session1_note not in ["", "COR", "ADM"]:
                                    notes_modules_surveilles[module] = {
                                        'libelle_complet': libelle,
                                        'note': session1_note,
                                        'resultat': session1_resultat,
                                        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                    }
            except Exception as e:
                continue

        print("=" * 50)
        return notes_modules_surveilles

    except Exception as e:
        print(f"Erreur vérification: {e}")
        return {}


def comparer_et_notifier(anciennes_notes, nouvelles_notes):
    notes_trouvees = []

    for module, infos in nouvelles_notes.items():
        if module not in anciennes_notes:
            notes_trouvees.append({'module': module, 'libelle': infos['libelle_complet']})

    if notes_trouvees:
        print(f"\n{len(notes_trouvees)} nouvelle(s) note(s) trouvée(s)")
        for pub in notes_trouvees:
            message = (
                f"✅ La note du module *{pub['module']}* est postée.\n\n"
                f"🕐 {datetime.now().strftime('%d/%m/%Y %H:%M')}"
            )
            envoyer_whatsapp(message)

    return len(notes_trouvees) > 0


def executer_verification():
    print("=" * 50)
    print(f"Vérification - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"Modules: {', '.join(MODULES_A_SURVEILLER)}")
    print("=" * 50)

    etat = charger_etat()
    anciennes_notes = etat.get("notes", {})

    driver = None
    try:
        driver = initialiser_navigateur()

        if se_connecter(driver):
            notes_actuelles = verifier_notes(driver)

            # --- Construction du message personnalisé ---
            lignes_message = []
            
            for module in MODULES_A_SURVEILLER:
                # Étape 1 : Vérifier si une note a été trouvée lors du run actuel
                if module in notes_actuelles:
                    note_recue = notes_actuelles[module]['note']
                    
                    # Optionnel : Si la note n'était pas présente dans l'historique précédent, c'est une VRAIE nouveauté
                    if module not in anciennes_notes:
                        lignes_message.append(f"{module} : Note postée, vous avez eu : {note_recue}.")
                    else:
                        # Si elle était déjà là au run d'avant, on l'affiche simplement comme postée
                        lignes_message.append(f"{module} : Note postée ({note_recue}).")
                else:
                    # Étape 2 : Pas de note trouvée au run actuel
                    lignes_message.append(f"{module} : Encore Pas de note.")

            # Assemblage final du bloc de texte à envoyer à chaque relance
            message_whatsapp = "\n".join(lignes_message)
            
            print("\n--- Message WhatsApp envoyé ---")
            print(message_whatsapp)
            print("--------------------------------")
            
            # Envoi systématique à chaque exécution du script
            envoyer_whatsapp(message_whatsapp)

            # Mises à jour de sécurité pour sauvegarder l'état
            notes_fusionnees = dict(anciennes_notes)
            notes_fusionnees.update(notes_actuelles)

            etat["notes"] = notes_fusionnees
            etat["total_verifications"] = etat.get("total_verifications", 0) + 1
            etat["derniere_verification"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        else:
            print("Connexion échouée pour ce passage, on réessaiera au prochain run planifié.")

    except Exception as e:
        print(f"Erreur pendant la vérification: {e}")

    finally:
        if driver:
            driver.quit()
        sauvegarder_etat(etat)


if __name__ == "__main__":
    executer_verification()
