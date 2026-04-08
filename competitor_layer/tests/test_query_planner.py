"""Tests for query planner."""

from __future__ import annotations

from competitor_layer.query_planner import plan_queries
from competitor_layer.schemas import IngredientRef, SearchContext


def _ascorbic_acid() -> IngredientRef:
    return IngredientRef(
        ingredient_id="ING-ASCORBIC-ACID",
        canonical_name="Ascorbic Acid",
        aliases=["Vitamin C", "L-Ascorbic Acid"],
        category="food ingredient",
    )


class TestAliasExpansion:
    def test_queries_contain_alias_terms(self):
        queries = plan_queries(_ascorbic_acid())
        joined = " | ".join(queries)
        assert "Vitamin C" in joined
        assert "L-Ascorbic Acid" in joined

    def test_canonical_name_always_present(self):
        queries = plan_queries(_ascorbic_acid())
        assert any("Ascorbic Acid" in q for q in queries)


class TestRegionAware:
    def test_region_present_in_queries(self):
        ctx = SearchContext(region="EU")
        queries = plan_queries(_ascorbic_acid(), context=ctx)
        assert any("EU" in q for q in queries)

    def test_no_region_no_region_queries(self):
        queries = plan_queries(_ascorbic_acid())
        assert not any("EU" in q or "US" in q for q in queries)


class TestGradeHint:
    def test_custom_grade_hint(self):
        ctx = SearchContext(grade_hint="pharmaceutical")
        queries = plan_queries(_ascorbic_acid(), context=ctx)
        assert any("pharmaceutical" in q for q in queries)

    def test_default_food_grade(self):
        queries = plan_queries(_ascorbic_acid())
        assert any("food grade" in q for q in queries)


class TestQueryBudget:
    def test_max_queries_respected(self):
        queries = plan_queries(_ascorbic_acid(), max_queries=5)
        assert len(queries) <= 5

    def test_no_duplicates(self):
        queries = plan_queries(_ascorbic_acid())
        lowered = [q.lower() for q in queries]
        assert len(lowered) == len(set(lowered))


class TestRegression:
    def test_ascorbic_acid_full_context(self):
        ctx = SearchContext(region="EU", product_category="beverage", grade_hint="food-grade")
        queries = plan_queries(_ascorbic_acid(), context=ctx)
        # Must contain core families
        assert any("supplier" in q.lower() for q in queries)
        assert any("manufacturer" in q.lower() for q in queries)
        assert any("technical data sheet" in q.lower() for q in queries)
        # Must contain region
        assert any("EU" in q for q in queries)
        # Must contain product category
        assert any("beverage" in q.lower() for q in queries)
        # Reasonable count
        assert 8 <= len(queries) <= 15
