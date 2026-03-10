#!/usr/bin/env python3
"""
Seed the database with curated book covers using Open Library cover IDs.
These are real Open Library cover IDs for acclaimed books with great cover designs.
Works offline - uses known cover IDs to construct URLs directly.
"""
from database import init_db, add_cover

# Format: (title, author, designer, genre, cover_id, year)
# cover_id is the Open Library cover ID (used to build image URL)
SEED_COVERS = [
    ("The Great Gatsby", "F. Scott Fitzgerald", "Francis Cugat", "Literary Fiction", 8227565, "1925"),
    ("1984", "George Orwell", "", "Dystopian Fiction", 12648655, "1949"),
    ("Brave New World", "Aldous Huxley", "", "Science Fiction", 8231432, "1932"),
    ("Fahrenheit 451", "Ray Bradbury", "Joseph Mugnaini", "Science Fiction", 8813988, "1953"),
    ("The Catcher in the Rye", "J.D. Salinger", "E. Michael Mitchell", "Literary Fiction", 8231637, "1951"),
    ("To Kill a Mockingbird", "Harper Lee", "", "Literary Fiction", 8228691, "1960"),
    ("Beloved", "Toni Morrison", "", "Literary Fiction", 8406786, "1987"),
    ("The Handmaid's Tale", "Margaret Atwood", "", "Dystopian Fiction", 8235583, "1985"),
    ("Slaughterhouse-Five", "Kurt Vonnegut", "", "Science Fiction", 8231830, "1969"),
    ("Catch-22", "Joseph Heller", "", "Satire", 8231803, "1961"),
    ("Where the Crawdads Sing", "Delia Owens", "", "Literary Fiction", 10389354, "2018"),
    ("The Night Circus", "Erin Morgenstern", "", "Fantasy", 8582891, "2011"),
    ("Circe", "Madeline Miller", "", "Fantasy", 8917876, "2018"),
    ("The Song of Achilles", "Madeline Miller", "", "Fantasy", 8579093, "2011"),
    ("Educated", "Tara Westover", "", "Memoir", 8805235, "2018"),
    ("Becoming", "Michelle Obama", "", "Memoir", 9261015, "2018"),
    ("The Goldfinch", "Donna Tartt", "", "Literary Fiction", 7887804, "2013"),
    ("A Little Life", "Hanya Yanagihara", "", "Literary Fiction", 8243643, "2015"),
    ("Normal People", "Sally Rooney", "", "Literary Fiction", 9255981, "2018"),
    ("The Silent Patient", "Alex Michaelides", "", "Thriller", 9193771, "2019"),
    ("Mexican Gothic", "Silvia Moreno-Garcia", "", "Horror", 10389974, "2020"),
    ("Piranesi", "Susanna Clarke", "", "Fantasy", 10588476, "2020"),
    ("House of Leaves", "Mark Z. Danielewski", "", "Horror", 476696, "2000"),
    ("Cloud Atlas", "David Mitchell", "", "Science Fiction", 394952, "2004"),
    ("The Shadow of the Wind", "Carlos Ruiz Zafón", "", "Mystery", 244498, "2001"),
    ("The Book Thief", "Markus Zusak", "", "Historical Fiction", 1858012, "2005"),
    ("The Overstory", "Richard Powers", "", "Literary Fiction", 8573880, "2018"),
    ("Shuggie Bain", "Douglas Stuart", "", "Literary Fiction", 10652988, "2020"),
    ("Hamnet", "Maggie O'Farrell", "", "Historical Fiction", 10389419, "2020"),
    ("Klara and the Sun", "Kazuo Ishiguro", "", "Science Fiction", 10652990, "2021"),
    ("The Vanishing Half", "Brit Bennett", "", "Literary Fiction", 10389356, "2020"),
    ("Pachinko", "Min Jin Lee", "", "Historical Fiction", 8573901, "2017"),
    ("Lincoln in the Bardo", "George Saunders", "", "Literary Fiction", 8406732, "2017"),
    ("The Underground Railroad", "Colson Whitehead", "", "Historical Fiction", 8243655, "2016"),
    ("All the Light We Cannot See", "Anthony Doerr", "", "Historical Fiction", 7887825, "2014"),
    ("The Sympathizer", "Viet Thanh Nguyen", "", "Literary Fiction", 8243710, "2015"),
    ("Dune", "Frank Herbert", "John Schoenherr", "Science Fiction", 8227948, "1965"),
    ("Neuromancer", "William Gibson", "", "Science Fiction", 8231906, "1984"),
    ("The Left Hand of Darkness", "Ursula K. Le Guin", "", "Science Fiction", 8227984, "1969"),
    ("Annihilation", "Jeff VanderMeer", "", "Science Fiction", 7887776, "2014"),
    ("The Fifth Season", "N.K. Jemisin", "", "Fantasy", 8243670, "2015"),
    ("The Starless Sea", "Erin Morgenstern", "", "Fantasy", 10389410, "2019"),
    ("Children of Time", "Adrian Tchaikovsky", "", "Science Fiction", 8243689, "2015"),
    ("Project Hail Mary", "Andy Weir", "", "Science Fiction", 10652994, "2021"),
    ("The Three-Body Problem", "Liu Cixin", "", "Science Fiction", 8011498, "2008"),
    ("Hyperion", "Dan Simmons", "", "Science Fiction", 8227989, "1989"),
    ("Foundation", "Isaac Asimov", "", "Science Fiction", 8227920, "1951"),
    ("The Shining", "Stephen King", "", "Horror", 8228500, "1977"),
    ("Bird Box", "Josh Malerman", "", "Horror", 7887863, "2014"),
    ("The Haunting of Hill House", "Shirley Jackson", "", "Horror", 8228160, "1959"),
    ("We Have Always Lived in the Castle", "Shirley Jackson", "", "Gothic Fiction", 8228156, "1962"),
    ("Gone Girl", "Gillian Flynn", "", "Thriller", 7222246, "2012"),
    ("The Girl with the Dragon Tattoo", "Stieg Larsson", "", "Thriller", 6555953, "2005"),
    ("Sapiens", "Yuval Noah Harari", "", "Non-Fiction", 8243617, "2011"),
    ("Thinking, Fast and Slow", "Daniel Kahneman", "", "Non-Fiction", 7222190, "2011"),
    ("The Design of Everyday Things", "Don Norman", "", "Design", 1858125, "1988"),
    ("Ways of Seeing", "John Berger", "", "Art Criticism", 297988, "1972"),
    ("On Photography", "Susan Sontag", "", "Photography", 297789, "1977"),
    ("Understanding Comics", "Scott McCloud", "", "Comics / Art", 89485, "1993"),
    ("Interaction of Color", "Josef Albers", "", "Design / Art", 1148413, "1963"),
    ("The Remains of the Day", "Kazuo Ishiguro", "", "Literary Fiction", 467387, "1989"),
    ("Never Let Me Go", "Kazuo Ishiguro", "", "Science Fiction", 1528580, "2005"),
    ("The Road", "Cormac McCarthy", "", "Post-Apocalyptic", 1857973, "2006"),
    ("Blood Meridian", "Cormac McCarthy", "", "Western", 467453, "1985"),
    ("Infinite Jest", "David Foster Wallace", "", "Literary Fiction", 476723, "1996"),
    ("White Teeth", "Zadie Smith", "", "Literary Fiction", 476673, "2000"),
    ("Atonement", "Ian McEwan", "", "Literary Fiction", 476641, "2001"),
    ("The Corrections", "Jonathan Franzen", "", "Literary Fiction", 476630, "2001"),
    ("The Secret History", "Donna Tartt", "", "Literary Fiction", 476699, "1992"),
    ("The Wind-Up Bird Chronicle", "Haruki Murakami", "", "Literary Fiction", 467455, "1994"),
    ("Norwegian Wood", "Haruki Murakami", "", "Literary Fiction", 467450, "1987"),
    ("Kafka on the Shore", "Haruki Murakami", "", "Literary Fiction", 1528566, "2002"),
    ("American Gods", "Neil Gaiman", "", "Fantasy", 476661, "2001"),
    ("The Name of the Wind", "Patrick Rothfuss", "", "Fantasy", 2553834, "2007"),
    ("The Lies of Locke Lamora", "Scott Lynch", "", "Fantasy", 1858078, "2006"),
    ("Station Eleven", "Emily St. John Mandel", "", "Science Fiction", 7887805, "2014"),
    ("The Martian", "Andy Weir", "", "Science Fiction", 7887780, "2011"),
    ("Dark Matter", "Blake Crouch", "", "Science Fiction", 8243651, "2016"),
    ("Recursion", "Blake Crouch", "", "Science Fiction", 9255989, "2019"),
    ("The Power", "Naomi Alderman", "", "Science Fiction", 8406780, "2016"),
    ("An American Marriage", "Tayari Jones", "", "Literary Fiction", 8805228, "2018"),
    ("Such a Fun Age", "Kiley Reid", "", "Literary Fiction", 10389349, "2019"),
    ("My Year of Rest and Relaxation", "Ottessa Moshfegh", "", "Literary Fiction", 8917864, "2018"),
    ("Severance", "Ling Ma", "", "Science Fiction", 8917871, "2018"),
    ("The Poppy War", "R.F. Kuang", "", "Fantasy", 8805260, "2018"),
    ("The City We Became", "N.K. Jemisin", "", "Fantasy", 10389367, "2020"),
    ("Ninth House", "Leigh Bardugo", "", "Fantasy", 10389382, "2019"),
    ("The Invisible Life of Addie LaRue", "V.E. Schwab", "", "Fantasy", 10389388, "2020"),
    ("Anxious People", "Fredrik Backman", "", "Literary Fiction", 10652979, "2019"),
    ("The Midnight Library", "Matt Haig", "", "Literary Fiction", 10588470, "2020"),
    ("Klara and the Sun", "Kazuo Ishiguro", "", "Literary Fiction", 10652990, "2021"),
    ("Beautiful World, Where Are You", "Sally Rooney", "", "Literary Fiction", 12648660, "2021"),
    ("The Love Songs of W.E.B. Du Bois", "Honorée Fanonne Jeffers", "", "Literary Fiction", 12648680, "2021"),
    ("Bewilderment", "Richard Powers", "", "Literary Fiction", 12648685, "2021"),
    ("The Lincoln Highway", "Amor Towles", "", "Historical Fiction", 12648670, "2021"),
    ("A Gentleman in Moscow", "Amor Towles", "", "Historical Fiction", 8243630, "2016"),
    ("Circe", "Madeline Miller", "Will Staehle", "Fantasy", 8917876, "2018"),
    ("The Seven Husbands of Evelyn Hugo", "Taylor Jenkins Reid", "", "Historical Fiction", 8573919, "2017"),
    ("Daisy Jones & The Six", "Taylor Jenkins Reid", "", "Historical Fiction", 9255968, "2019"),
    ("The Dutch House", "Ann Patchett", "", "Literary Fiction", 10389404, "2019"),
    ("Transcendent Kingdom", "Yaa Gyasi", "", "Literary Fiction", 10389357, "2020"),
    ("Homegoing", "Yaa Gyasi", "", "Historical Fiction", 8243648, "2016"),
]

COVERS_URL = "https://covers.openlibrary.org"


def seed():
    init_db()
    added = 0
    for title, author, designer, genre, cover_id, year in SEED_COVERS:
        image_url = f"{COVERS_URL}/b/id/{cover_id}-L.jpg"
        result = add_cover(
            title=title,
            author=author,
            designer=designer if designer else None,
            genre=genre,
            image_url=image_url,
            source="Open Library (Curated)",
            source_url=f"https://openlibrary.org/search?q={title.replace(' ', '+')}",
            year=year,
        )
        if result:
            added += 1
    print(f"Seeded {added} book covers into database.")


if __name__ == "__main__":
    seed()
