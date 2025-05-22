import aiohttp

BASE_URL = "https://api.semanticscholar.org/graph/v1/paper/search"

DEFAULT_FIELDS = "title,authors,year,url"
DEFAULT_LIMIT = 5


async def search_papers(query: str, limit: int = 5):
    params = {
        "query": query,
        "limit": limit,
        "fields": "title,authors,year,url",
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(BASE_URL, params=params) as response:
            print(f"Status: {response.status}")  # ✅ лог
            data = await response.json()
            print(data)  # ✅ лог
            if response.status != 200:
                return []
            return data.get("data", [])

