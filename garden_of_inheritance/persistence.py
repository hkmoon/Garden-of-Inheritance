"""Persistence, archive, and save-file helpers."""

from __future__ import annotations

import datetime
import json
import logging
import os
import re

from tkinter import messagebox

from inventory import Pollen, Seed
from plant import Plant


def upsert_archive_snapshot(archive: dict, plant, extras=None) -> bool:
    """Upsert a single plant snapshot into an archive dictionary."""

    def get_value(obj, key, default=None):
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    try:
        plants = archive.setdefault("plants", {})
        pid = get_value(plant, "id", None)
        if pid is None:
            return False

        snap = {
            "id": pid,
            "generation": get_value(plant, "generation", get_value(plant, "gen", "F?")),
            "mother_id": get_value(plant, "mother_id", get_value(plant, "motherId", None)),
            "father_id": get_value(plant, "father_id", get_value(plant, "fatherId", None)),
            "traits": get_value(plant, "traits", {}) or {},
            "ancestry": list(get_value(plant, "ancestry", []) or []),
            "paternal_ancestry": list(get_value(plant, "paternal_ancestry", []) or []),
        }

        try:
            if str(snap.get("generation", "")).upper() == "F0":
                if not snap.get("ancestry"):
                    snap["ancestry"] = [pid]
                if not snap.get("paternal_ancestry"):
                    snap["paternal_ancestry"] = [pid]
        except Exception:
            pass

        genotype = get_value(plant, "genotype", None)
        if genotype:
            snap["genotype"] = genotype

        source_pod_index = get_value(plant, "source_pod_index", None)
        if source_pod_index is not None:
            snap["source_pod_index"] = source_pod_index

        snap.update(extras or {})
        existing = plants.get(str(pid))
        if isinstance(existing, dict):
            merged = dict(existing)
            merged.update(snap)
            snap = merged
        plants[str(pid)] = snap
        return True
    except Exception:
        return False


def sanitize_filename(name: str) -> str:
    """Normalize a user-facing save name into a filesystem-safe suffix."""
    name = (name or "").replace(" ", "_")
    name = re.sub(r"[^a-zA-Z0-9_-]", "", name)
    return name[:50]


def _timestamp_display(timestamp_str: str, include_seconds: bool = True) -> str:
    try:
        if len(timestamp_str) == 15:
            date_part = timestamp_str[:8]
            time_part = timestamp_str[9:]
            display_date = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]}"
            if include_seconds:
                display_time = f"{time_part[:2]}:{time_part[2:4]}:{time_part[4:6]}"
            else:
                display_time = f"{time_part[:2]}:{time_part[2:4]}"
            return f"{display_date} {display_time}"
    except Exception:
        pass
    return "Unknown date"


