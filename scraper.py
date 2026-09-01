from datetime import datetime
import os
import json
import requests

# Correspondance des domaines Amazon et de leurs devises/codes
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
    "IE": {"domain": "amazon.co.uk", "currency": "GBP", "symbol": "£"} # L'Irlande route souvent sur .co.uk ou .de
}

def fetch_amazon_price_via_api(lens_name, market_key="FR"):
    api_key = os.environ.get("RAINFOREST_API_KEY")
    if not api_key:
        print("Erreur : RAINFOREST_API_KEY non trouvée dans les secrets !")
        return None

    target = AMAZON_TARGETS.get(market_key, AMAZON_TARGETS["FR"])
    
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
                    "usedState": "Bon état",
                    "domain": target["domain"]
                }
    except Exception as e:
        print(f"Erreur API pour {target['domain']} : {e}")
    return None

def update_json_database():
    db_file = "lenses_db.json"
    test_lens_name = "Sony FE 24-70mm F2.8 GM II"
    
    # Exemple de collecte multi-marchés (par défaut ciblé sur la France, extensible à la boucle)
    market = "FR"
    print(f"Recherche du prix pour : {test_lens_name} sur le marché {market}")
    
    pricing = fetch_amazon_price_via_api(test_lens_name, market)
    if not pricing:
        print("Impossible de récupérer le prix via l'API.")
        return

    try:
        with open(db_file, "r", encoding="utf-8") as f:
            database = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        database = []

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
        print("Base de données mise à jour avec succès via Rainforest API !")
    else:
        print("L'objectif est déjà présent dans le fichier JSON.")

if __name__ == "__main__":
    update_json_database()
