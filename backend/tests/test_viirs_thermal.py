"""Offline checks for the VIIRS thermal-field comparison.

These tests do not open a network connection and do not read the July CSVs.
"""

from decimal import Decimal

from fire_data.viirs_thermal import (
    CONFIRMED,
    DIFFERENT,
    INSUFFICIENT,
    UNRESOLVED,
    classify_thermal_relationship,
    compare_thermal_tables,
    extract_level2_temperature_encoding,
    extract_modis_bright_t31_statement,
    extract_user_guide_statements,
    extract_viirs_attribute_statements,
    names_documented,
    pdf_text,
    quantile_type7,
    semantics_support_comparison,
)

VIIRS_PAGE = """
Bright_ti4 / Brightness (in web services)
Brightness temperature I-4
VIIRS I-4 channel brightness temperature of the fire pixel measured in Kelvin.
Frequent saturation of the mid-infrared I4 channel (3.55-3.93 µm)
Bright_ti5 / Brightness_2 (in web services)
Brightness temperature I-5
I-5 Channel brightness temperature of the fire pixel measured in Kelvin.
"""

MODIS_PAGE = """
Bright_T31
Brightness temperature 31 (Kelvin)
Channel 31 brightness temperature of the fire pixel measured in Kelvin.
"""

GUIDE_PAGE = """
FP_T4 Fire pixel I4 brightness temperature kelvin
FP_T5 Fire pixel I5 brightness temperature kelvin
T4 Fire pixel brightness temperature on channel I4 (K)
T5 Fire pixel brightness temperature on channel I5 (K)
long-wave infrared (channel I5)
nominal saturation temperature of 367 K
"""

HEADER = [
    "latitude",
    "longitude",
    "brightness",
    "scan",
    "track",
    "acq_date",
    "acq_time",
    "satellite",
    "instrument",
    "confidence",
    "version",
    "bright_t31",
    "frp",
    "daynight",
    "type",
]
API_HEADER = [
    "latitude",
    "longitude",
    "bright_ti4",
    "scan",
    "track",
    "acq_date",
    "acq_time",
    "satellite",
    "instrument",
    "confidence",
    "version",
    "bright_ti5",
    "frp",
    "daynight",
    "type",
]


def _row(header: list[str], **overrides: str) -> dict[str, str]:
    base = {name: "0" for name in header}
    base.update(
        {
            "latitude": "10.5",
            "longitude": "-20",
            "acq_date": "2024-07-07",
            "acq_time": "0031",
            "satellite": "N20",
            "instrument": "VIIRS",
            "confidence": "n",
            "version": "2",
            "scan": "0.4",
            "track": "0.4",
            "frp": "1.5",
            "daynight": "D",
            "type": "0",
        }
    )
    if "brightness" in header:
        base["brightness"] = "320.1"
        base["bright_t31"] = "290.2"
    if "bright_ti4" in header:
        base["bright_ti4"] = "320.1"
        base["bright_ti5"] = "290.2"
    base.update(overrides)
    return base


def _statements() -> dict[str, object]:
    return extract_viirs_attribute_statements(VIIRS_PAGE)


def test_attribute_page_names_i4_and_i5_without_naming_bright_t31() -> None:
    statements = _statements()
    assert statements["i4_brightness_temperature_kelvin"] is True
    assert statements["i5_brightness_temperature_kelvin"] is True
    assert statements["brightness_web_service_alias_of_bright_ti4"] is True
    assert statements["brightness_2_web_service_alias_of_bright_ti5"] is True
    assert statements["i4_wavelength_on_page"] == "3.55-3.93 µm"
    assert statements["bright_t31_present"] is False
    assert statements["bright_t31_named_beside_i5"] is False
    assert statements["scale_factor_mentioned"] is False
    assert names_documented(statements, "brightness", "bright_ti4") is True
    assert names_documented(statements, "bright_t31", "bright_ti5") is False
    assert semantics_support_comparison(statements) is True


def test_a_less_than_sign_does_not_swallow_the_following_sentence() -> None:
    text = "DBT45 < 0 then FP_T4 Fire pixel I4 brightness temperature kelvin > end"
    statements = extract_user_guide_statements(text)
    assert statements["fp_t4_i4_kelvin"] is True


