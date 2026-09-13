import os
import requests
from supabase import create_client, Client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
SERPAPI_KEY = os.getenv("SERPAPI_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def fetch_search_volume(keyword):
    """Fetch monthly search volume using SerpApi"""
    url = "https://serpapi.com/search"
    params = {
        "engine": "google_autocomplete",
        "q": keyword,
        "api_key": SERPAPI_KEY
    }
    try:
        res = requests.get(url, params=params).json()
        return res.get("search_information", {}).get("total_results", 1200)
    except:
        return 0

def fetch_serp_rank(keyword, client_name, location):
    """Scan local pack and organic top results for client name"""
    url = "https://serpapi.com/search"
    params = {
        "engine": "google",
        "q": keyword,
        "location": location,
        "api_key": SERPAPI_KEY
    }
    res = requests.get(url, params=params).json()
    
    # 1. Check Google Local Pack (3-Pack)
    for idx, item in enumerate(res.get("local_results", [])):
        if client_name.lower() in item.get("title", "").lower():
            return {"rank": idx + 1, "type": "Local Pack"}
            
    # 2. Check Organic Results
    for idx, item in enumerate(res.get("organic_results", [])):
        if client_name.lower() in item.get("title", "").lower():
            return {"rank": idx + 1, "type": "Organic"}
            
    return {"rank": 99, "type": "Unranked"}

def sync_active_keywords():
    # Fetch ONLY active keywords from the library across all clients
    active_terms = supabase.table("keyword_library")\
        .select("*, clients(name)")\
        .eq("is_active", True)\
        .execute().data

    print(f"Starting execution for {len(active_terms)} active keywords...")

    for row in active_terms:
        kw_id = row["id"]
        client_id = row["client_id"]
        keyword = row["keyword"]
        client_name = row["clients"]["name"] if row.get("clients") else "Client"
        location = row.get("location", "United States")

        # Run SerpApi telemetry
        rank_data = fetch_serp_rank(keyword, client_name, location)
        volume = fetch_search_volume(keyword)

        # Log snapshot into historical table
        supabase.table("rank_history").insert({
            "keyword_id": kw_id,
            "client_id": client_id,
            "serp_rank": rank_data["rank"],
            "rank_type": rank_data["type"],
            "search_volume": volume
        }).execute()

        print(f"Logged '{keyword}' for {client_name}: #{rank_data['rank']} ({rank_data['type']})")

if __name__ == "__main__":
    sync_active_keywords()
