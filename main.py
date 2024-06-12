# ce code a pour vue de faire une liste des formations d'été disponibles dans le domaine de l'intelligence artificielle indiquées sur le site internet summerschoolsineurope, les données sont récupérées en anglais puis traduites en français
import re
import requests
from bs4 import BeautifulSoup
import csv
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from datetime import datetime

    # on enlève les points-virgule des chaînes de caractères récupérées car c'est le symbole qu'on a choisi pour indiquer les changements de colonne
def nettoyage(texte):
    return ' '.join(texte.split()).replace(';', ',')

    # on fait un ensemble de fonctions qui convertissent différentes monnaies en euros
def convertir_GBP_en_EUR(montant_GBP):
    taux_change = 1.19
    montant_EUR = montant_GBP * taux_change
    return montant_EUR

def convertir_DKK_en_EUR(montant_DKK):
    taux_change = 1 / 7.46
    montant_EUR = montant_DKK * taux_change
    return montant_EUR

def convertir_SEK_en_EUR(montant_SEK):
    taux_change = 11.26
    montant_EUR = montant_SEK / taux_change
    return montant_EUR

def convertir_CZK_en_EUR(montant_CZK):
    taux_change = 24.7
    montant_EUR = montant_CZK / taux_change
    return montant_EUR

    # on analyse le prix envoyé puis on réagit en fonction de la conversion à appliquer
def convertir_prix_en_euros(prix):
    correspondance = re.match(r'(\w{3}) (\d+(?:\.\d+)?)', prix)
    if correspondance:
        devise, montant = correspondance.groups()
        montant = float(montant)
        
        if devise == 'GBP':
            montant_eur = convertir_GBP_en_EUR(montant)
        elif devise == 'DKK':
            montant_eur = convertir_DKK_en_EUR(montant)
        elif devise == 'SEK':
            montant_eur = convertir_SEK_en_EUR(montant)
        elif devise == 'CZK':
            montant_eur = convertir_CZK_en_EUR(montant)
        else:
            montant_eur = montant
        
            # on arrondit le résultat obtenu pour avoir seulement deux chiffres après la virgule
        montant_eur_arrondi = round(montant_eur, 2)
        return f"{montant_eur_arrondi:.2f} €"
    else:
        return None

    # on calcule un décart en jours entre deux dates données en anglais
def calculer_duree(debut, fin):
    try:
        date_debut = datetime.strptime(debut, '%d %B %Y')
        date_fin = datetime.strptime(fin, '%d %B %Y')
        duree = (date_fin - date_debut).days
        return duree
    except ValueError:
        return 'Erreur : durée invalide.'


    # on crée une instance AutoTokenizer à partir du modèle opus-mt-en-fr pré-entraîné à la traduction automatique anglais-français 
tokenizer = AutoTokenizer.from_pretrained("Helsinki-NLP/opus-mt-en-fr")
    # on crée une instance seq2seq un modèle de séquençage à partir du modèle opus-mt-en-fr
model = AutoModelForSeq2SeqLM.from_pretrained("Helsinki-NLP/opus-mt-en-fr")

    # fonction responsable de la traduction d'un texte de l'anglais vers le français
def traduire_texte(texte):
    inputs = tokenizer(texte, return_tensors="pt", padding=True, truncation=True)
    outputs = model.generate(**inputs, max_length=150, num_beams=4, early_stopping=True)
    return tokenizer.batch_decode(outputs, skip_special_tokens=True)[0]

    # on choisit l'url de la page du site summerschoolineurope spécialisée pour l'intelligence artificielle
url = "https://www.summerschoolsineurope.eu/search/discipline;ArtInt"
    # on simule l'utilisation par un utilisateur lambda pour éviter d'être écarté par le site avec une erreur 403
identifiant = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
}

    # on entre le nom du fichier dans lequel on voudra stocker les informations
nom_fichier = 'liste_summer_schools_ia.csv'

    # on récupère et analyse les informations voulues sur cette page 
