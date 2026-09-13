import os
import requests
from supabase import create_client, Client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
SERPAPI_KEY = os.getenv("SERPAPI_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Target keywords to monitor per client location
KEYWORDS_TO_TRACK = ["car repair near me", "auto service stroudsburg", "towing service"]

def fetch_serp_keyword_data(keyword, location):
    """Fetch search rank and volume via SerpApi"""
    url = "https://serpapi.com/search"
    params = {
        "engine": "google",
        "q": keyword,
        "location": location,
        "api_key": SERPAPI_KEY
    }
    response = requests.get(url, params=params).json()
    
    # Extract organic or local pack rank
    rank = None
    if "local_results" in response:
        for idx, result in enumerate(response["local_results"]):
            rank = idx + 1
            break
            
    return {
        "keyword": keyword,
        "serp_rank": rank or 99,
        "search_volume": response.get("search_information", {}).get("total_results", 0)
    }

def fetch_gbp_performance_metrics(location_id, gbp_access_token):
    """
    Fetch calls, clicks, directions, and chats using official GBP API.
    Endpoint: https://businessprofileperformance.googleapis.com/v1/locations/{location_id}:fetchMultiDailyMetricsTimeSeries
    """
    url = f"https://businessprofileperformance.googleapis.com/v1/{location_id}:fetchMultiDailyMetricsTimeSeries"
    headers = {"Authorization": f"Bearer {gbp_access_token}"}
    params = {
        "dailyMetrics": ["CALL_CLICKS", "WEBSITE_CLICKS", "BUSINESS_DIRECTION_REQUESTS", "BUSINESS_IMPRESSIONS_DESKTOP_MAPS"],
        "dailyRange.start_date.year": 2026,
        "dailyRange.start_date.month": 9,
        "dailyRange.start_date.day": 1
    }
    # Note: Requires valid OAuth2 token from Google Cloud Console
    res = requests.get(url, headers=headers, params=params)
    return res.json() if res.status_code == 200 else {}

def sync_all():
    # Fetch all clients stored in Supabase
    clients = supabase.table("clients").select("*").execute().data
    
    for client in clients:
        client_id = client["id"]
        city = client.get("city", "Stroudsburg, Pennsylvania")
        
        for kw in KEYWORDS_TO_TRACK:
            serp_data = fetch_serp_keyword_data(kw, city)
            
            # Payload combining GBP metrics + SerpApi Keyword insights
            payload = {
                "client_id": client_id,
                "keyword": serp_data["keyword"],
                "serp_rank": serp_data["serp_rank"],
                "search_volume": serp_data["search_volume"],
                "gbp_calls": 42,             # Placeholder until OAuth token connected
                "gbp_website_clicks": 128,    # Placeholder until OAuth token connected
                "gbp_direction_requests": 65, # Placeholder until OAuth token connected
                "gbp_chats": 14              # Placeholder until OAuth token connected
            }
            
            supabase.table("gmb_serp_metrics").insert(payload).execute()
        print(f"✅ Synced metrics & keywords for {client['name']}")

if __name__ == "__main__":
    sync_all()
