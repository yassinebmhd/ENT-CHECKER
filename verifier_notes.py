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

WHATSAPP_PHONE = os.environ.get("WHATSAPP_PHONE")            # Ton chatID de groupe (ex: 120363213456789012@g.us)
GREENAPI_ID_INSTANCE = os.environ.get("GREENAPI_ID_INSTANCE")
GREENAPI_API_TOKEN = os.environ.get("GREENAPI_API_TOKEN")
GREENAPI_API_URL = os.environ.get("GREENAPI_API_URL")

if not all([IDENTIFIANT, MOT_DE_PASSE, WHATSAPP_PHONE, GREENAPI_ID_INSTANCE, GREENAPI_API_TOKEN, GREENAPI_API_URL]):
    raise SystemExit("Variables d'environnement manquantes.")

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


def charger_etat():
    if os.path.exists(FICHIER_ETAT):
        with open(FICHIER_ETAT, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
                # Assurer que les clés requises existent
                if "notes" not in data: data["notes"] = {}
                if "ticks_since_heartbeat" not in data: data["ticks_since_heartbeat"] = 0
                return data
            except json.JSONDecodeError:
                pass
    return {"notes": {}, "ticks_since_heartbeat": 0}


def sauvegarder_etat(etat):
    with open(FICHIER_ETAT, 'w', encoding='utf-8') as f:
        json.dump(etat, f, ensure_ascii=False, indent=2)


def envoyer_whatsapp(message):
    """Envoie un message WhatsApp au groupe (détecte automatiquement @g.us ou @c.us)."""
    try:
        url = f"{GREENAPI_API_URL}/waInstance{GREENAPI_ID_INSTANCE}/sendMessage/{GREENAPI_API_TOKEN}"
        
        # Flexibilité pour accepter les numéros simples comme les IDs de groupe complexes
        chat_id = WHATSAPP_PHONE if "@" in WHATSAPP_PHONE else f"{WHATSAPP_PHONE}@c.us"
        
        payload = {"chatId": chat_id, "message": message}
        response = requests.post(url, json=payload, timeout=20)
        return response.status_code == 200
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
    return webdriver.Chrome(options=options)


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
        lignes = driver.find_elements(By.CSS_SELECTOR, "tr")
        dans_semestre_4 = False

        for ligne in lignes:
            try:
                champs_texte = ligne.text.strip()
                if "semestre 4 informatique (mi)" in champs_texte.lower():
                    dans_semestre_4 = True
                    continue
                
                if dans_semestre_4 and ("semestre" in champs_texte.lower() or "etape" in champs_texte.lower()) and "semestre 4 informatique" not in champs_texte.lower():
                    break

                if dans_semestre_4:
                    cellules = ligne.find_elements(By.TAG_NAME, "td")
                    if len(cellules) >= 5:
                        libelle = cellules[2].text.strip()
                        session1_note = cellules[3].text.strip()
                        session1_resultat = cellules[4].text.strip()

                        if not libelle:
                            continue

                        for module in MODULES_A_SURVEILLER:
                            if module.lower() == libelle.lower():
                                # On ne stocke le module que si une note valide est présente
                                if session1_note and session1_note not in ["", "COR", "ADM"]:
                                    notes_modules_surveilles[module] = True
            except Exception:
                continue

        return notes_modules_surveilles
    except Exception as e:
        print(f"Erreur vérification: {e}")
        return {}


def executer_verification():
    print(f"Vérification - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    
    etat = charger_etat()
    anciennes_notes = etat.get("notes", {})
    
    driver = None
    try:
        driver = initialiser_navigateur()

        if se_connecter(driver):
            notes_actuelles = verifier_notes(driver)
            lignes_message = []
            
            # --- Filtrage intelligent des nouveautés ---
            for module in MODULES_A_SURVEILLER:
                # Si le module a une note au run actuel
                if module in notes_actuelles:
                    # S'il n'avait pas été détecté/annoncé auparavant, c'est une nouveauté !
                    if module not in anciennes_notes:
                        lignes_message.append(f"✅ La note du module *{module}* est postée.")
                        anciennes_notes[module] = True  # Marqué comme annoncé définitivement

            # S'il y a des nouveautés, on envoie l'alerte sans afficher la valeur numérique
            if lignes_message:
                message_alerte = "\n".join(lignes_message)
                print(f"Envoi alerte nouveauté:\n{message_alerte}")
                envoyer_whatsapp(message_alerte)

            # --- Gestion de la notification d'activité (Heartbeat) toutes les heures ---
            etat["ticks_since_heartbeat"] += 1
            
            # 12 ticks * 5 min = 60 min (1 heure)
            if etat["ticks_since_heartbeat"] >= 12:
                heartbeat_text = "Le script fonctionne correctement en arrière-plan. (Vérification toutes les 5 min) 🟢"
                print("Envoi du message d'activité horaire.")
                envoyer_whatsapp(heartbeat_text)
                etat["ticks_since_heartbeat"] = 0  # Réinitialisation du compteur

            # Sauvegarde de l'état mis à jour
            etat["notes"] = anciennes_notes
            
        else:
            print("Connexion échouée, nouvel essai au prochain run.")

    except Exception as e:
        print(f"Erreur pendant l'exécution: {e}")

    finally:
        if driver:
            driver.quit()
        sauvegarder_etat(etat)


if __name__ == "__main__":
    executer_verification()
