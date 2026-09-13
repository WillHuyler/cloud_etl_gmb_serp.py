import os
import requests
from supabase import create_client, Client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
SERPAPI_KEY = os.getenv("SERPAPI_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def fetch_serp_data(keyword, client_name, location_target):
    """Scan local pack/organic results, extract top 3 competitors, and capture search volume"""
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
        return {"rank": 99, "type": "Unranked", "volume": 0, "competitors": []}
    
    # Extract search volume estimate
    search_volume = res.get("search_information", {}).get("total_results", 0)

    client_rank = 99
    rank_type = "Unranked"
    competitors = []

    # 1. Parse Google Local Pack (3-Pack)
    local_results = res.get("local_results", [])
    if isinstance(local_results, list):
        for idx, item in enumerate(local_results):
            if isinstance(item, dict):
                title = item.get("title", "Unknown Business")
                if len(competitors) < 3 and client_name.lower() not in title.lower():
                    competitors.append(f"#{idx+1} {title}")
                if client_name.lower() in title.lower() and client_rank == 99:
                    client_rank = idx + 1
                    rank_type = "Local Pack"

    # 2. Parse Organic Results if local pack didn't yield top 3
    organic_results = res.get("organic_results", [])
    if isinstance(organic_results, list):
        for idx, item in enumerate(organic_results):
            if isinstance(item, dict):
                title = item.get("title", "Unknown Site")
                if len(competitors) < 3 and client_name.lower() not in title.lower():
                    competitors.append(f"Org #{idx+1} {title[:30]}")
                if client_name.lower() in title.lower() and client_rank == 99:
                    client_rank = idx + 1
                    rank_type = "Organic"

    return {
        "rank": client_rank,
        "type": rank_type,
        "volume": search_volume,
        "competitors": competitors[:3]
    }

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

        telemetry = fetch_serp_data(keyword, client_name, target_location)

        supabase.table("rank_history").insert({
            "keyword_id": kw_id,
            "client_id": client_id,
            "serp_rank": telemetry["rank"],
            "rank_type": telemetry["type"],
            "search_volume": telemetry["volume"],
            "top_competitors": telemetry["competitors"]
        }).execute()

        print(f"Logged '{keyword}' | Rank #{telemetry['rank']} | Competitors: {telemetry['competitors']}")

if __name__ == "__main__":
    sync_active_keywords()
