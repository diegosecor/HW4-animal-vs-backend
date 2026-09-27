import os
import tempfile
import unittest
from unittest.mock import patch

from app import app, initialize_database


TAXON = {
    "id": 1,
    "scientific_name": "demo",
    "observations_count": 100,
    "photo_url": None,
    "photo_attribution": None,
    "source_url": "https://www.inaturalist.org/taxa/1",
}


class AppTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database_path = os.path.join(self.temporary_directory.name, "test_animal_vs.db")
        app.config["DATABASE_PATH"] = self.database_path
        initialize_database()
        self.client = app.test_client()

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_catalog_has_many_animals(self):
        response = self.client.get("/api/animals")
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.json["animals"]), 60)

    def test_catalog_search_returns_domestic_dog(self):
        response = self.client.get("/api/animals/search?q=dog")
        self.assertEqual(response.status_code, 200)
        dog = next(animal for animal in response.json["animals"] if animal["id"] == "dog")
        self.assertEqual(dog["name"], "Domestic Dog")
        self.assertEqual(dog["mass_kg"], 30)

    def test_invalid_animal_search(self):
        for url in ("/api/animals/search", "/api/animals/search?q=" + "a" * 81):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 400)
                self.assertIn("error", response.json)

    def test_empty_popular_comparisons(self):
        response = self.client.get("/api/popular-comparisons")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"comparisons": []})

        animals_response = self.client.get("/api/popular-animals")
        self.assertEqual(animals_response.status_code, 200)
        self.assertEqual(animals_response.json, {"animals": []})

    def test_invalid_inputs_do_not_create_events(self):
        for url in ("/api/compare", "/api/compare?first=dog&second=unknown", "/api/compare?first=dog&second=dog"):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 400)
                self.assertIn("error", response.json)

        popular_response = self.client.get("/api/popular-comparisons")
        self.assertEqual(popular_response.json, {"comparisons": []})

    @patch("app.get_taxon", return_value=TAXON)
    def test_dog_cat_mass_comparison_and_tracking(self, fake_taxon):
        response = self.client.get("/api/compare?first=dog&second=cat")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["stat"], "Reference body mass")
        self.assertEqual(response.json["ratio"], 7.5)
        self.assertEqual(response.json["first"]["mass_kg"], 30)
        self.assertEqual(fake_taxon.call_count, 2)

        popular_response = self.client.get("/api/popular-comparisons")
        self.assertEqual(
            popular_response.json["comparisons"],
            [{
                "first": {"id": "cat", "name": "Domestic Cat"},
                "second": {"id": "dog", "name": "Domestic Dog"},
                "count": 1,
            }],
        )
        animals_response = self.client.get("/api/popular-animals")
        self.assertEqual(
            animals_response.json["animals"],
            [
                {"animal": {"id": "cat", "name": "Domestic Cat"}, "count": 1},
                {"animal": {"id": "dog", "name": "Domestic Dog"}, "count": 1},
            ],
        )

    @patch("app.get_taxon", return_value=TAXON)
    def test_reversed_matchup_increments_same_popular_pair(self, _fake_taxon):
        self.client.get("/api/compare?first=dog&second=cat")
        self.client.get("/api/compare?first=cat&second=dog")

        popular_response = self.client.get("/api/popular-comparisons")
        comparison = popular_response.json["comparisons"][0]
        self.assertEqual(comparison["first"]["id"], "cat")
        self.assertEqual(comparison["second"]["id"], "dog")
        self.assertEqual(comparison["count"], 2)

    def test_invalid_popular_comparison_limit(self):
        for url in ("/api/popular-comparisons?limit=0", "/api/popular-comparisons?limit=9", "/api/popular-comparisons?limit=invalid"):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 400)
                self.assertIn("error", response.json)

    @patch("app.get_taxon", side_effect=TimeoutError())
    def test_upstream_failure_does_not_create_event(self, _fake_taxon):
        response = self.client.get("/api/compare?first=dog&second=cat")
        self.assertEqual(response.status_code, 503)
        self.assertIn("error", response.json)
        self.assertEqual(self.client.get("/api/popular-comparisons").json, {"comparisons": []})


if __name__ == "__main__":
    unittest.main()
