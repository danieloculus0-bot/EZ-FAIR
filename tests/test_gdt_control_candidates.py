from gdt_control_candidates import partition_geometric_controls
import ez_fai_builder as base


def _characteristic(number: int, type_name: str, nominal: float = 1.0, rect=(10.0, 10.0, 20.0, 20.0)) -> base.Characteristic:
    return base.Characteristic(
        char_number=number,
        reference_location="P1-R1C1",
        nominal=nominal,
        lsl=nominal - 0.01,
        usl=nominal + 0.01,
        type=type_name,
        page_index=0,
        rect=rect,
        raw_text=str(nominal),
        metadata={"source": "test", "nearby": "test", "extraction": "VECTOR", "page_width": 1000.0, "page_height": 800.0},
    )


def test_nearby_unambiguous_gdt_becomes_balloonable_characteristic() -> None:
    diameter = _characteristic(1, "Ø", 0.250, (100, 100, 120, 120))
    position = _characteristic(2, "GD&T: POSITION", 0.010, (135, 100, 155, 120))
    position.raw_text = "POSITION | Ø.010(M) | A | B | C"
    position.comments = "Feature control frame tolerance. Datums: A-B-C"
    position.metadata["extraction"] = "GD&T"

    features, controls = partition_geometric_controls([diameter, position])

    assert features == [diameter, position]
    assert [item.char_number for item in features] == [1, 2]
    assert controls == []
    assert position.metadata["gdt_association"] == "AUTO_NEAREST_UNAMBIGUOUS"
    assert position.metadata["linked_feature_raw_text"] == diameter.raw_text


def test_ambiguous_gdt_is_held_for_review() -> None:
    first = _characteristic(1, "LINEAR", 1.0, (100, 100, 120, 120))
    second = _characteristic(2, "Ø", 0.375, (160, 100, 180, 120))
    control = _characteristic(3, "GD&T: FLATNESS", 0.005, (130, 100, 150, 120))
    control.metadata["extraction"] = "GD&T"

    features, controls = partition_geometric_controls([first, second, control])

    assert features == [first, second]
    assert [item.char_number for item in features] == [1, 2]
    assert len(controls) == 1
    assert controls[0].control_type == "FLATNESS"
    assert controls[0].status == "UNRESOLVED"