def find_save_by_name(data_dir: str, garden_name: str):
    """Find an existing save file by stored garden name."""
    try:
        for filename in os.listdir(data_dir):
            if not (filename.startswith("garden_") and filename.endswith(".json")):
                continue
            filepath = os.path.join(data_dir, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as handle:
                    save_data = json.load(handle)
            except Exception:
                continue

            stored_name = save_data.get("garden_name")
            if stored_name and stored_name.strip().lower() == garden_name.strip().lower():
                name_part = filename.replace("garden_", "").replace(".json", "")
                timestamp_str = name_part[-15:] if len(name_part) >= 15 else ""
                return {
                    "filename": filename,
                    "filepath": filepath,
                    "garden_name": stored_name,
                    "display_date": _timestamp_display(timestamp_str, include_seconds=True),
                }
        return None
    except Exception as exc:
        logging.warning("Error searching for existing save: %s", exc)
        return None


def cleanup_unnamed_saves(data_dir: str, keep_last: int = 10) -> None:
    """Keep only the newest unnamed autosaves."""
    try:
        unnamed_saves = []
        for filename in os.listdir(data_dir):
            if not (filename.startswith("garden_") and filename.endswith(".json")):
                continue
            name_part = filename.replace("garden_", "").replace(".json", "")
            if len(name_part) == 15 and name_part[8] == "_":
                filepath = os.path.join(data_dir, filename)
                unnamed_saves.append((filename, filepath, os.path.getmtime(filepath)))

        unnamed_saves.sort(key=lambda item: item[2])
        if len(unnamed_saves) > keep_last:
            for filename, filepath, _mtime in unnamed_saves[:-keep_last]:
                try:
                    os.remove(filepath)
                    logging.info("Deleted old unnamed save: %s", filename)
                except Exception as exc:
                    logging.warning("Failed to delete old save %s: %s", filename, exc)
    except Exception as exc:
        logging.warning("Failed to cleanup unnamed saves: %s", exc)


def list_save_files(data_dir: str):
    """List named and unnamed saves with display metadata."""
    named_saves = []
    unnamed_saves = []

    if not os.path.exists(data_dir):
        return {"named": named_saves, "unnamed": unnamed_saves}

    for filename in os.listdir(data_dir):
        if not (filename.startswith("garden_") and filename.endswith(".json")):
            continue

        filepath = os.path.join(data_dir, filename)
        mtime = os.path.getmtime(filepath)
        name_part = filename.replace("garden_", "").replace(".json", "")

        try:
            with open(filepath, "r", encoding="utf-8") as handle:
                save_data = json.load(handle)
            stored_name = save_data.get("garden_name")
        except Exception:
            stored_name = None

        if stored_name:
            timestamp_str = name_part[-15:] if len(name_part) >= 15 else ""
            named_saves.append(
                {
                    "garden_name": stored_name,
                    "filename": filename,
                    "filepath": filepath,
                    "mtime": mtime,
                    "timestamp": timestamp_str,
                    "display_name": (
                        f"{stored_name} ({_timestamp_display(timestamp_str, include_seconds=False)})"
                        if timestamp_str
                        else stored_name
                    ),
                }
            )
        else:
            unnamed_saves.append(
                {
                    "filename": filename,
                    "filepath": filepath,
                    "mtime": mtime,
                    "display_name": _timestamp_display(name_part, include_seconds=True)
                    if len(name_part) == 15 and "_" in name_part
                    else filename,
                }
            )

    named_saves.sort(key=lambda item: item["mtime"], reverse=True)
    unnamed_saves.sort(key=lambda item: item["mtime"], reverse=True)
    return {"named": named_saves, "unnamed": unnamed_saves}


def serialize_garden_state(app, rows: int, cols: int):
    """Serialize the current garden state into the existing save structure."""
    plants_data = []
    for tile in app.tiles:
        if tile.plant and tile.plant.alive:
            plants_data.append(
                {
                    "tile_idx": tile.idx,
                    "id": tile.plant.id,
                    "generation": tile.plant.generation,
                    "stage": tile.plant.stage,
                    "alive": tile.plant.alive,
                    "days_since_planting": tile.plant.days_since_planting,
                    "health": tile.plant.health,
                    "water": tile.plant.water,
                    "traits": tile.plant.traits,
                    "revealed_traits": tile.plant.revealed_traits,
                    "reveal_order": tile.plant.reveal_order,
                    "entered_stage5_age": tile.plant.entered_stage5_age,
                    "max_age_days": tile.plant.max_age_days,
                    "senescent": tile.plant.senescent,
                    "germination_delay": tile.plant.germination_delay,
                    "pending_cross": tile.plant.pending_cross,
                    "pollinated": tile.plant.pollinated,
                    "emasculated": tile.plant.emasculated,
                    "emasc_day": tile.plant.emasc_day,
                    "emasc_phase": tile.plant.emasc_phase,
                    "selfing_frac_before_emasc": tile.plant.selfing_frac_before_emasc,
                    "pods_total": tile.plant.pods_total,
                    "pods_remaining": tile.plant.pods_remaining,
                    "ovules_per_pod": tile.plant.ovules_per_pod,
                    "ovules_left": tile.plant.ovules_left,
                    "aborted_ovules": tile.plant.aborted_ovules,
                    "fully_harvested": getattr(tile.plant, "fully_harvested", False),
                    "ancestry": tile.plant.ancestry,
                    "paternal_ancestry": tile.plant.paternal_ancestry,
                    "genotype": getattr(tile.plant, "genotype", None),
                    "last_anther_check_day": tile.plant.last_anther_check_day,
                    "anthers_available_today": tile.plant.anthers_available_today,
                    "anthers_collected_day": tile.plant.anthers_collected_day,
                    "mother_id": getattr(tile.plant, "mother_id", None),
                    "father_id": getattr(tile.plant, "father_id", None),
                    "selfed": getattr(tile.plant, "selfed", False),
                    "source_pod_index": getattr(tile.plant, "source_pod_index", None),
                    "is_weak": getattr(tile.plant, "is_weak", False),
                    "weak_blocks_flowering": getattr(tile.plant, "weak_blocks_flowering", False),
                    "late_season_stress": getattr(tile.plant, "late_season_stress", False),
                }
            )

    inventory_data = {
        "seeds": [
            {
                "name": seed.name,
                "id": seed.id,
                "source_id": seed.source_id,
                "donor_id": seed.donor_id,
                "traits": seed.traits,
                "generation": seed.generation,
                "pod_index": seed.pod_index,
                "genotype": seed.genotype,
                "ancestry": seed.ancestry,
            }
            for seed in app.harvest_inventory
        ],
        "pollen": [
            {
                "name": pollen.name,
                "id": pollen.id,
                "source_id": pollen.source_id,
                "collected_day": pollen.collected_day,
                "expires_day": pollen.expires_day,
                "genotype": pollen.genotype,
                "traits": pollen.traits,
            }
            for pollen in app.inventory.get_all("pollen")
        ],
    }

    garden_data = {
        "day": app.garden.day,
        "phase_index": app.garden.phase_index,
        "phase": app.garden.phase,
        "clock_hour": app.garden.clock_hour,
        "year": app.garden.year,
        "month": app.garden.month,
        "day_of_month": app.garden.day_of_month,
        "weather": app.garden.weather,
        "temp": app.garden.temp,
        "target_temps": getattr(app.garden, "target_temps", {}),
        "temp_updates_remaining": getattr(app.garden, "temp_updates_remaining", 3),
    }

    temp_tracker_data = None
    if getattr(app, "temp_tracker", None):
        temp_tracker_data = {
            "measurements": app.temp_tracker.measurements,
            "modern_measurements": getattr(app.temp_tracker, "modern_measurements", []),
        }

    archive_data = None
    if isinstance(getattr(app, "archive", None), dict):
        archive_data = {
            "plants": {str(key): value for key, value in app.archive.get("plants", {}).items()}
        }

    lineage_store_data = None
    if isinstance(getattr(app, "lineage_store", None), dict):
        lineage_store_data = {
            "plants": {
                str(key): value for key, value in app.lineage_store.get("plants", {}).items()
            }
        }

    return {
        "version": "v1.0",
        "save_date": datetime.datetime.now().isoformat(),
        "plants": plants_data,
        "inventory": inventory_data,
        "garden": garden_data,
        "history": list(getattr(app.garden, "history", [])),
        "archive": archive_data,
        "lineage_store": lineage_store_data,
        "law_flags": {
            "law1_ever_discovered": getattr(app, "law1_ever_discovered", False),
            "law2_ever_discovered": getattr(app, "law2_ever_discovered", False),
            "law3_ever_discovered": getattr(app, "law3_ever_discovered", False),
            "law1_first_plant": getattr(app, "law1_first_plant", None),
            "law2_first_plant": getattr(app, "law2_first_plant", None),
            "law3_first_plant": getattr(app, "law3_first_plant", None),
            "law2_ratio_ui": getattr(app, "law2_ratio_ui", ""),
            "law3_ratio_ui": getattr(app, "law3_ratio_ui", ""),
            "_genotype_revealed": getattr(app, "_genotype_revealed", False),
        },
        "next_plant_id": getattr(app, "next_plant_id", 1),
        "temperature_tracker": temp_tracker_data,
        "ui_settings": {
            "running": app.running,
            "enable_daynight": app.enable_daynight,
            "auto_water_ff": app.auto_water_ff.get(),
            "auto_water_normal": app.auto_water_normal.get(),
            "auto_record_temperature": app.auto_record_temperature.get(),
            "show_breed_dialogs": app.show_breed_dialogs.get(),
            "available_seeds": app.available_seeds,
            "grid_rows": rows,
            "grid_cols": cols,
        },
    }


def deserialize_garden_state(app, save_data, rows: int, cols: int) -> None:
    """Restore garden state from an existing serialized save dictionary."""
    for tile in app.tiles:
        if tile.plant is not None:
            try:
                app.garden.unregister_plant(tile.plant)
            except Exception:
                pass
        tile.plant = None
    try:
        app.garden.plants.clear()
    except Exception:
        pass

    garden_data = save_data["garden"]
    app.garden.day = garden_data.get("day", 1)
    app.garden.phase_index = garden_data.get("phase_index", 0)
    app.garden.phase = garden_data.get("phase", "morning")
    app.garden.clock_hour = garden_data.get("clock_hour", 6)
    app.garden.year = garden_data.get("year", 1856)
    app.garden.month = garden_data.get("month", 4)
    app.garden.day_of_month = garden_data.get("day_of_month", 1)
    app.garden.weather = garden_data.get("weather", "☀️")
    app.garden.temp = garden_data.get("temp", 12.0)
    if "target_temps" in garden_data:
        app.garden.target_temps = garden_data["target_temps"]
    if "temp_updates_remaining" in garden_data:
        app.garden.temp_updates_remaining = garden_data["temp_updates_remaining"]

    if not hasattr(app.garden, "history"):
        app.garden.history = []
    app.garden.history = save_data.get("history", [])

    if not hasattr(app, "archive"):
        app.archive = {}
    archive_data = save_data.get("archive")
    app.archive["plants"] = archive_data.get("plants", {}) if isinstance(archive_data, dict) else {}

    if not hasattr(app, "lineage_store"):
        app.lineage_store = {}
    lineage_store_data = save_data.get("lineage_store")
    app.lineage_store["plants"] = (
        lineage_store_data.get("plants", {}) if isinstance(lineage_store_data, dict) else {}
    )
    for key, value in app.archive.get("plants", {}).items():
        app.lineage_store["plants"].setdefault(str(key), value)

    law_flags = save_data.get("law_flags", {})
    app.law1_ever_discovered = law_flags.get("law1_ever_discovered", False)
    app.law2_ever_discovered = law_flags.get("law2_ever_discovered", False)
    app.law3_ever_discovered = law_flags.get("law3_ever_discovered", False)
    app.law1_first_plant = law_flags.get("law1_first_plant", None)
    app.law2_first_plant = law_flags.get("law2_first_plant", None)
    app.law3_first_plant = law_flags.get("law3_first_plant", None)
    app.law2_ratio_ui = law_flags.get("law2_ratio_ui", "Ratio __:__")
    app.law3_ratio_ui = law_flags.get("law3_ratio_ui", "Ratio __:__:__:__")
    app._genotype_revealed = law_flags.get("_genotype_revealed", False)
    app.next_plant_id = save_data.get("next_plant_id", 1)

    if save_data.get("temperature_tracker") and getattr(app, "temp_tracker", None):
        temp_data = save_data["temperature_tracker"]
        app.temp_tracker.measurements = temp_data.get("measurements", [])
        app.temp_tracker.modern_measurements = temp_data.get("modern_measurements", [])

    ui_settings = save_data.get("ui_settings", {})
    app.running = ui_settings.get("running", False)
    app.enable_daynight = ui_settings.get("enable_daynight", True)
    app.auto_water_ff.set(ui_settings.get("auto_water_ff", False))
    app.auto_water_normal.set(ui_settings.get("auto_water_normal", False))
    app.auto_record_temperature.set(ui_settings.get("auto_record_temperature", True))
    app.show_breed_dialogs.set(ui_settings.get("show_breed_dialogs", True))
    app.available_seeds = ui_settings.get("available_seeds", 10)

    saved_rows = ui_settings.get("grid_rows", rows)
    saved_cols = ui_settings.get("grid_cols", cols)
    if saved_rows != rows or saved_cols != cols:
        messagebox.showwarning(
            "Grid Size Mismatch",
            f"Save file has {saved_rows}x{saved_cols} grid, but current is {rows}x{cols}.\n\n"
            "Plants will be loaded where possible.",
        )

    inventory_data = save_data["inventory"]
    app.inventory._items_seeds.clear()
    app.harvest_inventory.clear()
    seeds_to_restore = inventory_data.get("seeds", [])
    logging.info("Restoring %s seeds from save file", len(seeds_to_restore))
    for seed_data in seeds_to_restore:
        try:
            seed = Seed(
                name=seed_data.get("name", f"Seed_{seed_data['id']}"),
                id=seed_data["id"],
                source_id=seed_data["source_id"],
                donor_id=seed_data.get("donor_id"),
                traits=seed_data.get("traits", {}),
                generation=seed_data.get("generation", 0),
                pod_index=seed_data.get("pod_index", 0),
                genotype=seed_data.get("genotype", {}),
                ancestry=seed_data.get("ancestry", []),
            )
            app.inventory._items_seeds.append(seed)
            app.harvest_inventory.append(seed)
        except Exception as exc:
            logging.warning("Failed to restore seed: %s", exc)

    app.inventory._items_pollen.clear()
    for pollen_data in inventory_data.get("pollen", []):
        try:
            pollen = Pollen(
                name=pollen_data.get("name", f"Pollen_{pollen_data['id']}"),
                id=pollen_data["id"],
                source_plant=None,
                collection_time=0,
                source_id=pollen_data.get("source_id", 0),
                collected_day=pollen_data.get("collected_day", 0),
                expires_day=pollen_data.get("expires_day", 0),
                genotype=pollen_data.get("genotype", {}),
                traits=pollen_data.get("traits", {}),
            )
            app.inventory._items_pollen.append(pollen)
        except Exception as exc:
            logging.warning("Failed to restore pollen: %s", exc)

    for plant_data in save_data["plants"]:
        tile_idx = plant_data["tile_idx"]
        if tile_idx >= len(app.tiles):
            continue
        tile = app.tiles[tile_idx]
        plant = Plant(
            id=plant_data["id"],
            env=app.garden,
            generation=plant_data["generation"],
        )
        plant.stage = plant_data["stage"]
        plant.alive = plant_data["alive"]
        plant.days_since_planting = plant_data["days_since_planting"]
        plant.health = plant_data["health"]
        plant.water = plant_data["water"]
        plant.traits = plant_data["traits"]
        plant.revealed_traits = plant_data["revealed_traits"]
        plant.reveal_order = plant_data["reveal_order"]
        plant.entered_stage5_age = plant_data.get("entered_stage5_age")
        plant.max_age_days = plant_data["max_age_days"]
        plant.senescent = plant_data["senescent"]
        plant.germination_delay = plant_data["germination_delay"]
        plant.pending_cross = plant_data.get("pending_cross")
        plant.pollinated = plant_data["pollinated"]
        plant.emasculated = plant_data["emasculated"]
        plant.emasc_day = plant_data.get("emasc_day")
        plant.emasc_phase = plant_data.get("emasc_phase")
        plant.selfing_frac_before_emasc = plant_data["selfing_frac_before_emasc"]
        plant.pods_total = plant_data["pods_total"]
        plant.pods_remaining = plant_data["pods_remaining"]
        plant.ovules_per_pod = plant_data["ovules_per_pod"]
        plant.ovules_left = plant_data["ovules_left"]
        plant.aborted_ovules = plant_data["aborted_ovules"]
        plant.fully_harvested = plant_data.get("fully_harvested", False)
        plant.ancestry = plant_data["ancestry"]
        plant.paternal_ancestry = plant_data["paternal_ancestry"]
        if plant_data.get("genotype"):
            plant.genotype = plant_data["genotype"]
        plant.last_anther_check_day = plant_data.get("last_anther_check_day")
        plant.anthers_available_today = plant_data["anthers_available_today"]
        plant.anthers_collected_day = plant_data.get("anthers_collected_day")
        plant.mother_id = plant_data.get("mother_id")
        plant.father_id = plant_data.get("father_id")
        plant.selfed = plant_data.get("selfed", False)
        plant.is_weak = plant_data.get("is_weak", False)
        plant.weak_blocks_flowering = plant_data.get("weak_blocks_flowering", False)
        plant.late_season_stress = plant_data.get("late_season_stress", False)
        source_pod_index = plant_data.get("source_pod_index")
        if source_pod_index is not None:
            plant.source_pod_index = int(source_pod_index)
        tile.plant = plant

    if not hasattr(app, "used_ids"):
        app.used_ids = set()
    for tile in app.tiles:
        if tile.plant is not None:
            pid = getattr(tile.plant, "id", None)
            if pid is not None:
                try:
                    app.used_ids.add(int(pid))
                except Exception:
                    pass
    for key in app.archive.get("plants", {}):
        try:
            app.used_ids.add(int(key))
        except Exception:
            pass
    if app.used_ids:
        app.next_plant_id = max(app.next_plant_id, max(app.used_ids) + 1)

    try:
        app._eager_seed_and_backfill()
    except Exception:
        pass

    app.render_all()
    app._update_temp_button_state()
    if hasattr(app, "seed_counter_var"):
        try:
            app.seed_counter_var.set(f"Seeds: {len(app.harvest_inventory)}")
        except Exception:
            pass
    app.pause_btn.configure(text=("⏸ Pause" if app.running else "▶ Resume"))

