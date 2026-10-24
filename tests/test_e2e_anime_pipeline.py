"""
Root Test Discovery Forwarder: Anime Character Pipeline E2E Test Suite.
Enables running `uv run pytest tests/test_e2e_anime_pipeline.py` or `uv run pytest -k anime`
from repository root while maintaining primary test suite in teamwork_projects/anime_character_pipeline/tests.
"""

pytest_plugins = ["teamwork_projects.anime_character_pipeline.tests.conftest"]

from teamwork_projects.anime_character_pipeline.tests.test_tier1_features import TestTier1FeatureCoverage
from teamwork_projects.anime_character_pipeline.tests.test_tier2_boundaries import TestTier2BoundariesAndCornerCases
from teamwork_projects.anime_character_pipeline.tests.test_tier3_interactions import TestTier3CrossFeatureInteractions
from teamwork_projects.anime_character_pipeline.tests.test_tier4_workloads import TestTier4WorkloadScenarios

__all__ = [
    "pytest_plugins",
    "TestTier1FeatureCoverage",
    "TestTier2BoundariesAndCornerCases",
    "TestTier3CrossFeatureInteractions",
    "TestTier4WorkloadScenarios",
]
