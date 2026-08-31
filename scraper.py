from datetime import datetime
import os
import json
import requests

def fetch_amazon_price_via_api(lens_name):
    api_key = os.environ.get("RAINFOREST_API_KEY")
    if not api_key:
        print("Erreur : RAINFOREST_API_KEY non trouvée dans les secrets !")
        return None

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
        print(f"Erreur API : {e}")
    return None

def update_json_database():
    db_file = "lenses_db.json"
    
    # On simule un objectif détecté pour tester toute la chaîne de bout en bout
    test_lens_name = "Sony FE 24-70mm F2.8 GM II"
    print(f"Recherche du prix pour : {test_lens_name}")
    
    pricing = fetch_amazon_price_via_api(test_lens_name)
    if not pricing:
        print("Impossible de récupérer le prix via l'API.")
        return

    try:
        with open(db_file, "r", encoding="utf-8") as f:
            database = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        database = []

    # Vérifie si l'objectif y est déjà
    existing_names = {item["name"] for item in database}
    current_date_str = datetime.now().strftime("%B %Y")

    if test_lens_name not in existing_names:
        new_entry = {
            "name": test_lens_name,
            "brand": "Sony",
            "ref": "SEL2470GM2",
            "type": "zoom",
            "aperture": "f/2.8",
            "dxoScore": 45,
            "dxoQual": "Testé",
            "dxoLink": "https://www.dxomark.com",
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
        
        with open(db_file, "w", encoding="utf-8") as f:
            json.dump(database, f, ensure_ascii=False, indent=4)
        print("Base de données mise à jour avec succès !")
    else:
        print("L'objectif est déjà présent dans le fichier JSON.")

if __name__ == "__main__":
    update_json_database()
