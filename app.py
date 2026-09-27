"""Animal VS: JSON backend for curated body-mass comparisons."""

from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from flask import Flask, jsonify, request


app = Flask(__name__)

# Reference masses are rounded educational examples in kilograms. They vary by
# age, sex, and population; iNaturalist supplies taxon data, not mass values.
ANIMALS = {
    "alligator": {"name": "American Alligator", "plural": "American alligators", "scientific_name": "Alligator mississippiensis", "mass_kg": 360},
    "ant": {"name": "Black Garden Ant", "plural": "black garden ants", "scientific_name": "Lasius niger", "mass_kg": 0.000005},
    "bat": {"name": "Little Brown Bat", "plural": "little brown bats", "scientific_name": "Myotis lucifugus", "mass_kg": 0.009},
    "bear": {"name": "Brown Bear", "plural": "brown bears", "scientific_name": "Ursus arctos", "mass_kg": 270},
    "bee": {"name": "Honey Bee", "plural": "honey bees", "scientific_name": "Apis mellifera", "mass_kg": 0.0001},
    "bison": {"name": "American Bison", "plural": "American bison", "scientific_name": "Bison bison", "mass_kg": 700},
    "butterfly": {"name": "Monarch Butterfly", "plural": "monarch butterflies", "scientific_name": "Danaus plexippus", "mass_kg": 0.0005},
    "camel": {"name": "Dromedary Camel", "plural": "dromedary camels", "scientific_name": "Camelus dromedarius", "mass_kg": 600},
    "capybara": {"name": "Capybara", "plural": "capybaras", "scientific_name": "Hydrochoerus hydrochaeris", "mass_kg": 50},
    "cat": {"name": "Domestic Cat", "plural": "domestic cats", "scientific_name": "Felis catus", "mass_kg": 4},
    "cheetah": {"name": "Cheetah", "plural": "cheetahs", "scientific_name": "Acinonyx jubatus", "mass_kg": 50},
    "chimpanzee": {"name": "Chimpanzee", "plural": "chimpanzees", "scientific_name": "Pan troglodytes", "mass_kg": 50},
    "cobra": {"name": "Indian Cobra", "plural": "Indian cobras", "scientific_name": "Naja naja", "mass_kg": 6},
    "cow": {"name": "Domestic Cow", "plural": "domestic cows", "scientific_name": "Bos taurus", "mass_kg": 650},
    "crocodile": {"name": "Nile Crocodile", "plural": "Nile crocodiles", "scientific_name": "Crocodylus niloticus", "mass_kg": 500},
    "deer": {"name": "White-tailed Deer", "plural": "white-tailed deer", "scientific_name": "Odocoileus virginianus", "mass_kg": 100},
    "dog": {"name": "Domestic Dog", "plural": "domestic dogs", "scientific_name": "Canis familiaris", "mass_kg": 30},
    "dolphin": {"name": "Bottlenose Dolphin", "plural": "bottlenose dolphins", "scientific_name": "Tursiops truncatus", "mass_kg": 200},
    "eagle": {"name": "Bald Eagle", "plural": "bald eagles", "scientific_name": "Haliaeetus leucocephalus", "mass_kg": 5},
    "elephant": {"name": "African Bush Elephant", "plural": "African bush elephants", "scientific_name": "Loxodonta africana", "mass_kg": 4000},
    "flamingo": {"name": "American Flamingo", "plural": "American flamingos", "scientific_name": "Phoenicopterus ruber", "mass_kg": 3.5},
    "frog": {"name": "American Bullfrog", "plural": "American bullfrogs", "scientific_name": "Lithobates catesbeianus", "mass_kg": 0.5},
    "giraffe": {"name": "Giraffe", "plural": "giraffes", "scientific_name": "Giraffa camelopardalis", "mass_kg": 1200},
    "goat": {"name": "Domestic Goat", "plural": "domestic goats", "scientific_name": "Capra hircus", "mass_kg": 60},
    "gorilla": {"name": "Western Gorilla", "plural": "western gorillas", "scientific_name": "Gorilla gorilla", "mass_kg": 160},
    "hippopotamus": {"name": "Hippopotamus", "plural": "hippopotamuses", "scientific_name": "Hippopotamus amphibius", "mass_kg": 1500},
    "horse": {"name": "Horse", "plural": "horses", "scientific_name": "Equus ferus caballus", "mass_kg": 500},
    "kangaroo": {"name": "Red Kangaroo", "plural": "red kangaroos", "scientific_name": "Osphranter rufus", "mass_kg": 85},
    "koala": {"name": "Koala", "plural": "koalas", "scientific_name": "Phascolarctos cinereus", "mass_kg": 12},
    "lion": {"name": "Lion", "plural": "lions", "scientific_name": "Panthera leo", "mass_kg": 190},
    "mantis": {"name": "Praying Mantis", "plural": "praying mantises", "scientific_name": "Mantis religiosa", "mass_kg": 0.005},
    "moose": {"name": "Moose", "plural": "moose", "scientific_name": "Alces alces", "mass_kg": 500},
    "mouse": {"name": "House Mouse", "plural": "house mice", "scientific_name": "Mus musculus", "mass_kg": 0.02},
    "octopus": {"name": "Common Octopus", "plural": "common octopuses", "scientific_name": "Octopus vulgaris", "mass_kg": 3},
    "orangutan": {"name": "Bornean Orangutan", "plural": "Bornean orangutans", "scientific_name": "Pongo pygmaeus", "mass_kg": 75},
    "orca": {"name": "Orca", "plural": "orcas", "scientific_name": "Orcinus orca", "mass_kg": 6000},
    "ostrich": {"name": "Common Ostrich", "plural": "common ostriches", "scientific_name": "Struthio camelus", "mass_kg": 100},
    "owl": {"name": "Great Horned Owl", "plural": "great horned owls", "scientific_name": "Bubo virginianus", "mass_kg": 1.5},
    "panda": {"name": "Giant Panda", "plural": "giant pandas", "scientific_name": "Ailuropoda melanoleuca", "mass_kg": 100},
    "peacock": {"name": "Indian Peafowl", "plural": "Indian peafowl", "scientific_name": "Pavo cristatus", "mass_kg": 5},
    "penguin": {"name": "Emperor Penguin", "plural": "emperor penguins", "scientific_name": "Aptenodytes forsteri", "mass_kg": 30},
    "pig": {"name": "Domestic Pig", "plural": "domestic pigs", "scientific_name": "Sus scrofa domesticus", "mass_kg": 100},
    "polar-bear": {"name": "Polar Bear", "plural": "polar bears", "scientific_name": "Ursus maritimus", "mass_kg": 450},
    "python": {"name": "Burmese Python", "plural": "Burmese pythons", "scientific_name": "Python bivittatus", "mass_kg": 90},
    "rabbit": {"name": "European Rabbit", "plural": "European rabbits", "scientific_name": "Oryctolagus cuniculus", "mass_kg": 2},
    "rat": {"name": "Brown Rat", "plural": "brown rats", "scientific_name": "Rattus norvegicus", "mass_kg": 0.35},
    "rhinoceros": {"name": "White Rhinoceros", "plural": "white rhinoceroses", "scientific_name": "Ceratotherium simum", "mass_kg": 2300},
    "seal": {"name": "Harbor Seal", "plural": "harbor seals", "scientific_name": "Phoca vitulina", "mass_kg": 100},
    "shark": {"name": "Great White Shark", "plural": "great white sharks", "scientific_name": "Carcharodon carcharias", "mass_kg": 900},
    "sheep": {"name": "Domestic Sheep", "plural": "domestic sheep", "scientific_name": "Ovis aries", "mass_kg": 70},
    "sloth": {"name": "Brown-throated Sloth", "plural": "brown-throated sloths", "scientific_name": "Bradypus variegatus", "mass_kg": 5},
    "snake": {"name": "Corn Snake", "plural": "corn snakes", "scientific_name": "Pantherophis guttatus", "mass_kg": 0.9},
    "squid": {"name": "Giant Squid", "plural": "giant squids", "scientific_name": "Architeuthis dux", "mass_kg": 500},
    "squirrel": {"name": "Eastern Gray Squirrel", "plural": "eastern gray squirrels", "scientific_name": "Sciurus carolinensis", "mass_kg": 0.5},
    "tiger": {"name": "Tiger", "plural": "tigers", "scientific_name": "Panthera tigris", "mass_kg": 220},
    "tortoise": {"name": "Galápagos Tortoise", "plural": "Galápagos tortoises", "scientific_name": "Chelonoidis niger", "mass_kg": 250},
    "turtle": {"name": "Green Sea Turtle", "plural": "green sea turtles", "scientific_name": "Chelonia mydas", "mass_kg": 180},
    "walrus": {"name": "Walrus", "plural": "walruses", "scientific_name": "Odobenus rosmarus", "mass_kg": 1000},
    "whale": {"name": "Blue Whale", "plural": "blue whales", "scientific_name": "Balaenoptera musculus", "mass_kg": 100000},
    "wolf": {"name": "Gray Wolf", "plural": "gray wolves", "scientific_name": "Canis lupus", "mass_kg": 45},
    "zebra": {"name": "Plains Zebra", "plural": "plains zebras", "scientific_name": "Equus quagga", "mass_kg": 350},
}

