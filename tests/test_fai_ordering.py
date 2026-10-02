import ez_fai_builder as base
from fai_ordering import order_characteristics_for_fai


def _c(n, x, y, source):
    return base.Characteristic(
        char_number=n,
        reference_location="P1-R1C1",
        nominal=float(n),
        lsl=float(n) - 0.1,
        usl=float(n) + 0.1,
        type="LINEAR",
        page_index=0,
        rect=(x, y, x + 12, y + 8),
        raw_text=str(n),
        metadata={"source": source, "page_width": 1000.0, "page_height": 800.0},
    )


def test_order_is_clockwise_not_horizontal_scanline():
    top = _c(99, 490, 60, "TOP")
    right = _c(99, 900, 390, "RIGHT")
    bottom = _c(99, 490, 720, "BOTTOM")
    left = _c(99, 70, 390, "LEFT")

    ordered = order_characteristics_for_fai([left, bottom, right, top])

    assert [item.raw_text for item in ordered] == [top.raw_text, right.raw_text, bottom.raw_text, left.raw_text]
    assert [item.char_number for item in ordered] == [1, 2, 3, 4]


def test_local_callout_group_stays_consecutive():
    group_a = _c(1, 480, 65, "4X DIA .250 THRU")
    group_b = _c(2, 520, 72, "4X DIA .250 THRU")
    far = _c(3, 900, 390, "1.000")

    ordered = order_characteristics_for_fai([far, group_b, group_a])

    positions = [ordered.index(group_a), ordered.index(group_b)]
    assert abs(positions[0] - positions[1]) == 1
    assert group_a.metadata["balloon_group"] == group_b.metadata["balloon_group"]
