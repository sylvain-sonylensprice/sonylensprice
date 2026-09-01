from datetime import datetime
import os
import json
import requests

AMAZON_TARGETS = {
    "US": {"domain": "amazon.com", "currency": "USD", "symbol": "$"},
    "UK": {"domain": "amazon.co.uk", "currency": "GBP", "symbol": "£"},
    "DE": {"domain": "amazon.de", "currency": "EUR", "symbol": "€"},
    "ES": {"domain": "amazon.es", "currency": "EUR", "symbol": "€"},
    "FR": {"domain": "amazon.fr", "currency": "EUR", "symbol": "€"},
    "IT": {"domain": "amazon.it", "currency": "EUR", "symbol": "€"},
    "CA": {"domain": "amazon.ca", "currency": "CAD", "symbol": "CA$"},
    "AU": {"domain": "amazon.com.au", "currency": "AUD", "symbol": "AU$"},
    "IN": {"domain": "amazon.in", "currency": "INR", "symbol": "₹"},
    "SE": {"domain": "amazon.se", "currency": "SEK", "symbol": "kr"},
    "IE": {"domain": "amazon.co.uk", "currency": "GBP", "symbol": "£"}
}

def fetch_price_for_domain(lens_name, target):
    api_key = os.environ.get("RAINFOREST_API_KEY")
    if not api_key:
        print("Erreur : RAINFOREST_API_KEY non trouvée dans les secrets !")
        return None

    params = {
        "api_key": api_key,
        "type": "search",
        "amazon_domain": target["domain"],
        "search_term": lens_name
    }
    
    try:
        api_result = requests.get('https://api.rainforestapi.com/request', params=params, timeout=15)
        data = api_result.json()
        
        if "search_results" in data and len(data["search_results"]) > 0:
            first_result = data["search_results"][0]
            if "price" in first_result and "value" in first_result["price"]:
                price_val = float(first_result["price"]["value"])
                symbol = target["symbol"]
                return {
                    "newPrice": f"{price_val} {symbol}",
                    "newPriceVal": price_val,
                    "usedPrice": f"Dès {int(price_val * 0.8)} {symbol}",
                    "usedPriceVal": int(price_val * 0.8),
                    "url": first_result.get("link", "#")
                }
    except Exception as e:
        print(f"Erreur API pour {target['domain']} : {e}")
    return None

def update_global_database():
    db_file = "lenses_db.json"
    
    # Liste des objectifs à suivre (références ou noms complets)
    lenses_to_track = [
        {
            "name": "Sony FE 24-70mm F2.8 GM II",
            "ref": "SEL2470GM2",
            "brand": "Sony",
            "type": "zoom",
            "aperture": "f/2.8",
            "dxoScore": 45
        }
    ]

    try:
        with open(db_file, "r", encoding="utf-8") as f:
            database = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        database = []

    current_date_str = datetime.now().strftime("%B %Y")

    for lens_def in lenses_to_track:
        print(f"\n--- Traitement de : {lens_def['name']} ---")
        prices_by_market = {}

        for market_key, target in AMAZON_TARGETS.items():
            print(f"Interrogation de {target['domain']} ({market_key})...")
            res = fetch_price_for_domain(lens_def["name"], target)
            if res:
                prices_by_market[market_key] = res

        # Recherche si l'objectif existe déjà dans la base
        existing_item = next((item for item in database if item["name"] == lens_def["name"]), None)

        if existing_item:
            # Mise à jour des prix par marché
            existing_item["prices_by_market"] = prices_by_market
            # Maintien d'un prix de référence principal (ex: FR ou US) s'il existe
            if "FR" in prices_by_market:
                existing_item["newPrice"] = prices_by_market["FR"]["newPrice"]
                existing_item["newPriceVal"] = prices_by_market["FR"]["newPriceVal"]
                existing_item["usedPrice"] = prices_by_market["FR"]["usedPrice"]
                existing_item["usedPriceVal"] = prices_by_market["FR"]["usedPriceVal"]
                existing_item["url"] = prices_by_market["FR"]["url"]
            print(f"Mise à jour des prix pour {lens_def['name']}")
        else:
            # Création d'une nouvelle entrée complète
            fr_data = prices_by_market.get("FR", {"newPrice": "N/C", "newPriceVal": 0, "usedPrice": "N/C", "usedPriceVal": 0, "url": "#"})
            new_entry = {
                "name": lens_def["name"],
                "brand": lens_def["brand"],
                "ref": lens_def["ref"],
                "type": lens_def["type"],
                "aperture": lens_def["aperture"],
                "dxoScore": lens_def["dxoScore"],
                "newPrice": fr_data["newPrice"],
                "newPriceVal": fr_data["newPriceVal"],
                "usedPrice": fr_data["usedPrice"],
                "usedPriceVal": fr_data["usedPriceVal"],
                "url": fr_data["url"],
                "prices_by_market": prices_by_market,
                "historyData": {
                    "6M": { "labels": [current_date_str], "prices": [fr_data["newPriceVal"]] }
                }
            }
            database.append(new_entry)
            print(f"Ajout de {lens_def['name']} dans la base.")

    with open(db_file, "w", encoding="utf-8") as f:
        json.dump(database, f, ensure_ascii=False, indent=4)
    print("\nBase de données globalement synchronisée !")

if __name__ == "__main__":
    update_global_database()