INAT_AUTOCOMPLETE_URL = "https://api.inaturalist.org/v1/taxa/autocomplete"
CACHE_SECONDS = 6 * 60 * 60
MAX_SEARCH_RESULTS = 12
MAX_POPULAR_COMPARISONS = 8
DEFAULT_DATABASE_PATH = Path(__file__).with_name("animal_vs.db")

app.config["DATABASE_PATH"] = os.environ.get("ANIMAL_VS_DATABASE", str(DEFAULT_DATABASE_PATH))
_taxon_cache: dict[str, tuple[float, dict]] = {}


def get_database_connection() -> sqlite3.Connection:
    """Return a connection to the local comparison-event database."""
    database_path = Path(app.config["DATABASE_PATH"])
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database() -> None:
    """Create and migrate the durable comparison-event table."""
    connection = get_database_connection()
    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS comparison_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                first_id TEXT NOT NULL,
                second_id TEXT NOT NULL,
                first_name TEXT,
                second_name TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        existing_columns = {row["name"] for row in connection.execute("PRAGMA table_info(comparison_events)")}
        for column_name in ("first_name", "second_name"):
            if column_name not in existing_columns:
                connection.execute(f"ALTER TABLE comparison_events ADD COLUMN {column_name} TEXT")
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS comparison_events_pair_index
            ON comparison_events (first_id, second_id)
            """
        )
        connection.commit()
    finally:
        connection.close()


def canonical_pair(first: dict, second: dict) -> tuple[dict, dict]:
    """Make a matchup direction-independent for popularity counting."""
    return tuple(sorted((first, second), key=lambda animal: animal["id"]))


def record_comparison(first: dict, second: dict) -> None:
    """Store one completed body-mass comparison event."""
    canonical_first, canonical_second = canonical_pair(first, second)
    connection = get_database_connection()
    try:
        connection.execute(
            """
            INSERT INTO comparison_events (first_id, second_id, first_name, second_name)
            VALUES (?, ?, ?, ?)
            """,
            (canonical_first["id"], canonical_second["id"], canonical_first["name"], canonical_second["name"]),
        )
        connection.commit()
    finally:
        connection.close()


def get_popular_comparisons(limit: int) -> list[dict]:
    """Return the most frequently completed matchup pairs from local storage."""
    connection = get_database_connection()
    try:
        rows = connection.execute(
            """
            SELECT first_id, second_id,
                   COALESCE(first_name, 'Animal #' || first_id) AS first_name,
                   COALESCE(second_name, 'Animal #' || second_id) AS second_name,
                   COUNT(*) AS count
            FROM comparison_events
            GROUP BY first_id, second_id, first_name, second_name
            ORDER BY count DESC, first_name ASC, second_name ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    finally:
        connection.close()

    return [
        {
            "first": {"id": row["first_id"], "name": row["first_name"]},
            "second": {"id": row["second_id"], "name": row["second_name"]},
            "count": row["count"],
        }
        for row in rows
    ]


