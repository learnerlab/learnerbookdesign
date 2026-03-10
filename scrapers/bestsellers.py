"""
Scraper for NYT Best Sellers via Open Library search.
Searches for well-known best-selling books and award winners.
"""
import requests
import time
from database import add_cover

COVERS_URL = "https://covers.openlibrary.org"

# Curated lists of acclaimed/best-selling books known for great covers
BEST_COVER_BOOKS = [
    # Modern literary fiction with notable covers
    "The Great Gatsby", "1984", "Brave New World", "Fahrenheit 451",
    "The Catcher in the Rye", "To Kill a Mockingbird", "Beloved",
    "The Handmaid's Tale", "Slaughterhouse-Five", "Catch-22",
    # Contemporary best sellers
    "Where the Crawdads Sing", "The Night Circus", "Circe",
    "The Song of Achilles", "Educated", "Becoming",
    "The Goldfinch", "A Little Life", "Normal People",
    "The Silent Patient", "Mexican Gothic", "Piranesi",
    # Design-forward covers
    "S. by J.J. Abrams", "House of Leaves", "The Raw Shark Texts",
    "Extremely Loud and Incredibly Close", "The Curious Incident",
    "Cloud Atlas", "The Shadow of the Wind", "The Book Thief",
    # Award winners (Booker, Pulitzer, National Book Award)
    "The Overstory", "Shuggie Bain", "Hamnet", "Klara and the Sun",
    "The Vanishing Half", "Transcendent Kingdom", "Pachinko",
    "Lincoln in the Bardo", "The Underground Railroad",
    "All the Light We Cannot See", "The Sympathizer",
    # Sci-fi/Fantasy with great covers
    "Dune", "Neuromancer", "The Left Hand of Darkness",
    "Annihilation", "The Fifth Season", "Piranesi",
    "The Starless Sea", "Children of Time", "Project Hail Mary",
    "The Three-Body Problem", "Hyperion", "Foundation",
    # Horror/Thriller
    "The Shining", "Bird Box", "The Haunting of Hill House",
    "We Have Always Lived in the Castle", "Beloved",
    "Gone Girl", "The Girl with the Dragon Tattoo",
    # Non-fiction with striking covers
    "Sapiens", "Thinking Fast and Slow", "The Design of Everyday Things",
    "Ways of Seeing", "On Photography", "Understanding Comics",
    "The Visual Display of Quantitative Information",
    "Interaction of Color", "Grid Systems in Graphic Design",
]


def search_book(query):
    """Search Open Library for a book and return cover data."""
    url = f"https://openlibrary.org/search.json?q={requests.utils.quote(query)}&limit=3"
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError):
        return None

    docs = data.get("docs", [])
    if not docs:
        return None

    doc = docs[0]
    cover_i = doc.get("cover_i")
    if not cover_i:
        return None

    return {
        "title": doc.get("title", query),
        "author": ", ".join(doc.get("author_name", [])[:2]),
        "cover_id": cover_i,
        "image_url": f"{COVERS_URL}/b/id/{cover_i}-L.jpg",
        "year": str(doc.get("first_publish_year", "")),
        "subject": ", ".join(doc.get("subject", [])[:3]),
        "key": doc.get("key", ""),
    }


def scrape_bestsellers():
    """Search for best-selling books with notable covers."""
    total = 0
    for book_title in BEST_COVER_BOOKS:
        result = search_book(book_title)
        if not result:
            continue

        genre = result.get("subject", "")
        if len(genre) > 100:
            genre = genre[:100]

        added = add_cover(
            title=result["title"],
            author=result["author"],
            genre=genre,
            image_url=result["image_url"],
            source="Open Library (Best Sellers)",
            source_url=f"https://openlibrary.org{result['key']}",
            year=result["year"],
        )
        if added:
            total += 1
        time.sleep(0.3)

    return total
