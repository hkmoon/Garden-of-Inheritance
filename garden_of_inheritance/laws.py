"""Shared Mendelian-law analysis logic."""

from __future__ import annotations

from collections import Counter
from itertools import combinations


# Law 1 (Dominance): how many phenotype-only F1 offspring (same phenotype) needed
LAW1_MIN_F1 = 16

# Law 2 (Segregation, ~3:1): minimum F2 sample size and acceptable dominant fraction band
LAW2_MIN_N = 65
LAW2_DOM_FRAC_MIN = 0.677
LAW2_DOM_FRAC_MAX = 0.796

# Law 3 (Independent Assortment, ~9:3:3:1): minimum dihybrid F2 sample size and chi-square threshold
LAW3_MIN_N = 80
LAW3_CHI2_MAX = 4.0


def test_mendelian_laws(app, archive=None, pid=None, allow_credit=True, toast=True, target_law=None):
    """Run shared Mendelian-law detection against archive snapshots."""
    archive = archive if archive is not None else getattr(app, "archive", None)
    if not isinstance(archive, dict):
        return {"law1": False, "law2": False, "law3": False, "new": []}
    plants = archive.get("plants", {})
    if not isinstance(plants, dict) or not plants:
        return {"law1": False, "law2": False, "law3": False, "new": []}

    revealed = bool(getattr(app, "_genotype_revealed", False))
    if revealed and allow_credit:
        allow_credit = False

    if pid in (None, "", -1):
        pid = getattr(app, "law_context_pid", None)

    def get_snapshot(pid_):
        if pid_ in (None, "", -1):
            return None
        if pid_ in plants:
            return plants.get(pid_)
        try:
            str_id = str(pid_)
            if str_id in plants:
                return plants.get(str_id)
        except Exception:
            pass
        try:
            int_id = int(pid_)
            if int_id in plants:
                return plants.get(int_id)
        except Exception:
            pass
        return None

    snap = get_snapshot(pid)
    if not snap:
        return {"law1": False, "law2": False, "law3": False, "new": []}

    def parents_from_snapshot(snap_obj):
        if not isinstance(snap_obj, dict):
            return (getattr(snap_obj, "mother_id", None), getattr(snap_obj, "father_id", None))

        mother_keys = [
            "mother_id",
            "mother",
            "maternal_id",
            "mom_id",
            "female_parent",
            "female_id",
            "dam_id",
            "seed_parent_id",
            "seed_parent",
            "maternal_pid",
            "female",
        ]
        father_keys = [
            "father_id",
            "father",
            "paternal_id",
            "dad_id",
            "male_parent",
            "male_id",
            "sire_id",
            "pollen_donor_id",
            "pollen_source_id",
            "pollen_parent_id",
            "pollinator_id",
            "pollen_donor",
            "pollen_source",
            "pollen",
        ]
        nested_keys = [
            "pollination",
            "cross",
            "cross_info",
            "seed_source",
            "source_pod",
            "source_cross",
            "repro",
            "reproduction",
        ]

        def pick(mapping, keys):
            for key in keys:
                if isinstance(mapping, dict) and key in mapping and mapping[key] not in (None, "", -1):
                    return mapping[key]
            return None

        mother_id = pick(snap_obj, mother_keys)
        father_id = pick(snap_obj, father_keys)
        if mother_id is None or father_id is None:
            for nested_key in nested_keys:
                nested_value = snap_obj.get(nested_key)
                if isinstance(nested_value, dict):
                    if mother_id is None:
                        mother_id = pick(nested_value, mother_keys)
                    if father_id is None:
                        father_id = pick(nested_value, father_keys)
        return (mother_id, father_id)

    def get_value(snapshot, key, default=None):
        if isinstance(snapshot, dict):
            return snapshot.get(key, default)
        try:
            return getattr(snapshot, key, default)
        except Exception:
            return default

    try:
        mid, fid = parents_from_snapshot(snap)
    except Exception:
        mid, fid = (get_value(snap, "mother_id", None), get_value(snap, "father_id", None))

    try:
        traits = (
            dict(snap.get("traits", {}) or {})
            if isinstance(snap, dict)
            else dict(getattr(snap, "traits", {}) or {})
        )
    except Exception:
        traits = {}

    def genotype_from_snapshot(snapshot):
        try:
            genotype = snapshot.get("genotype") if isinstance(snapshot, dict) else getattr(snapshot, "genotype", None)
            genotype = genotype or {}
        except Exception:
            genotype = {}
        return dict(genotype) if isinstance(genotype, dict) else {}

    def law1_cross_signature_for_trait(mother_snap, father_snap, locus):
        mother_geno = genotype_from_snapshot(mother_snap)
        father_geno = genotype_from_snapshot(father_snap)
        if not isinstance(mother_geno, dict) or not isinstance(father_geno, dict):
            return None

        mother_pair = mother_geno.get(locus)
        father_pair = father_geno.get(locus)
        if not (isinstance(mother_pair, (list, tuple)) and len(mother_pair) >= 2):
            return None
        if not (isinstance(father_pair, (list, tuple)) and len(father_pair) >= 2):
            return None

        if not (mother_pair[0] == mother_pair[1] and father_pair[0] == father_pair[1]):
            return None
        if mother_pair[0] == father_pair[0]:
            return None

        def canon(pair):
            return "".join(sorted([str(pair[0]), str(pair[1])]))

        return tuple(sorted([canon(mother_pair), canon(father_pair)]))

    law1_discovered = False
    law1_trait_name = ""
    law1_dominant_value = ""
    law1_all_valid = []

    law2_discovered = False
    law2_ratio_str = ""
    law2_trait_name = ""
    law2_dominant_value = ""
    law2_all_valid = []
    law2_all_valid_ratios = {}

    law3_discovered = False
    law3_ratio_str = ""
    law3_trait_pair = ()
    law3_all_valid_pairs = []
    law3_all_valid_pairs_ratios = {}

    trait_to_locus = {
        "flower_color": "A",
        "pod_color": "Gp",
        "seed_color": "I",
        "seed_shape": "R",
        "plant_height": "Le",
    }
    law_trait_keys = ["flower_color", "pod_color", "seed_color", "seed_shape", "plant_height"]

    if not revealed:
        mother_snap = get_snapshot(mid)
        father_snap = get_snapshot(fid)
        if mother_snap and father_snap and mid not in (None, "", -1) and fid not in (None, "", -1) and str(mid) != str(fid):
            try:
                mother_traits = (
                    dict(mother_snap.get("traits", {}) or {})
                    if isinstance(mother_snap, dict)
                    else dict(getattr(mother_snap, "traits", {}) or {})
                )
            except Exception:
                mother_traits = {}
            try:
                father_traits = (
                    dict(father_snap.get("traits", {}) or {})
                    if isinstance(father_snap, dict)
                    else dict(getattr(father_snap, "traits", {}) or {})
                )
            except Exception:
                father_traits = {}

            mother_geno = genotype_from_snapshot(mother_snap)
            father_geno = genotype_from_snapshot(father_snap)
            dominant_candidates = []

            for trait_key in law_trait_keys:
                child_value = str(traits.get(trait_key, "")).strip()
                mother_value = str(mother_traits.get(trait_key, "")).strip()
                father_value = str(father_traits.get(trait_key, "")).strip()
                if not (
                    child_value
                    and mother_value
                    and father_value
                    and mother_value != father_value
                    and (child_value == mother_value or child_value == father_value)
                ):
                    continue

                locus = trait_to_locus.get(trait_key)
                if not locus:
                    continue

                cross_sig = law1_cross_signature_for_trait(mother_snap, father_snap, locus)
                if cross_sig is None:
                    continue

                mother_pair = mother_geno.get(locus)
                father_pair = father_geno.get(locus)
                if not (
                    isinstance(mother_pair, (list, tuple))
                    and len(mother_pair) >= 2
                    and isinstance(father_pair, (list, tuple))
                    and len(father_pair) >= 2
                ):
                    continue
                if not (mother_pair[0] == mother_pair[1] and father_pair[0] == father_pair[1]):
                    continue
                if mother_pair[0] == father_pair[0]:
                    continue

                same_pheno_total = 0
                for child_snap in plants.values():
                    if isinstance(child_snap, dict) and not child_snap.get("alive", True):
                        continue
                    child_mid, child_fid = parents_from_snapshot(child_snap if isinstance(child_snap, dict) else {})
                    if child_mid in (None, "", -1) or child_fid in (None, "", -1):
                        continue
                    sib_mother = get_snapshot(child_mid)
                    sib_father = get_snapshot(child_fid)
                    if not sib_mother or not sib_father:
                        continue
                    sib_sig = law1_cross_signature_for_trait(sib_mother, sib_father, locus)
                    if sib_sig is None or sib_sig != cross_sig:
                        continue
                    try:
                        sibling_traits = (
                            child_snap.get("traits", {})
                            if isinstance(child_snap, dict)
                            else getattr(child_snap, "traits", {}) or {}
                        )
                    except Exception:
                        sibling_traits = {}
                    if str(sibling_traits.get(trait_key, "")).strip() == child_value:
                        same_pheno_total += 1

                if same_pheno_total < LAW1_MIN_F1:
                    continue
                dominant_candidates.append((trait_key, child_value, same_pheno_total))

            if dominant_candidates:
                law1_discovered = True
                law1_trait_name, law1_dominant_value, _count = dominant_candidates[0]
                law1_all_valid = [(trait_key, dominant_value) for trait_key, dominant_value, _count in dominant_candidates]

    def law2_family_signature(parent_snap, grandparent_m, grandparent_f, locus):
        parent_geno = genotype_from_snapshot(parent_snap)
        parent_pair = parent_geno.get(locus)
        if not (isinstance(parent_pair, (list, tuple)) and len(parent_pair) >= 2):
            return None
        if parent_pair[0] == parent_pair[1]:
            return None

        gm_geno = genotype_from_snapshot(grandparent_m)
        gf_geno = genotype_from_snapshot(grandparent_f)
        gm_pair = gm_geno.get(locus)
        gf_pair = gf_geno.get(locus)
        if not (isinstance(gm_pair, (list, tuple)) and len(gm_pair) >= 2):
            return None
        if not (isinstance(gf_pair, (list, tuple)) and len(gf_pair) >= 2):
            return None
        if not (gm_pair[0] == gm_pair[1] and gf_pair[0] == gf_pair[1]):
            return None

        def canon(pair):
            return "".join(sorted([str(pair[0]), str(pair[1])]))

        return tuple(sorted([canon(gm_pair), canon(gf_pair)]))

    def get_grandparents(parent_snap):
        try:
            parent_mid, parent_fid = parents_from_snapshot(parent_snap)
        except Exception:
            parent_mid, parent_fid = (
                get_value(parent_snap, "mother_id", None),
                get_value(parent_snap, "father_id", None),
            )
        return get_snapshot(parent_mid), get_snapshot(parent_fid)

    try:
        has_parents = mid not in (None, "", -1) and fid not in (None, "", -1)
    except Exception:
        has_parents = False

    parent_snap_m = get_snapshot(mid) if has_parents else None
    parent_snap_f = get_snapshot(fid) if has_parents else None
    gp_m = gp_f = None
    parent_snap = None
    parent_traits = None
    if not revealed and parent_snap_m and parent_snap_f:
        parent_snap = parent_snap_m
        try:
            parent_traits = (
                dict(parent_snap.get("traits", {}) or {})
                if isinstance(parent_snap, dict)
                else dict(getattr(parent_snap, "traits", {}) or {})
            )
        except Exception:
            parent_traits = {}
        gp_m, gp_f = get_grandparents(parent_snap)

    if not revealed and parent_snap and gp_m and gp_f:
        parent_geno = genotype_from_snapshot(parent_snap)
        for trait_key in law_trait_keys:
            locus = trait_to_locus.get(trait_key)
            if not locus:
                continue
            fam_sig = law2_family_signature(parent_snap, gp_m, gp_f, locus)
            if fam_sig is None:
                continue
            dominant_pheno = str(parent_traits.get(trait_key, "")).strip().lower()
            counts = {"dom": 0, "rec": 0}
            total = 0
            for child_snap in plants.values():
                if isinstance(child_snap, dict) and not child_snap.get("alive", True):
                    continue
                child_mid, child_fid = parents_from_snapshot(child_snap if isinstance(child_snap, dict) else {})
                if child_mid in (None, "", -1) or child_fid in (None, "", -1):
                    continue
                pm = get_snapshot(child_mid)
                pf = get_snapshot(child_fid)
                if not pm or not pf:
                    continue
                pm_pair = genotype_from_snapshot(pm).get(locus)
                pf_pair = genotype_from_snapshot(pf).get(locus)
                if not (
                    isinstance(pm_pair, (list, tuple))
                    and len(pm_pair) >= 2
                    and isinstance(pf_pair, (list, tuple))
                    and len(pf_pair) >= 2
                ):
                    continue
                if len(set(pm_pair[:2])) != 2 or len(set(pf_pair[:2])) != 2:
                    continue
                pm_gp_m, pm_gp_f = get_grandparents(pm)
                pf_gp_m, pf_gp_f = get_grandparents(pf)
                if law2_family_signature(pm, pm_gp_m, pm_gp_f, locus) != fam_sig:
                    continue
                if law2_family_signature(pf, pf_gp_m, pf_gp_f, locus) != fam_sig:
                    continue
                try:
                    child_traits = (
                        child_snap.get("traits", {})
                        if isinstance(child_snap, dict)
                        else getattr(child_snap, "traits", {}) or {}
                    )
                except Exception:
                    child_traits = {}
                phenotype = str(child_traits.get(trait_key, "")).strip().lower()
                if not phenotype:
                    continue
                total += 1
                if phenotype == dominant_pheno:
                    counts["dom"] += 1
                else:
                    counts["rec"] += 1

            if total < LAW2_MIN_N:
                continue
            dom_frac = counts["dom"] / float(total) if total else 0.0
            if LAW2_DOM_FRAC_MIN <= dom_frac <= LAW2_DOM_FRAC_MAX:
                law2_discovered = True
                law2_trait_name = trait_key
                law2_dominant_value = dominant_pheno
                try:
                    if counts["rec"] > 0:
                        law2_ratio_str = f"{(counts['dom'] / float(counts['rec'])):.2f}".replace(".", ",") + ":1"
                    else:
                        law2_ratio_str = f"{counts['dom']}:{counts['rec']}"
                except Exception:
                    law2_ratio_str = ""
                law2_all_valid.append((trait_key, dominant_pheno))
                law2_all_valid_ratios[trait_key] = law2_ratio_str

    if not revealed and parent_snap and gp_m and gp_f and plants and not law3_discovered:
        parent_geno = genotype_from_snapshot(parent_snap)

        def law3_family_signature(parent_snap_, gp_m_, gp_f_, loc1, loc2):
            parent_geno_ = genotype_from_snapshot(parent_snap_)
            pair1 = parent_geno_.get(loc1)
            pair2 = parent_geno_.get(loc2)
            if not (
                isinstance(pair1, (list, tuple))
                and len(pair1) >= 2
                and isinstance(pair2, (list, tuple))
                and len(pair2) >= 2
            ):
                return None
            if len(set(pair1[:2])) != 2 or len(set(pair2[:2])) != 2:
                return None
            gm_geno = genotype_from_snapshot(gp_m_)
            gf_geno = genotype_from_snapshot(gp_f_)

            def canon(pair):
                return "".join(sorted([str(pair[0]), str(pair[1])]))

            key1 = tuple(sorted([canon(gm_geno.get(loc1, ("?", "?"))), canon(gf_geno.get(loc1, ("?", "?")))]))
            key2 = tuple(sorted([canon(gm_geno.get(loc2, ("?", "?"))), canon(gf_geno.get(loc2, ("?", "?")))]))
            return tuple(sorted([(loc1, key1), (loc2, key2)]))

        candidate_traits = [key for key in law_trait_keys if key in (parent_traits or {}) and trait_to_locus.get(key)]
        for tk1, tk2 in combinations(candidate_traits, 2):
            if {"pod_color", "seed_shape"} == {tk1, tk2}:
                continue
            loc1 = trait_to_locus.get(tk1)
            loc2 = trait_to_locus.get(tk2)
            if not loc1 or not loc2:
                continue
            pair1 = parent_geno.get(loc1)
            pair2 = parent_geno.get(loc2)
            if not (
                isinstance(pair1, (list, tuple))
                and len(pair1) >= 2
                and isinstance(pair2, (list, tuple))
                and len(pair2) >= 2
            ):
                continue
            if len(set(pair1[:2])) != 2 or len(set(pair2[:2])) != 2:
                continue
            fam_sig = law3_family_signature(parent_snap, gp_m, gp_f, loc1, loc2)
            if fam_sig is None:
                continue
            combo_counts = Counter()
            dom1 = str((parent_traits or {}).get(tk1, "")).strip().lower()
            dom2 = str((parent_traits or {}).get(tk2, "")).strip().lower()
            for child_snap in plants.values():
                if isinstance(child_snap, dict) and not child_snap.get("alive", True):
                    continue
                child_mid, child_fid = parents_from_snapshot(child_snap if isinstance(child_snap, dict) else {})
                if child_mid in (None, "", -1) or child_fid in (None, "", -1):
                    continue
                pm = get_snapshot(child_mid)
                pf = get_snapshot(child_fid)
                if not pm or not pf:
                    continue
                pm_gp_m, pm_gp_f = get_grandparents(pm)
                pf_gp_m, pf_gp_f = get_grandparents(pf)
                if law3_family_signature(pm, pm_gp_m, pm_gp_f, loc1, loc2) != fam_sig:
                    continue
                if law3_family_signature(pf, pf_gp_m, pf_gp_f, loc1, loc2) != fam_sig:
                    continue
                try:
                    child_traits = (
                        child_snap.get("traits", {})
                        if isinstance(child_snap, dict)
                        else getattr(child_snap, "traits", {}) or {}
                    )
                except Exception:
                    child_traits = {}
                phenotype1 = str(child_traits.get(tk1, "")).strip().lower()
                phenotype2 = str(child_traits.get(tk2, "")).strip().lower()
                if not phenotype1 or not phenotype2:
                    continue
                combo_counts[("D" if phenotype1 == dom1 else "r", "D" if phenotype2 == dom2 else "r")] += 1

            needed_keys = [("D", "D"), ("D", "r"), ("r", "D"), ("r", "r")]
            total = sum(combo_counts.values())
            if total < LAW3_MIN_N or any(combo_counts[key] == 0 for key in needed_keys):
                continue
            chi2 = 0.0
            expected_ratios = {("D", "D"): 9, ("D", "r"): 3, ("r", "D"): 3, ("r", "r"): 1}
            for key in needed_keys:
                expected = expected_ratios[key] * (total / 16.0)
                if expected > 0:
                    diff = combo_counts[key] - expected
                    chi2 += (diff * diff) / expected
            if chi2 <= LAW3_CHI2_MAX:
                law3_discovered = True
                try:
                    scaled = [(combo_counts[key] / total) * 16.0 for key in needed_keys]
                    law3_ratio_str = " : ".join(f"{value:.1f}".replace(".", ",") for value in scaled) + " (scaled to 16)"
                except Exception:
                    law3_ratio_str = ""
                law3_trait_pair = (tk1.replace("_", " "), tk2.replace("_", " "))
                law3_all_valid_pairs.append((tk1, tk2))
                law3_all_valid_pairs_ratios[frozenset({tk1, tk2})] = law3_ratio_str

    new = []
    if not revealed and allow_credit:
        if law1_discovered and not getattr(app, "law1_ever_discovered", False) and (target_law is None or target_law == 1):
            setattr(app, "law1_ever_discovered", True)
            setattr(app, "law1_first_plant", pid)
            new.append("law1")
            if toast and hasattr(app, "_toast"):
                try:
                    app._toast(f"Law 1 (Dominance) discovered from plant #{pid}!", level="info")
                except Exception:
                    pass
        if law2_discovered and not getattr(app, "law2_ever_discovered", False) and (target_law is None or target_law == 2):
            setattr(app, "law2_ever_discovered", True)
            setattr(app, "law2_first_plant", pid)
            new.append("law2")
            if toast and hasattr(app, "_toast"):
                try:
                    app._toast(f"Law 2 (Segregation) discovered from plant #{pid}!", level="info")
                except Exception:
                    pass
        if law3_discovered and not getattr(app, "law3_ever_discovered", False) and (target_law is None or target_law == 3):
            setattr(app, "law3_ever_discovered", True)
            setattr(app, "law3_first_plant", pid)
            new.append("law3")
            if toast and hasattr(app, "_toast"):
                try:
                    app._toast(f"Law 3 (Independent Assortment) discovered from plant #{pid}!", level="info")
                except Exception:
                    pass

    try:
        if not revealed:
            if law2_discovered:
                setattr(app, "law2_ratio_ui", law2_ratio_str or "Ratio __:__")
            if law3_discovered and law3_ratio_str:
                setattr(app, "law3_ratio_ui", law3_ratio_str)
            if hasattr(app, "_update_law_status_label"):
                app._update_law_status_label()
    except Exception:
        pass

    try:
        if isinstance(snap, dict):
            if law2_discovered and law2_ratio_str:
                snap["law2_ratio"] = law2_ratio_str
                if law2_trait_name:
                    snap["law2_trait"] = law2_trait_name
            if law3_discovered and law3_ratio_str:
                snap["law3_ratio"] = law3_ratio_str
                if law3_trait_pair:
                    snap["law3_traits"] = f"{law3_trait_pair[0]} × {law3_trait_pair[1]}"
    except Exception:
        pass

    return {
        "law1": bool(law1_discovered),
        "law2": bool(law2_discovered),
        "law3": bool(law3_discovered),
        "new": new,
        "law1_trait": law1_trait_name if law1_discovered else None,
        "law1_dominant_value": law1_dominant_value if law1_discovered else None,
        "law1_all_valid": law1_all_valid if law1_discovered else [],
        "law2_trait": law2_trait_name if law2_discovered else None,
        "law2_dominant_value": law2_dominant_value if law2_discovered else None,
        "law2_all_valid": law2_all_valid if law2_discovered else [],
        "law2_all_valid_ratios": law2_all_valid_ratios if law2_discovered else {},
        "law3_traits": tuple(law3_trait_pair) if (law3_discovered and law3_trait_pair) else None,
        "law3_all_valid_pairs": law3_all_valid_pairs if law3_discovered else [],
        "law3_all_valid_pairs_ratios": law3_all_valid_pairs_ratios if law3_discovered else {},
    }