reponse = requests.get(url, headers=identifiant)
if reponse.status_code == 200:
    soup = BeautifulSoup(reponse.content, 'html.parser')
        # on a identifié la partie générale qui prend chaque carte de chaque formation, on les sélectionne pour les regarder une par une
    liste_formations = soup.find_all('div', class_='card course article-feed masonry')

    with open(nom_fichier, mode='w', newline='', encoding='utf-8') as fichier:
        writer = csv.writer(fichier, delimiter=';')
            # on détermine les colonnes que l'on veut dans le fichier csv
        writer.writerow(['Titre', 'Pays', 'Ville', 'Début', 'Fin', 'Durée (en jours)', 'Langue', 'Nombre de crédits', 'Coût (en euros)'])

            # on lance la récupération des informations de chaque formation
        for formation in liste_formations:
                # on récupère le titre de la formation
            h3_tag = formation.find('h3')
            titre_anglais = h3_tag.text if h3_tag else 'Non-indiqué'
            titre_francais = traduire_texte(titre_anglais)

                # on récupère le lieu de la formation, qui est écrit sous la forme Ville, Pays (ex : Paris, France), donc on découpe cette information en deux colonnes à partir de la première virgule
            lieu_brut = formation.find('div', class_='location')
            lieu_anglais = lieu_brut.text if lieu_brut else 'Non-indiqué'
            pays_ville = lieu_anglais.split(', ', 1)
            if len(pays_ville) == 2:
                ville, pays = pays_ville
            else:
                ville = pays_ville[0]
                pays = 'Non-indiqué'
            ville_francais = traduire_texte(ville)
            pays_francais = traduire_texte(pays)

            details_formation = formation.find('div', class_='course-details')
            if details_formation:
                liste_details = details_formation.find_all('div', class_='detailset')

                    # on récupère la période de la formation
                
                periode_anglais = nettoyage(liste_details[1].find('span', class_='detail').text) if len(liste_details) > 1 else 'Non-indiqué'
                dates = periode_anglais.split(' - ')

                    # on récupère les dates de début et de fin
                debut = traduire_texte(dates[0]) if len(dates) > 1 else 'Non-indiqué'
                fin = traduire_texte(dates[1]) if len(dates) > 1 else 'Non-indiqué'
                
                    # on récupère la durée en jours
                duree = calculer_duree(dates[0], dates[1]) if len(dates) > 1 else 'Non-indiqué'

                    # ce code est écrit en 2024, on choisit de garder seulement les formations qui se passent en 2024 ou 2025, sinon, on n'écrit rien dans le fichier
                if "2024" not in periode_anglais and "2025" not in periode_anglais:
                    continue

                    # on récupère la langue de la formation
                langues_autorisees = ["Anglais", "Italien", "Français", "Espagnol", "Albanais", "Estonien", "Allemand", "Esperanto"]
                langue_anglais = nettoyage(liste_details[2].find('span', class_='detail').text) if len(liste_details) > 2 else 'Non-indiqué'
                    # on remarque que opus-mt-en-fr traduit mal le mot "English" en français, donc on écrit directement dans ce cas
                if "English" in langue_anglais or "english" in langue_anglais :
                    langue_francais = "Anglais"
                else :
                    langue_francais = traduire_texte(langue_anglais)
                    print(langue_francais)
                        # on a remarqué qu'il y a trop de risque de mal traduction pour les langues, donc dans le cas où la langue donnée ne correspond à aucune relevée comme étant valide en se basant sur les langues trouvées sur le site précédemment, on indiquera 'Non-indiqué' par sécurité, mais également dans le cas où cette information n'ait pas été entré, ce qui casserait la structure repérée d'une fiche d'information sur une formation
                    if langue_francais not in langues_autorisees :
                        langue_francais = 'Non-indiqué'

                    # on récupère le nombre de crédits apporté(s) par la formation
                if len(liste_details) > 3:
                    credits_detail = liste_details[3].find('span', class_='detail').text
                    if 'EC' in credits_detail:
                        credits = nettoyage(credits_detail)
                        cout = nettoyage(liste_details[4].find('span', class_='detail').text) if len(liste_details) > 4 else 'Non-indiqué'
                    else:
                            # on traite le cas où la formation n'apporte aucun crédit
                        credits = '0 EC'
                        cout = nettoyage(credits_detail)
                else:
                    credits = 'Non-indiqué'
                    cout = 'Non-indiqué'

                    # on récupère le coût de la formation  
                cout_eur = convertir_prix_en_euros(cout)

            else:
                debut = 'Non-indiqué'
                fin = 'Non-indiqué'
                duree = 'Non-indiqué'
                langue_francais = 'Non-indiqué'
                credits = 'Non-indiqué'
                cout = 'Non-indiqué'
                cout_eur = 'Non-indiqué'

                # on écrit la ligne que l'on vient de regarder dans le fichier csv aux bonnes colonnes
            writer.writerow([f"{titre_francais} ({titre_anglais})", pays_francais, ville_francais, debut, fin, duree, langue_francais, credits, cout_eur])
    
        # on renvoie un message de réussite si tout cela a pu s'effectuer sans accroc
    print(f"Les données ont été enregistrées dans le fichier : {nom_fichier}")
else:
    print(f"Erreur : {reponse.status_code}")