def test_a_line_break_inside_the_attribute_cell_still_names_the_alias() -> None:
    text = VIIRS_PAGE.replace(
        "Bright_ti4 / Brightness (in web services)",
        "Bright_ti4 /<br>Brightness (in web services)",
    ).replace(
        "Bright_ti5 / Brightness_2 (in web services)",
        "Bright_ti5 /<br>Brightness_2 (in web services)",
    )
    statements = extract_viirs_attribute_statements(text)
    assert statements["brightness_web_service_alias_of_bright_ti4"] is True
    assert statements["brightness_2_web_service_alias_of_bright_ti5"] is True


def test_level2_table_scale_and_offset_are_read_from_cells() -> None:
    html = """
    <tr><td>FP_T4</td><td>I04 Brightness Temperature of Fire Pixel</td><td>Kelvin</td>
    <td>float32</td><td>N/A</td><td>208 to 367</td><td>N/A</td><td>N/A</td></tr>
    <tr><td>FP_T5</td><td>I05 Brightness Temperature of Fire Pixel</td><td>Kelvin</td>
    <td>float32</td><td>N/A</td><td>205 to 380</td><td>N/A</td><td>N/A</td></tr>
    """
    rows = extract_level2_temperature_encoding(html)
    assert rows["FP_T4"]["units"] == "Kelvin"
    assert rows["FP_T4"]["scale_factor"] == "N/A"
    assert rows["FP_T4"]["offset"] == "N/A"
    assert rows["FP_T5"]["valid_range"] == "205 to 380"


def test_a_non_pdf_is_not_parsed_as_a_text_layer() -> None:
    assert pdf_text(b"not a pdf") == "not a pdf"


def test_modis_bright_t31_definition_is_not_applied_to_viirs() -> None:
    statements = extract_modis_bright_t31_statement(MODIS_PAGE)
    assert statements["channel_31_kelvin"] is True
    assert statements["applied_to_viirs_archive"] is False


def test_user_guide_keeps_t4_and_t5_distinct_from_the_firms_header() -> None:
    statements = extract_user_guide_statements(GUIDE_PAGE)
    assert statements["fp_t4_i4_kelvin"] is True
    assert statements["fp_t5_i5_kelvin"] is True
    assert statements["monthly_t4_i4_kelvin"] is True
    assert statements["monthly_t5_i5_kelvin"] is True
    assert statements["i5_called_long_wave_infrared"] is True
    assert statements["i4_nominal_saturation_367k"] is True
    assert statements["guide_names_firms_archive_columns"] is False
    assert statements["scale_factor_mentioned"] is False


def test_type7_quantiles_of_a_two_point_sample() -> None:
    assert quantile_type7([], Decimal("0.5")) is None
    assert quantile_type7([Decimal("4")], Decimal("0.99")) == Decimal("4")
    assert quantile_type7([Decimal("0"), Decimal("10")], Decimal("0.5")) == Decimal("5")
    assert quantile_type7([Decimal("0"), Decimal("0"), Decimal("0")], Decimal("0.95")) == Decimal("0")


def test_equal_thermal_values_are_not_renamed() -> None:
    archive = [_row(HEADER)]
    api = [_row(API_HEADER, acq_time="31", latitude="10.50", frp="1.50")]
    before = dict(archive[0])
    result = compare_thermal_tables(HEADER, archive, API_HEADER, api)
    assert archive[0] == before
    assert "bright_ti4" not in archive[0]
    assert result["fields_renamed"] is False
    assert result["observations_aligned"] is True
    assert result["same_fire"] == "not_assessed"
    assert result["harmonization_coefficient_calculated"] is False
    for pair in result["pairs"]:
        assert pair["fields_renamed"] is False
        assert pair["exact_numeric_equality"] == 1
        assert pair["maximum_absolute_difference"] == "0"
        assert pair["mean_absolute_difference"] == "0"
        assert pair["systematic_offset"] == "none_observed"
        assert pair["scale_or_other_transformation"] == "not_calculated"
        assert pair["signed_difference_quantiles_type7"]["0.5"] == "0"
    assert result["controls"][0]["exact_numeric_equality"] == 0


def test_duplicate_keys_use_the_thermal_multiset_rather_than_stored_order() -> None:
    shared = {"latitude": "1", "longitude": "2", "acq_time": "0100"}
    archive = [
        _row(HEADER, brightness="300", bright_t31="280", **shared),
        _row(HEADER, brightness="310", bright_t31="290", **shared),
    ]
    api = [
        _row(API_HEADER, bright_ti4="310", bright_ti5="290", **shared),
        _row(API_HEADER, bright_ti4="300", bright_ti5="280", **shared),
    ]
    result = compare_thermal_tables(HEADER, archive, API_HEADER, api)
    assert result["observations_aligned"] is True
    assert result["aligned_unique_rows"] == 0
    assert result["aligned_ambiguous_rows_with_matching_thermal_multiset"] == 2
    for pair in result["pairs"]:
        assert pair["exact_numeric_equality"] == 2
        assert pair["maximum_absolute_difference"] == "0"
        assert pair["systematic_offset"] == "none_observed"


