"""Tests for field name normalization."""

from __future__ import annotations

from quality_verification_layer.normalization import (
    normalize_field_name,
    normalize_attributes,
    _value_is_plausible,
)
from quality_verification_layer.schemas import ExtractedAttribute, Confidence


class TestFieldNameMapping:
    def test_exact_match(self):
        assert normalize_field_name("purity", "Ascorbic Acid") == "purity"
        assert normalize_field_name("assay", "Ascorbic Acid") == "purity"

    def test_spec_canonical_names(self):
        assert normalize_field_name("assay_percent", "Ascorbic Acid") == "purity"
        assert normalize_field_name("loss_on_drying_percent", "test") == "loss_on_drying"
        assert normalize_field_name("heavy_metals_ppm", "test") == "heavy_metals"
        assert normalize_field_name("lead_ppm", "test") == "lead"
        assert normalize_field_name("shelf_life_months", "test") == "shelf_life"

    def test_ingredient_stop_word_stripping(self):
        assert normalize_field_name("ascorbic_acid_purity", "Ascorbic Acid") == "purity"

    def test_substring_match(self):
        assert normalize_field_name("total_heavy_metals_content", "test") == "heavy_metals"

    def test_novel_field_preserved(self):
        assert normalize_field_name("some_novel_field", "test") == "some_novel_field"


class TestValuePlausibility:
    def test_cas_number_rejected_for_numeric(self):
        assert not _value_is_plausible("purity", "50-81-7")

    def test_molecular_formula_rejected(self):
        assert not _value_is_plausible("purity", "C6H8O6")

    def test_numeric_value_accepted(self):
        assert _value_is_plausible("purity", "99.5")
        assert _value_is_plausible("heavy_metals", "8")

    def test_ppm_in_percent_field_rejected(self):
        assert not _value_is_plausible("purity", "99.5", "ppm")

    def test_percent_in_ppm_field_rejected(self):
        assert not _value_is_plausible("heavy_metals", "10", "%")

    def test_non_numeric_field_accepts_anything(self):
        assert _value_is_plausible("grade", "USP")
        assert _value_is_plausible("certifications", "Kosher, Halal")


class TestNormalizeAttributes:
    def test_normalizes_field_names(self):
        attrs = [
            ExtractedAttribute(
                attribute_id="A1",
                field_name="assay",
                value="99.5",
                unit="%",
            ),
        ]
        result = normalize_attributes(attrs, "Ascorbic Acid")
        assert result[0].field_name == "purity"

    def test_rejects_implausible_mapping(self):
        attrs = [
            ExtractedAttribute(
                attribute_id="A1",
                field_name="ascorbic_acid_cas",
                value="50-81-7",
            ),
        ]
        result = normalize_attributes(attrs, "Ascorbic Acid")
        # Should NOT be mapped to a numeric canonical field
        assert result[0].field_name != "purity"