def request_inaturalist(url: str) -> dict:
    """Fetch JSON from iNaturalist using the application's user agent."""
    api_request = Request(url, headers={"User-Agent": "AnimalVS-CMU-course-project/1.0"})
    with urlopen(api_request, timeout=8) as response:
        return json.load(response)


def get_taxon(scientific_name: str) -> dict:
    """Fetch an exact iNaturalist taxon by scientific name with a memory cache."""
    cached = _taxon_cache.get(scientific_name)
    if cached and time.time() - cached[0] < CACHE_SECONDS:
        return cached[1]

    params = {"q": scientific_name, "per_page": 10}
    payload = request_inaturalist(f"{INAT_AUTOCOMPLETE_URL}?{urlencode(params)}")
    match = next(
        (
            item for item in payload.get("results", [])
            if item.get("name", "").casefold() == scientific_name.casefold()
            and item.get("rank") in {"species", "subspecies"}
        ),
        None,
    )
    if match is None:
        raise LookupError(f"iNaturalist did not find {scientific_name}.")

    photo = match.get("default_photo") or {}
    taxon = {
        "id": match["id"],
        "scientific_name": match["name"],
        "common_name_api": match.get("preferred_common_name"),
        "observations_count": match.get("observations_count"),
        "conservation_status": (match.get("conservation_status") or {}).get("status_name"),
        "photo_url": photo.get("medium_url"),
        "photo_attribution": photo.get("attribution"),
        "source_url": f"https://www.inaturalist.org/taxa/{match['id']}",
    }
    _taxon_cache[scientific_name] = (time.time(), taxon)
    return taxon


