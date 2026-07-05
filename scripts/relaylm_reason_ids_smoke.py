from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.reason_ids import normalize_reason_ids


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def main() -> int:
    ordered = normalize_reason_ids(["b_reason", "a_reason", "c_reason"])
    require(ordered == ["b_reason", "a_reason", "c_reason"], ordered)
    print("ok preserves first-seen order")

    deduped = normalize_reason_ids(["a_reason", "b_reason", "a_reason"])
    require(deduped == ["a_reason", "b_reason"], deduped)
    print("ok deduplicates reason ids")

    dropped = normalize_reason_ids(["good_reason", "BadReason", "", 123, "next_reason"])
    require(dropped == ["good_reason", "next_reason"], dropped)
    print("ok drops invalid reason ids")

    marked = normalize_reason_ids(
        ["good_reason", "BadReason", "", 123, "next_reason"],
        invalid="marker",
        output="tuple",
    )
    require(marked == ("good_reason", "invalid_reason_id", "next_reason"), marked)
    print("ok marks invalid reason ids once")

    as_list = normalize_reason_ids(("tuple_reason",), output="list")
    require(type(as_list) is list and as_list == ["tuple_reason"], as_list)
    print("ok list output")

    as_tuple = normalize_reason_ids(["list_reason"], output="tuple")
    require(type(as_tuple) is tuple and as_tuple == ("list_reason",), as_tuple)
    print("ok tuple output")

    non_iter_drop = normalize_reason_ids(12345)
    require(non_iter_drop == [], non_iter_drop)
    non_iter_marker = normalize_reason_ids(12345, invalid="marker", output="tuple")
    require(non_iter_marker == ("invalid_reason_id",), non_iter_marker)
    print("ok non-list input handling")

    empty_values = normalize_reason_ids([], output="tuple")
    require(empty_values == (), empty_values)
    print("ok empty values")

    scalar_string = normalize_reason_ids("scalar_reason")
    require(scalar_string == ["scalar_reason"], scalar_string)
    print("ok scalar string is treated as one reason id")

    print("all reason_id normalization smoke checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
