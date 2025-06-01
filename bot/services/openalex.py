import aiohttp

BASE_URL = "https://api.openalex.org/works"

async def search_openalex(query: str, per_page: int = 3, page: int = 1):
    params = {
        "search": query,
        "per_page": per_page,
        "page": page
    }

    headers = {
        "User-Agent": "GeoGuruEduBot/1.0 (mailto:samoylowfgg@gmail.com)"
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(BASE_URL, params=params) as response:
            if response.status != 200:
                print("❌ Статус ответа:", response.status)
                print("❌ Тело ответа:", await response.text())
                return []
            data = await response.json()
            return data.get("results", [])

