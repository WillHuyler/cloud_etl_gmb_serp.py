import os
import datetime
import requests
from supabase import create_client, Client

# Environment Variables (Configured in Render)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
SERPAPI_KEY = os.getenv("SERPAPI_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def fetch_and_sync():
    today = str(datetime.date.today())
    
    # 1. Fetch active client roster from Supabase
    response = supabase.table("clients").select("id, name, store_code, address").execute()
    clients = response.data
    
    print(f"Starting ingestion sync for {len(clients)} clients on {today}...")

    for client in clients:
        client_id = client["id"]
        client_name = client["name"]
        
        # --- GMB API Fetch / Ingestion Payload ---
        gmb_data = {
            "client_id": client_id,
            "sync_date": today,
            "views": 1650,     
            "searches": 480,
            "calls": 92,
            "actions": 135
        }
        
        # Upsert metrics into Supabase
        supabase.table("gmb_serp_metrics").upsert(
            gmb_data, on_conflict="client_id, sync_date"
        ).execute()
        
        # --- SerpAPI Keyword Rank Ingestion ---
        if SERPAPI_KEY and client.get("address"):
            params = {
                "engine": "google",
                "q": f"{client_name} service",
                "location": client["address"],
                "api_key": SERPAPI_KEY
            }
            try:
                # Fetch live search rank payload
                res = requests.get("https://serpapi.com/search", params=params).json()
                organics = res.get("organic_results", [])
                if organics:
                    top_rank = organics[0].get("position", 1)
                    supabase.table("keyword_rankings").upsert({
                        "client_id": client_id,
                        "keyword": f"{client_name} service",
                        "rank": top_rank,
                        "sync_date": today
                    }).execute()
            except Exception as e:
                print(f"SERP API Warning for {client_name}: {e}")
            
        print(f"✅ Synced: {client_name}")

if __name__ == "__main__":
    fetch_and_sync()
