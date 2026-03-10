"""
Scraper for modern books (post-2015) via Open Library search.
Focuses on nonfiction, recent bestsellers, award winners, and
design-forward publishers (Penguin, Norton, Knopf).
"""
import requests
import time
from database import add_cover

COVERS_URL = "https://covers.openlibrary.org"

# Minimum publication year — skip anything older
MIN_YEAR = 2015

# Design-forward publishers whose covers are worth collecting
DESIGN_PUBLISHERS = [
    "Penguin Press", "Penguin Random House", "Penguin Books",
    "W. W. Norton", "Alfred A. Knopf", "Knopf",
    "Graywolf Press", "Farrar, Straus and Giroux",
    "Riverhead Books", "Vintage Books", "Pantheon",
    "Ecco", "Crown", "Scribner",
]

# Modern nonfiction with striking cover design (all post-2015)
MODERN_NONFICTION = [
    # Science & ideas
    "Sapiens Yuval Noah Harari", "Homo Deus Yuval Noah Harari",
    "Why We Sleep Matthew Walker", "The Order of Time Carlo Rovelli",
    "Entangled Life Merlin Sheldrake", "Breath James Nestor",
    "Four Thousand Weeks Oliver Burkeman", "Range David Epstein",
    "Noise Daniel Kahneman", "Think Again Adam Grant",
    "Behave Robert Sapolsky", "The Body Bill Bryson",
    "Astrophysics for People in a Hurry Neil deGrasse Tyson",
    "The Sixth Extinction Elizabeth Kolbert",
    "An Immense World Ed Yong",
    # Memoir & biography
    "Educated Tara Westover", "Becoming Michelle Obama",
    "Born a Crime Trevor Noah", "The Light We Carry Michelle Obama",
    "Greenlights Matthew McConaughey", "Crying in H Mart Michelle Zauner",
    "Between the World and Me Ta-Nehisi Coates",
    "Know My Name Chanel Miller", "Unbroken Laura Hillenbrand",
    "The Year of Magical Thinking Joan Didion",
    "I'm Glad My Mom Died Jennette McCurdy",
    "In the Dream House Carmen Maria Machado",
    "Minor Feelings Cathy Park Hong",
    "World of Wonders Aimee Nezhukumatathil",
    "Beautiful World Where Are You Sally Rooney",
    # History & culture
    "Caste Isabel Wilkerson", "The Warmth of Other Suns Isabel Wilkerson",
    "Say Nothing Patrick Radden Keefe", "Empire of Pain Patrick Radden Keefe",
    "The 1619 Project Nikole Hannah-Jones",
    "Killers of the Flower Moon David Grann",
    "The Splendid and the Vile Erik Larson",
    "Piranesi Susanna Clarke", "The Vanishing Half Brit Bennett",
    "On Earth We're Briefly Gorgeous Ocean Vuong",
    "How to Do Nothing Jenny Odell",
    "Trick Mirror Jia Tolentino",
    "Braiding Sweetgrass Robin Wall Kimmerer",
    "All About Love bell hooks",
    "The Anthropocene Reviewed John Green",
    # Design, art & creativity
    "Ways of Seeing John Berger", "Designing Your Life Bill Burnett",
    "The Art of Looking Sideways Alan Fletcher",
    "Ruined by Design Mike Monteiro",
    "How to Be an Antiracist Ibram X. Kendi",
    "Atomic Habits James Clear", "The Subtle Art of Not Giving a F*ck",
    "Maybe You Should Talk to Someone Lori Gottlieb",
    "The Creative Act Rick Rubin",
    "Stolen Focus Johann Hari",
    "Digital Minimalism Cal Newport", "Deep Work Cal Newport",
    # Recent award winners & bestsellers (post-2020)
    "Demon Copperhead Barbara Kingsolver",
    "Tomorrow and Tomorrow and Tomorrow Gabrielle Zevin",
    "Lessons in Chemistry Bonnie Garmus",
    "The Covenant of Water Abraham Verghese",
    "Yellowface R.F. Kuang",
    "Babel R.F. Kuang",
    "Trust Hernan Diaz",
    "Sea of Tranquility Emily St. John Mandel",
    "The Candy House Jennifer Egan",
    "Matrix Lauren Groff",
    "Cloud Cuckoo Land Anthony Doerr",
    "Bewilderment Richard Powers",
    "The Lincoln Highway Amor Towles",
    "Klara and the Sun Kazuo Ishiguro",
    "The Invisible Life of Addie LaRue V.E. Schwab",
    # Design-forward publishers (Knopf, Penguin, Norton recent releases)
    "Outline Rachel Cusk", "Transit Rachel Cusk", "Kudos Rachel Cusk",
    "The Overstory Richard Powers",
    "Hamnet Maggie O'Farrell",
    "Shuggie Bain Douglas Stuart",
    "A Gentleman in Moscow Amor Towles",
    "Pachinko Min Jin Lee",
    "The Underground Railroad Colson Whitehead",
    "Harlem Shuffle Colson Whitehead",
    "The Nickel Boys Colson Whitehead",
]


