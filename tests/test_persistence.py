import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

from garden_of_inheritance.bootstrap import load_grid_config, save_grid_config
from garden_of_inheritance.persistence import (
    deserialize_garden_state,
    serialize_garden_state,
    upsert_archive_snapshot,
)
from inventory import Inventory, Pollen, Seed
from plant import Plant


class FakeVar:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class FakePauseButton:
    def __init__(self):
        self.text = None

    def configure(self, **kwargs):
        self.text = kwargs.get("text", self.text)


class FakeGarden:
    def __init__(self):
        self.plants = set()
        self.day = 3
        self.phase_index = 1
        self.phase = "noon"
        self.clock_hour = 12
        self.year = 1856
        self.month = 5
        self.day_of_month = 7
        self.weather = "☀️"
        self.temp = 19.5
        self.target_temps = {"12": 19.5}
        self.temp_updates_remaining = 2
        self.history = ["snapshot"]
        self._app = None

    def register_plant(self, plant):
        self.plants.add(plant)

    def unregister_plant(self, plant):
        self.plants.discard(plant)


class FakeApp:
    def __init__(self, with_plant=False):
        self.garden = FakeGarden()
        self.garden._app = self
        self.inventory = Inventory()
        self.harvest_inventory = []
        self.running = False
        self.enable_daynight = True
        self.auto_water_ff = FakeVar(True)
        self.auto_water_normal = FakeVar(False)
        self.auto_record_temperature = FakeVar(True)
        self.show_breed_dialogs = FakeVar(True)
        self.available_seeds = 5
        self.archive = {"plants": {}}
        self.lineage_store = {"plants": {}}
        self.law1_ever_discovered = True
        self.law2_ever_discovered = False
        self.law3_ever_discovered = False
        self.law1_first_plant = 1
        self.law2_first_plant = None
        self.law3_first_plant = None
        self.law2_ratio_ui = "Ratio __:__"
        self.law3_ratio_ui = "Ratio __:__:__:__"
        self._genotype_revealed = False
        self.next_plant_id = 2
        self.temp_tracker = SimpleNamespace(
            measurements=[{"hour": 12, "temp": 19.5}],
            modern_measurements=[{"hour": 12, "temp": 20.0}],
        )
        self.pause_btn = FakePauseButton()
        self.seed_counter_var = FakeVar("")
        self.rendered = 0
        self.temp_button_updates = 0
        self.archive_seeded = 0

        plant = None
        if with_plant:
            plant = Plant(id=1, env=self.garden, generation="F1")
            plant.stage = 7
            plant.traits = {"flower_color": "purple", "plant_height": "tall"}
            plant.revealed_traits = {"flower_color": "purple"}
            plant.reveal_order = ["flower_color"]
            plant.genotype = {"A": ["A", "a"]}
            plant.pods_total = 4
            plant.pods_remaining = 2
            plant.mother_id = 10
            plant.father_id = 11
            plant.source_pod_index = 3

            seed = Seed(
                name="Seed_1",
                id=1,
                source_id=1,
                donor_id=2,
                traits={"flower_color": "purple"},
                generation=1,
                pod_index=3,
                genotype={"A": ["A", "a"]},
                ancestry=[1, 2],
            )
            pollen = Pollen(
                name="Pollen_1",
                id=2,
                source_plant=plant,
                collection_time=0,
                collected_day=3,
                expires_day=4,
                genotype={"A": ["A", "a"]},
                traits={"flower_color": "purple"},
            )
            self.harvest_inventory.append(seed)
            self.inventory.add(pollen)
            self.archive = {"plants": {"1": {"id": 1, "traits": {"flower_color": "purple"}}}}
            self.lineage_store = {"plants": {"1": {"id": 1, "traits": {"flower_color": "purple"}}}}

        self.tiles = [SimpleNamespace(idx=0, plant=plant)]

    def render_all(self):
        self.rendered += 1

    def _update_temp_button_state(self):
        self.temp_button_updates += 1

    def _eager_seed_and_backfill(self):
        self.archive_seeded += 1


class PersistenceTests(unittest.TestCase):
    def test_archive_snapshot_merges_and_normalizes_keys(self):
        archive = {"plants": {"1": {"id": 1, "source_pod_index": 9}}}
        plant = SimpleNamespace(
            id=1,
            generation="F1",
            mother_id=10,
            father_id=11,
            traits={"flower_color": "purple"},
            ancestry=[1],
            paternal_ancestry=[2],
            genotype={"A": ["A", "a"]},
        )
        self.assertTrue(upsert_archive_snapshot(archive, plant, {"extra": "value"}))
        self.assertIn("1", archive["plants"])
        self.assertEqual(archive["plants"]["1"]["source_pod_index"], 9)
        self.assertEqual(archive["plants"]["1"]["extra"], "value")

    def test_serialize_deserialize_roundtrip_preserves_core_state(self):
        source = FakeApp(with_plant=True)
        save_data = serialize_garden_state(source, rows=7, cols=16)

        target = FakeApp(with_plant=False)
        with mock.patch("garden_of_inheritance.persistence.messagebox.showwarning"):
            deserialize_garden_state(target, save_data, rows=7, cols=16)

        self.assertEqual(len(target.harvest_inventory), 1)
        self.assertEqual(len(target.inventory.get_all("pollen")), 1)
        self.assertEqual(target.tiles[0].plant.id, 1)
        self.assertEqual(target.tiles[0].plant.source_pod_index, 3)
        self.assertEqual(target.archive["plants"]["1"]["id"], 1)
        self.assertEqual(target.pause_btn.text, "▶ Resume")
        self.assertEqual(target.rendered, 1)
        self.assertEqual(target.temp_button_updates, 1)
        self.assertEqual(target.archive_seeded, 1)

    def test_grid_config_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            anchor = f"{tmpdir}/launcher.py"
            save_grid_config(anchor, 9, 12, False)
            loaded = load_grid_config(anchor, default_rows=7, default_cols=16)
        self.assertEqual(loaded, {"rows": 9, "cols": 12, "show_dialog": False})


if __name__ == "__main__":
    unittest.main()
