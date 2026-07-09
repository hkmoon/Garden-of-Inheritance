import unittest

from garden_of_inheritance.laws import test_mendelian_laws


class FakeApp:
    def __init__(self):
        self.archive = {}
        self.law_context_pid = None
        self._genotype_revealed = False
        self.law1_ever_discovered = False
        self.law2_ever_discovered = False
        self.law3_ever_discovered = False
        self.law2_ratio_ui = ""
        self.law3_ratio_ui = ""
        self.toasts = []
        self.status_updates = 0

    def _toast(self, msg, level=None):
        self.toasts.append((msg, level))

    def _update_law_status_label(self):
        self.status_updates += 1


def build_law1_archive():
    plants = {
        "1": {
            "id": 1,
            "traits": {"flower_color": "purple"},
            "genotype": {"A": ["A", "A"]},
            "generation": "F0",
            "alive": True,
        },
        "2": {
            "id": 2,
            "traits": {"flower_color": "white"},
            "genotype": {"A": ["a", "a"]},
            "generation": "F0",
            "alive": True,
        },
    }
    for child_id in range(100, 116):
        plants[str(child_id)] = {
            "id": child_id,
            "mother_id": 1,
            "father_id": 2,
            "traits": {"flower_color": "purple"},
            "genotype": {"A": ["A", "a"]},
            "generation": "F1",
            "alive": True,
        }
    return {"plants": plants}


class MendelianLawTests(unittest.TestCase):
    def test_invalid_archive_returns_empty_result(self):
        app = FakeApp()
        result = test_mendelian_laws(app, archive=None, pid=100)
        self.assertEqual(result["new"], [])
        self.assertFalse(result["law1"])
        self.assertFalse(result["law2"])
        self.assertFalse(result["law3"])

    def test_law1_detects_with_string_keys_and_int_pid(self):
        app = FakeApp()
        archive = build_law1_archive()
        result = test_mendelian_laws(app, archive=archive, pid=100, toast=False)
        self.assertTrue(result["law1"])
        self.assertIn("law1", result["new"])
        self.assertEqual(result["law1_trait"], "flower_color")
        self.assertEqual(result["law1_dominant_value"], "purple")
        self.assertTrue(app.law1_ever_discovered)
        self.assertEqual(app.status_updates, 1)

    def test_genotype_reveal_blocks_discovery_credit(self):
        app = FakeApp()
        app._genotype_revealed = True
        archive = build_law1_archive()
        result = test_mendelian_laws(app, archive=archive, pid=100, toast=False)
        self.assertFalse(result["law1"])
        self.assertEqual(result["new"], [])
        self.assertFalse(app.law1_ever_discovered)


if __name__ == "__main__":
    unittest.main()

