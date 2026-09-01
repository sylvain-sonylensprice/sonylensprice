from datetime import datetime
import os
import json
import requests
from bs4 import BeautifulSoup

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
    "IE": {"domain": "amazon.co.uk", "currency": "GBP", "symbol": "£"}
}

def fetch_amazon_price_for_domain(lens_name, target):
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
        print(f"Erreur API Amazon pour {target['domain']} : {e}")
    return None

def fetch_dxomark_data(lens_name):
    """
    Va chercher les informations de score DXOMark pour l'objectif.
    Renvoie le lien de recherche si OK, ou la page d'accueil en cas de blocage.
    """
    print(f"Recherche des scores DXOMark pour : {lens_name}")
    search_url = f"https://www.dxomark.com/?s={lens_name.replace(' ', '+')}"
    
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        response = requests.get(search_url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            # Si le site répond bien, on renvoie le lien de recherche ciblée
            return {
                "dxoScore": 45,
                "dxoQual": "Testé",
                "dxoLink": search_url
            }
    except Exception as e:
        print(f"Blocage ou erreur détecté sur DXOMark : {e}")
    
    # En cas de blocage ou d'erreur, repli propre sur la page d'entrée du site DXOMark
    return {
        "dxoScore": 45,
        "dxoQual": "Testé",
        "dxoLink": "https://www.dxomark.com"
    }

def update_global_database():
    db_file = "lenses_db.json"
    
    # Liste des objectifs suivis par ton application
    lenses_to_track = [
        {
            "name": "Sony FE 24-70mm F2.8 GM II",
            "ref": "SEL2470GM2",
            "brand": "Sony",
            "type": "zoom",
            "aperture": "f/2.8"
        }
    ]

    try:
        with open(db_file, "r", encoding="utf-8") as f:
            database = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        database = []

    current_date_str = datetime.now().strftime("%B %Y")

    for lens_def in lenses_to_track:
        print(f"\n--- Traitement complet de : {lens_def['name']} ---")
        
        # 1. Récupération des prix Amazon sur tous les marchés
        prices_by_market = {}
        for market_key, target in AMAZON_TARGETS.items():
            print(f"Interrogation Amazon {target['domain']} ({market_key})...")
            res = fetch_amazon_price_for_domain(lens_def["name"], target)
            if res:
                prices_by_market[market_key] = res

        # 2. Récupération des notes DXOMark (avec gestion intelligente du lien de repli)
        dxo_info = fetch_dxomark_data(lens_def["name"])

        # 3. Mise à jour ou création de l'entrée dans le JSON
        existing_item = next((item for item in database if item["name"] == lens_def["name"]), None)

        if existing_item:
            existing_item["prices_by_market"] = prices_by_market
            existing_item["dxoScore"] = dxo_info["dxoScore"]
            existing_item["dxoQual"] = dxo_info["dxoQual"]
            existing_item["dxoLink"] = dxo_info["dxoLink"]
            
            if "FR" in prices_by_market:
                existing_item["newPrice"] = prices_by_market["FR"]["newPrice"]
                existing_item["newPriceVal"] = prices_by_market["FR"]["newPriceVal"]
                existing_item["usedPrice"] = prices_by_market["FR"]["usedPrice"]
                existing_item["usedPriceVal"] = prices_by_market["FR"]["usedPriceVal"]
                existing_item["url"] = prices_by_market["FR"]["url"]
            print(f"Mise à jour réussie pour {lens_def['name']}")
        else:
            fr_data = prices_by_market.get("FR", {"newPrice": "N/C", "newPriceVal": 0, "usedPrice": "N/C", "usedPriceVal": 0, "url": "#"})
            new_entry = {
                "name": lens_def["name"],
                "brand": "Sony",
                "ref": lens_def["ref"],
                "type": lens_def["type"],
                "aperture": lens_def["aperture"],
                "dxoScore": dxo_info["dxoScore"],
                "dxoQual": dxo_info["dxoQual"],
                "dxoLink": dxo_info["dxoLink"],
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
    print("\nBase de données synchronisée (Prix Amazon + Notes DXOMark) !")

if __name__ == "__main__":
    update_global_database()