def search_catalog(query: str) -> list[dict]:
    """Return matching entries from the expanded local mass-reference catalog."""
    normalized_query = query.casefold()
    matches = [
        {"id": animal_id, **animal}
        for animal_id, animal in ANIMALS.items()
        if normalized_query in animal_id.casefold()
        or normalized_query in animal["name"].casefold()
        or normalized_query in animal["scientific_name"].casefold()
    ]
    return sorted(matches, key=lambda animal: animal["name"])[:MAX_SEARCH_RESULTS]


@app.after_request
def allow_public_frontend(response):
    """Allow the public GitHub Pages frontend to call this public API."""
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response


@app.get("/api/animals")
def list_animals():
    """Return the entire curated mass-reference catalog."""
    return jsonify({"animals": [{"id": animal_id, **animal} for animal_id, animal in ANIMALS.items()]})


@app.get("/api/animals/search")
def animal_search():
    """Search the curated mass-reference catalog by text."""
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "Enter at least one character to search for an animal."}), 400
    if len(query) > 80:
        return jsonify({"error": "Search queries must be 80 characters or fewer."}), 400
    return jsonify({"animals": search_catalog(query)})


@app.get("/api/popular-comparisons")
def popular_comparisons():
    """Return the locally recorded matchup pairs with the highest search count."""
    requested_limit = request.args.get("limit", "5")
    try:
        limit = int(requested_limit)
    except ValueError:
        return jsonify({"error": "The limit must be a whole number."}), 400
    if not 1 <= limit <= MAX_POPULAR_COMPARISONS:
        return jsonify({"error": f"The limit must be between 1 and {MAX_POPULAR_COMPARISONS}."}), 400

    try:
        return jsonify({"comparisons": get_popular_comparisons(limit)})
    except sqlite3.Error as exc:
        app.logger.exception("Could not load popular comparisons: %s", exc)
        return jsonify({"error": "Could not load popular comparisons."}), 500


@app.get("/api/compare")
def compare():
    """Compare reference body masses and enrich both animals with live taxon data."""
    first_id = request.args.get("first", "").strip().lower()
    second_id = request.args.get("second", "").strip().lower()
    if not first_id or not second_id:
        return jsonify({"error": "Please choose two animals to compare."}), 400
    if first_id not in ANIMALS or second_id not in ANIMALS:
        return jsonify({"error": "One of the animals is not in the mass-reference catalog."}), 400
    if first_id == second_id:
        return jsonify({"error": "Please choose two different animals."}), 400

    first = {"id": first_id, **ANIMALS[first_id]}
    second = {"id": second_id, **ANIMALS[second_id]}
    try:
        first_taxon = get_taxon(first["scientific_name"])
        second_taxon = get_taxon(second["scientific_name"])
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, LookupError) as exc:
        app.logger.warning("iNaturalist lookup failed: %s", exc)
        return jsonify({"error": "Could not query iNaturalist. Please try again in a moment."}), 503

    try:
        record_comparison(first, second)
    except sqlite3.Error as exc:
        app.logger.exception("Could not record comparison: %s", exc)
        return jsonify({"error": "Could not record the completed comparison."}), 500

    ratio = first["mass_kg"] / second["mass_kg"]
    return jsonify({
        "first": {**first, "taxon": first_taxon},
        "second": {**second, "taxon": second_taxon},
        "ratio": round(ratio, 4),
        "stat": "Reference body mass",
        "unit": "kg",
        "method": "first animal mass ÷ second animal mass",
        "caveat": "Masses are rounded educational approximations from the local catalog; iNaturalist provides species data, photos, and observations, not mass or strength.",
    })


initialize_database()


if __name__ == "__main__":
    app.run(debug=True)
