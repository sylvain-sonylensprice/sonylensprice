from datetime import datetime
import json
import requests
from bs4 import BeautifulSoup

# URL spécifique des tests d'objectifs Sony sur DXOMark
DXOMARK_SONY_LENSES_URL = "https://www.dxomark.com/category/lens-reviews/?filter_brand=sony"

def scrape_dxomark_sony_lenses():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(DXOMARK_SONY_LENSES_URL, headers=headers, timeout=10)
        if response.status_code != 200:
            print(f"Erreur de connexion : Code {response.status_code}")
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        scraped_data = []
        
        # Ciblage des blocs d'articles sur DXOMark
        articles = soup.find_all("div", class_="product-review-item")

        for article in articles:
            title_elem = article.find("h2")
            score_elem = article.find("div", class_="score")
            link_elem = article.find("a")

            if title_elem and score_elem:
                name = title_elem.get_text(strip=True)
                # Nettoyage et conversion du score (ex: "37/50" -> 37)
                score_text = score_elem.get_text(strip=True).split("/")[0]
                score = int(score_text) if score_text.isdigit() else 0
                link = link_elem["href"] if link_elem else ""

                scraped_data.append({
                    "name": name,
                    "dxoScore": score,
                    "dxoLink": link
                })

        return scraped_data
    except Exception as e:
        print(f"Erreur lors du scraping : {e}")
        return []

def update_json_database(new_lenses):
    db_file = "lenses_db.json"
    try:
        with open(db_file, "r", encoding="utf-8") as f:
            database = json.load(f)
    except FileNotFoundError:
        database = []

    updated = False
    existing_names = {item["name"] for item in database}
    current_date_str = datetime.now().strftime("%B %Y")

    for lens in new_lenses:
        if lens["name"] not in existing_names:
            # Création automatique de la structure pour le site
            new_entry = {
                "name": lens["name"],
                "brand": "Sony",
                "ref": "REF-AUTO",
                "type": "zoom" if "zoom" in lens["name"].lower() or any(f in lens["name"] for f in ["24-70", "28-75", "70-200"]) else "prime",
                "aperture": "f/2.8",
                "dxoScore": lens["dxoScore"],
                "dxoQual": "Testé",
                "dxoLink": lens["dxoLink"],
                "newPrice": "1 499 €",
                "newPriceVal": 1499,
                "usedPrice": "Dès 1 290 €",
                "usedPriceVal": 1290,
                "usedState": "Bon état",
                "historyData": {
                    "1M": { "labels": ['S1', 'S2', 'S3', 'S4'], "prices": [1499, 1499, 1499, 1499] },
                    "6M": { "labels": [current_date_str], "prices": [1499] },
                    "1Y": { "labels": [current_date_str], "prices": [1499] },
                    "ALL": { "labels": [current_date_str], "prices": [1499] }
                }
            }
            database.append(new_entry)
            updated = True
            print(f"Nouvel objectif Sony détecté et ajouté : {lens['name']}")

    if updated:
        with open(db_file, "w", encoding="utf-8") as f:
            json.dump(database, f, ensure_ascii=False, indent=4)
        print("Base de données 'lenses_db.json' mise à jour avec succès.")
    else:
        print("Aucun nouvel objectif Sony trouvé.")

if __name__ == "__main__":
    latest_reviews = scrape_dxomark_sony_lenses()
    if latest_reviews:
        update_json_database(latest_reviews)
