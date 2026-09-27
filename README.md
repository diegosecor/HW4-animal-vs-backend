# Animal VS · Backend

## Overview

Animal VS is a Flask JSON backend for educational animal body-mass comparisons. It contains a curated catalog of more than 60 common animals across mammals, birds, reptiles, marine animals, and invertebrates. Each catalog entry has a rounded reference mass in kilograms, while iNaturalist supplies live species metadata, photographs, and observation counts.

> Reference masses are educational approximations. They vary by age, sex, and population, and they do **not** measure strength, fighting ability, population size, abundance, or conservation status.

## Endpoints

### `GET /api/animals`
Returns the full curated mass-reference catalog.

- **Parameters:** none
- **Response:** `{"animals": [{"id": "dog", "name": "Domestic Dog", "mass_kg": 30, ...}]}`

### `GET /api/animals/search?q=<text>`
Searches the expanded mass-reference catalog by ID, common name, or scientific name.

- **Parameters:** `q`, 1–80 characters. Examples: `dog`, `tiger`, `whale`, or `Canis`.
- **Response:** up to 12 matching animals with their reference masses.
- **Example:** `GET /api/animals/search?q=dog`

### `GET /api/compare?first=<id>&second=<id>`
Compares the reference masses of two different catalog animals, enriches each with iNaturalist data, and records the completed matchup.

- **Parameters:** two distinct catalog IDs, such as `dog` and `cat`.
- **Response:** both animals, taxon metadata, mass ratio, method, and caveat.
- **Errors:** HTTP 400 for invalid selections, HTTP 503 when iNaturalist is unavailable, and HTTP 500 if the completed comparison cannot be stored.
- **Example:** `GET /api/compare?first=dog&second=cat`

### `GET /api/popular-comparisons?limit=5`
Returns the most frequently completed matchups.

- **Parameters:** optional `limit` from 1 through 8; default is 5.
- **Response:** `{"comparisons": [{"first": {...}, "second": {...}, "count": 3}]}`
- **Counting rule:** matchups are direction-independent, so Dog vs Cat and Cat vs Dog count together.

## Frontend Communication

1. As a visitor types, the frontend requests `/api/animals/search?q=...`.
2. It renders matching mass-reference animals in a custom autocomplete menu.
3. When two entries are selected, it calls `/api/compare` using their catalog IDs.
4. It displays the mass equivalence and iNaturalist species cards, then refreshes the popular-matchup ranking.

## Running Locally

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Try:

- `http://127.0.0.1:5000/api/animals/search?q=dog`
- `http://127.0.0.1:5000/api/compare?first=dog&second=cat`
- `http://127.0.0.1:5000/api/popular-comparisons`

## Comparison Storage

Completed comparisons are stored in `backend/animal_vs.db` by default and are excluded from Git. To place the SQLite file elsewhere, set `ANIMAL_VS_DATABASE`:

```powershell
$env:ANIMAL_VS_DATABASE = "C:\path\to\animal_vs.db"
python app.py
```

A Render free web service has ephemeral filesystem storage, so the local ranking can reset after a redeploy or restart. Use a managed database or persistent disk for a durable public ranking.

## Security and Reliability

- **No secrets required:** iNaturalist is public.
- **CORS:** GitHub Pages requests are allowed with `Access-Control-Allow-Origin: *`.
- **Validation:** animal IDs and ranking limits are validated server-side.
- **Caching:** successful iNaturalist lookups are held in memory for six hours.
- **Failure handling:** failed iNaturalist lookups are not recorded as completed comparisons.

## Deploying to Render

- **Build command:** `pip install -r requirements.txt`
- **Start command:** `gunicorn app:app`
- Set `API_BASE` in `frontend/app.js` to the deployed Render HTTPS URL before publishing the frontend.

## Tests

```powershell
python -m unittest discover -s tests -v
```

The suite covers the expanded catalog, catalog search, mass calculation, matchup tracking, reverse-pair aggregation, validation, and upstream failures.

## Tools and Key Prompts

**AI tool:** Claude Sonnet 4.5 through Kiro IDE.

Key prompts:

1. "I want to create a simple app that consumes a public API with animal information and compares those animals by some stat in a 'vs' style."
2. "Record the animals that people search for and count the most searched versus matchups."
3. "I like option one, but I want many more animals."

API: [iNaturalist documentation](https://api.inaturalist.org/v1/docs/) · [autocomplete example](https://api.inaturalist.org/v1/taxa/autocomplete?q=Canis%20familiaris)
