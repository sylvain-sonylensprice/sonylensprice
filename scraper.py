from datetime import datetime
import os
import json
import requests
from bs4 import BeautifulSoup

BRANDS_TO_SCRAPE = ["sony", "sigma", "tamron", "samyang", "viltrox", "laowa"]

AMAZON_DOMAINS = [
    "amazon.fr",
    "amazon.de",
    "amazon.it",
    "amazon.es",
    "amazon.co.uk",
    "amazon.com"
]

def fetch_amazon_price_via_api(lens_name):
    """
    Interroge Amazon via une API de scraping dédiée (ex: Rainforest API)
    pour récupérer le prix en euros sans se faire bloquer.
    """
    api_key = os.environ.get("RAINFOREST_API_KEY")
    
    # Si aucune clé n'est configurée, on renvoie une valeur de secours par défaut
    if not api_key:
        return {
            "newPrice": "899 €",
            "newPriceVal": 899,
            "usedPrice": "Dès 750 €",
            "usedPriceVal": 750,
            "usedState": "Bon état"
        }

    # Exemple d'appel pour l'Europe (Amazon.fr par défaut)
    params = {
        "api_key": api_key,
        "type": "search",
        "amazon_domain": "amazon.fr",
        "search_term": lens_name
    }
    
    try:
        api_result = requests.get('https://api.rainforestapi.com/request', params=params, timeout=15)
        data = api_result.json()
        
        if "search_results" in data and len(data["search_results"]) > 0:
            first_result = data["search_results"][0]
            if "price" in first_result and "value" in first_result["price"]:
                price_val = int(first_result["price"]["value"])
                return {
                    "newPrice": f"{price_val} €",
                    "newPriceVal": price_val,
                    "usedPrice": f"Dès {int(price_val * 0.8)} €",
                    "usedPriceVal": int(price_val * 0.8),
                    "usedState": "Bon état"
                }
    except Exception as e:
        print(f"Erreur API Amazon pour {lens_name} : {e}")

    return {
        "newPrice": "899 €",
        "newPriceVal": 899,
        "usedPrice": "Dès 750 €",
        "usedPriceVal": 750,
        "usedState": "Bon état"
    }

def scrape_dxomark_lenses():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    scraped_data = []
    
    for brand in BRANDS_TO_SCRAPE:
        url = f"https://www.dxomark.com/category/lens-reviews/?filter_brand={brand}"
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                continue

            soup = BeautifulSoup(response.text, "html.parser")
            articles = soup.find_all("div", class_="product-review-item")

            for article in articles:
                title_elem = article.find("h2")
                score_elem = article.find("div", class_="score")
                link_elem = article.find("a")

                if title_elem and score_elem:
                    name = title_elem.get_text(strip=True)
                    score_text = score_elem.get_text(strip=True).split("/")[0]
                    score = int(score_text) if score_text.isdigit() else 0
                    link = link_elem["href"] if link_elem else ""

                    scraped_data.append({
                        "name": name,
                        "brand": brand.capitalize(),
                        "dxoScore": score,
                        "dxoLink": link
                    })
        except Exception as e:
            print(f"Erreur DXOMark pour {brand} : {e}")

    return scraped_data

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
            # Récupération automatique du prix via l'API sécurisée
            pricing = fetch_amazon_price_via_api(lens["name"])
            
            new_entry = {
                "name": lens["name"],
                "brand": lens["brand"],
                "ref": "REF-AUTO",
                "type": "zoom" if any(z in lens["name"].lower() for z in ["zoom", "24-70", "28-75", "70-200"]) else "prime",
                "aperture": "f/2.8",
                "dxoScore": lens["dxoScore"],
                "dxoQual": "Testé",
                "dxoLink": lens["dxoLink"],
                "newPrice": pricing["newPrice"],
                "newPriceVal": pricing["newPriceVal"],
                "usedPrice": pricing["usedPrice"],
                "usedPriceVal": pricing["usedPriceVal"],
                "usedState": pricing["usedState"],
                "historyData": {
                    "1M": { "labels": ['S1', 'S2', 'S3', 'S4'], "prices": [pricing["newPriceVal"], pricing["newPriceVal"], pricing["newPriceVal"], pricing["newPriceVal"]] },
                    "6M": { "labels": [current_date_str], "prices": [pricing["newPriceVal"]] },
                    "1Y": { "labels": [current_date_str], "prices": [pricing["newPriceVal"]] },
                    "ALL": { "labels": [current_date_str], "prices": [pricing["newPriceVal"]] }
                }
            }
            database.append(new_entry)
            updated = True
            print(f"Ajouté : {lens['name']}")

    if updated:
        with open(db_file, "w", encoding="utf-8") as f:
            json.dump(database, f, ensure_ascii=False, indent=4)
        print("Base de données mise à jour.")

if __name__ == "__main__":
    latest_reviews = scrape_dxomark_lenses()
    if latest_reviews:
        update_json_database(latest_reviews)
