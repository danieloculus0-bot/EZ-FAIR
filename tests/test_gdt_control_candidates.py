from gdt_control_candidates import partition_geometric_controls
import ez_fai_builder as base


def _characteristic(number: int, type_name: str, nominal: float = 1.0) -> base.Characteristic:
    return base.Characteristic(
        char_number=number,
        reference_location="P1-R1C1",
        nominal=nominal,
        lsl=nominal - 0.01,
        usl=nominal + 0.01,
        type=type_name,
        page_index=0,
        rect=(10.0, 10.0, 20.0, 20.0),
        raw_text=str(nominal),
        metadata={"source": "test", "nearby": "test", "extraction": "VECTOR"},
    )


def test_gdt_control_is_not_balloonable_feature() -> None:
    diameter = _characteristic(1, "Ø", 0.250)
    position = _characteristic(2, "GD&T: POSITION", 0.010)
    position.raw_text = "POSITION | Ø.010(M) | A | B | C"
    position.comments = "Feature control frame tolerance. Datums: A-B-C"
    position.metadata["extraction"] = "GD&T"

    features, controls = partition_geometric_controls([diameter, position])

    assert features == [diameter]
    assert features[0].char_number == 1
    assert len(controls) == 1
    assert controls[0].control_type == "POSITION"
    assert controls[0].tolerance == position.usl
    assert controls[0].status == "UNRESOLVED"


def test_remaining_features_are_renumbered_after_partition() -> None:
    first = _characteristic(3, "LINEAR", 1.0)
    control = _characteristic(4, "GD&T: FLATNESS", 0.005)
    second = _characteristic(8, "Ø", 0.375)

    features, controls = partition_geometric_controls([first, control, second])

    assert [item.char_number for item in features] == [1, 2]
    assert len(controls) == 1
