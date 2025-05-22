import aiohttp

BASE_URL = "https://api.openalex.org/works"

async def search_openalex(query: str, limit: int = 5):
    params = {
        "search": query,
        "per-page": limit
    }

    headers = {
        "User-Agent": "GeoGuruEduBot/1.0 (mailto:samoylowfgg@gmail.com)"
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(BASE_URL, params=params) as response:
            if response.status != 200:
                return []

            data = await response.json()
            return data.get("results", [])