def test_missing_and_invalid_values_stay_out_of_the_numeric_sample() -> None:
    archive = [
        _row(HEADER, latitude="1", brightness="", bright_t31="280"),
        _row(HEADER, latitude="2", brightness="bad", bright_t31="281"),
        _row(HEADER, latitude="3", brightness="300.0", bright_t31="282"),
    ]
    api = [
        _row(API_HEADER, latitude="1", bright_ti4="300", bright_ti5="280"),
        _row(API_HEADER, latitude="2", bright_ti4="301", bright_ti5="281"),
        _row(API_HEADER, latitude="3", bright_ti4="300", bright_ti5="282"),
    ]
    result = compare_thermal_tables(HEADER, archive, API_HEADER, api)
    i4 = result["pairs"][0]
    assert i4["missing_archive"] == 1
    assert i4["invalid_archive"] == 1
    assert i4["numeric_pairs"] == 1
    assert i4["exact_numeric_equality"] == 1
    assert i4["maximum_absolute_difference"] == "0"


def test_a_constant_difference_is_reported_and_no_coefficient_is_fit() -> None:
    archive = [_row(HEADER, latitude=str(index), brightness="300", bright_t31="280") for index in range(4)]
    api = [_row(API_HEADER, latitude=str(index), bright_ti4="302", bright_ti5="280") for index in range(4)]
    result = compare_thermal_tables(HEADER, archive, API_HEADER, api)
    i4 = result["pairs"][0]
    assert i4["systematic_offset"] == "constant_difference_observed"
    assert i4["mean_signed_difference_api_minus_archive"] == "2"
    assert i4["maximum_absolute_difference"] == "2"
    assert i4["absolute_difference_quantiles_type7"]["0"] == "2"
    assert i4["absolute_difference_quantiles_type7"]["1"] == "2"
    assert i4["harmonization_coefficient_calculated"] is False
    assert result["pairs"][1]["systematic_offset"] == "none_observed"


def test_matching_values_stay_unresolved_when_bright_t31_is_not_named() -> None:
    comparison = compare_thermal_tables(HEADER, [_row(HEADER)], API_HEADER, [_row(API_HEADER)])
    for pair in comparison["pairs"]:
        pair["name_documented"] = names_documented(_statements(), pair["archive_field"], pair["api_field"])
    assert classify_thermal_relationship(comparison, _statements(), request_ok=True) == UNRESOLVED


def test_both_documented_aliases_and_exact_values_are_confirmed() -> None:
    statements = _statements()
    statements["bright_t31_named_beside_i5"] = True
    comparison = compare_thermal_tables(HEADER, [_row(HEADER)], API_HEADER, [_row(API_HEADER)])
    assert classify_thermal_relationship(comparison, statements, request_ok=True) == CONFIRMED


def test_a_failed_request_is_insufficient_evidence() -> None:
    comparison = compare_thermal_tables(HEADER, [_row(HEADER)], API_HEADER, [_row(API_HEADER)])
    assert classify_thermal_relationship(comparison, _statements(), request_ok=False) == INSUFFICIENT
    assert classify_thermal_relationship(None, _statements(), request_ok=True) == INSUFFICIENT


def test_an_explicit_product_split_is_required_for_a_different_stream() -> None:
    archive = [_row(HEADER, brightness="300")]
    api = [_row(API_HEADER, bright_ti4="310")]
    comparison = compare_thermal_tables(HEADER, archive, API_HEADER, api)
    assert classify_thermal_relationship(comparison, _statements(), request_ok=True) == UNRESOLVED
    statements = _statements()
    statements["archive_and_area_are_different_products"] = True
    assert classify_thermal_relationship(comparison, statements, request_ok=True) == DIFFERENT


def test_unmatched_rows_are_not_called_a_different_product() -> None:
    archive = [_row(HEADER, latitude="1"), _row(HEADER, latitude="2")]
    api = [_row(API_HEADER, latitude="1")]
    comparison = compare_thermal_tables(HEADER, archive, API_HEADER, api)
    assert comparison["unaligned_archive_rows"] == 1
    assert comparison["observations_aligned"] is False
    assert classify_thermal_relationship(comparison, _statements(), request_ok=True) == INSUFFICIENT
