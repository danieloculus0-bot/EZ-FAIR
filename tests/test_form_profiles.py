from pathlib import Path

import pytest

from form_profiles import (
    FormConfiguration,
    FormConfigurationStore,
    build_default_configuration,
    get_profile,
    resolve_columns,
)


def test_default_profile_contains_r3_minimum_fields():
    profile = get_profile("ez_fair_r3")
    field_keys = {field.key for section in profile.sections for field in section.fields}
    column_keys = {column.key for column in profile.columns}

    assert {"part_no", "part_name", "drawing_no", "revision", "date", "inspector", "item_no", "po_no", "order_no", "reason_for_fai"} <= field_keys
    assert {"char_number", "reference_location", "lsl", "nominal", "usl", "feature_type", "supplier_actual", "supplier_result", "ez_actual", "in_spec", "qualified_tooling", "comments"} <= column_keys


def test_unknown_components_are_rejected():
    profile = get_profile("ez_fair_r3")
    config = FormConfiguration(
        enabled_sections=["header", "invented_section"],
        enabled_columns=["char_number", "made_up_column"],
    )
    with pytest.raises(ValueError, match="pre-approved"):
        config.validated(profile)


def test_required_columns_cannot_be_disabled():
    profile = get_profile("ez_fair_r3")
    config = FormConfiguration(
        enabled_sections=["header"],
        enabled_columns=["comments"],
        column_order=["comments"],
    ).validated(profile)
    assert {"char_number", "reference_location", "lsl", "nominal", "usl", "feature_type"} <= set(config.enabled_columns)


def test_optional_tooling_can_be_hidden_without_deleting_definition():
    profile = get_profile("ez_fair_r3")
    config = build_default_configuration()
    config.enabled_columns.remove("qualified_tooling")
    config.column_order.remove("qualified_tooling")
    resolved = resolve_columns(config)
    assert "qualified_tooling" not in {column.key for column in resolved}
    assert "qualified_tooling" in profile.approved_column_keys


def test_configuration_round_trip(tmp_path: Path):
    path = tmp_path / "form.json"
    store = FormConfigurationStore(path)
    config = build_default_configuration()
    config.accent_color = "#22AAFF"
    config.button_color = "#0055CC"
    store.save(config)
    loaded = store.load()
    assert loaded.accent_color == "#22AAFF"
    assert loaded.button_color == "#0055CC"
