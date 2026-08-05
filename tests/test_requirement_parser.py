from decimal import Decimal

from requirement_parser import classify_feature, parse_requirement


def test_feature_classification():
    assert classify_feature("4X Ø.250 THRU") == "DIAMETER"
    assert classify_feature("R .125 TYP") == "RADIUS"
    assert classify_feature("SR .500") == "SPHERICAL RADIUS"
    assert classify_feature("30°") == "ANGLE"
    assert classify_feature(".020 X 45° CHAMFER") == "CHAMFER"
    assert classify_feature("1/4-20 UNC-2B") == "THREAD"
    assert classify_feature("⌴ Ø.375 ↧ .250") == "COUNTERBORE"


def test_symmetric_and_asymmetric_limits():
    symmetric = parse_requirement("Ø.250 ±.002")
    assert symmetric.feature_type == "DIAMETER"
    assert symmetric.nominal == Decimal(".250")
    assert symmetric.lsl == Decimal(".248")
    assert symmetric.usl == Decimal(".252")

    asymmetric = parse_requirement("1.250 +.010 / -.005")
    assert asymmetric.lsl == Decimal("1.245")
    assert asymmetric.usl == Decimal("1.260")


def test_limits_and_unilateral_tolerances():
    limits = parse_requirement("1.245 TO 1.255")
    assert limits.nominal is None
    assert limits.lsl == Decimal("1.245")
    assert limits.usl == Decimal("1.255")

    plus = parse_requirement("1.250 +.010")
    assert plus.lsl == Decimal("1.250")
    assert plus.usl == Decimal("1.260")

    minus = parse_requirement("1.250 -.005")
    assert minus.lsl == Decimal("1.245")
    assert minus.usl == Decimal("1.250")


def test_quantity_reference_and_basic_flags():
    pattern = parse_requirement("4X Ø.250 ±.002")
    assert pattern.quantity == 4
    assert pattern.feature_type == "DIAMETER"

    reference = parse_requirement("(.750) REF")
    assert reference.reference_only is True

    basic = parse_requirement("[1.250]")
    assert basic.basic is True
    assert basic.lsl is None
    assert basic.usl is None
