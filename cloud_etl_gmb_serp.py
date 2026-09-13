import os
import requests
from supabase import create_client, Client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
SERPAPI_KEY = os.getenv("SERPAPI_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def fetch_serp_rank(keyword, client_name, location_target):
    """Scan local pack and organic results safely handling string or dict items"""
    url = "https://serpapi.com/search"
    params = {
        "engine": "google",
        "q": keyword,
        "location": location_target,
        "api_key": SERPAPI_KEY
    }
    
    try:
        res = requests.get(url, params=params).json()
    except Exception as e:
        print(f"API request failed for {keyword}: {e}")
        return {"rank": 99, "type": "Unranked"}
    
    # 1. Check Google Local Pack (3-Pack) safely
    local_results = res.get("local_results", [])
    if isinstance(local_results, list):
        for idx, item in enumerate(local_results):
            if isinstance(item, dict):
                title = item.get("title", "")
                if isinstance(title, str) and client_name.lower() in title.lower():
                    return {"rank": idx + 1, "type": "Local Pack"}
            elif isinstance(item, str) and client_name.lower() in item.lower():
                return {"rank": idx + 1, "type": "Local Pack"}
            
    # 2. Check Organic Results safely
    organic_results = res.get("organic_results", [])
    if isinstance(organic_results, list):
        for idx, item in enumerate(organic_results):
            if isinstance(item, dict):
                title = item.get("title", "")
                snippet = item.get("snippet", "")
                if isinstance(title, str) and client_name.lower() in title.lower():
                    return {"rank": idx + 1, "type": "Organic"}
            elif isinstance(item, str) and client_name.lower() in item.lower():
                return {"rank": idx + 1, "type": "Organic"}
            
    return {"rank": 99, "type": "Unranked"}

def sync_active_keywords():
    active_terms = supabase.table("keyword_library")\
        .select("*, clients(name)")\
        .eq("is_active", True)\
        .execute().data

    print(f"Executing sync for {len(active_terms)} active keywords...")

    for row in active_terms:
        kw_id = row["id"]
        client_id = row["client_id"]
        keyword = row["keyword"]
        client_name = row["clients"]["name"] if row.get("clients") else "Client"
        
        target_location = row.get("zip_code") or row.get("location") or "United States"

        rank_data = fetch_serp_rank(keyword, client_name, target_location)

        supabase.table("rank_history").insert({
            "keyword_id": kw_id,
            "client_id": client_id,
            "serp_rank": rank_data["rank"],
            "rank_type": rank_data["type"]
        }).execute()

        print(f"Logged '{keyword}' for {client_name} at target '{target_location}': #{rank_data['rank']}")

if __name__ == "__main__":
    sync_active_keywords()