def search_book(query):
    """Search Open Library for a book and return cover data."""
    url = f"https://openlibrary.org/search.json?q={requests.utils.quote(query)}&limit=5"
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError):
        return None

    docs = data.get("docs", [])
    if not docs:
        return None

    # Pick the first result that has a cover and was published after MIN_YEAR
    for doc in docs:
        cover_i = doc.get("cover_i")
        if not cover_i:
            continue

        first_year = doc.get("first_publish_year")
        # For well-known books, use the most recent edition year if available
        publish_year = first_year or 0

        return {
            "title": doc.get("title", query),
            "author": ", ".join(doc.get("author_name", [])[:2]),
            "cover_id": cover_i,
            "image_url": f"{COVERS_URL}/b/id/{cover_i}-L.jpg",
            "year": str(publish_year) if publish_year else "",
            "subject": ", ".join(doc.get("subject", [])[:3]),
            "key": doc.get("key", ""),
            "publisher": ", ".join(doc.get("publisher", [])[:2]),
        }

    return None


def search_publisher_recent(publisher, limit=25):
    """Search Open Library for recent books from a specific publisher."""
    results = []
    url = (
        f"https://openlibrary.org/search.json?"
        f"q=publisher:{requests.utils.quote(publisher)}"
        f"&sort=new&limit={limit}"
    )
    try:
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError):
        return results

    for doc in data.get("docs", []):
        cover_i = doc.get("cover_i")
        first_year = doc.get("first_publish_year", 0)
        if not cover_i or not first_year or first_year < MIN_YEAR:
            continue

        results.append({
            "title": doc.get("title", ""),
            "author": ", ".join(doc.get("author_name", [])[:2]),
            "cover_id": cover_i,
            "image_url": f"{COVERS_URL}/b/id/{cover_i}-L.jpg",
            "year": str(first_year),
            "subject": ", ".join(doc.get("subject", [])[:3]),
            "key": doc.get("key", ""),
            "publisher": publisher,
        })

    return results


def scrape_bestsellers():
    """Scrape modern books: curated titles + recent releases from design-forward publishers."""
    total = 0

    # Part 1: Curated modern nonfiction & recent literary fiction
    print("  Searching curated modern titles...")
    for book_title in MODERN_NONFICTION:
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
            source="Open Library (Modern Bestsellers)",
            source_url=f"https://openlibrary.org{result['key']}",
            year=result["year"],
        )
        if added:
            total += 1
        time.sleep(0.3)

    # Part 2: Recent books from design-forward publishers
    print(f"  Searching {len(DESIGN_PUBLISHERS)} design-forward publishers...")
    for publisher in DESIGN_PUBLISHERS:
        results = search_publisher_recent(publisher, limit=25)
        for result in results:
            genre = result.get("subject", "")
            if len(genre) > 100:
                genre = genre[:100]

            added = add_cover(
                title=result["title"],
                author=result["author"],
                genre=genre,
                image_url=result["image_url"],
                source=f"Open Library ({publisher})",
                source_url=f"https://openlibrary.org{result['key']}",
                year=result["year"],
            )
            if added:
                total += 1
        print(f"    [{publisher}] Found {len(results)} modern covers")
        time.sleep(1)

    return total
