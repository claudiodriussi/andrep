"""
Composition and the FilesystemLoader perimeter (internal notes §4.7).

Composition targets are template content: the loader must keep them inside
its own directories. A missing target is skipped silently (optional
overrides); a target outside the perimeter is an explicit error.
"""
import pytest

from andrep import AndRepRenderer, FilesystemLoader
from conftest import emitted_values, make_template, write_templates


def composed(main: dict, templates: dict, tmp_path, custom: dict = None) -> AndRepRenderer:
    base = write_templates(tmp_path / "base", {"main": main, **templates})
    if custom:
        write_templates(base / "custom", custom)
    return AndRepRenderer("main", loader=FilesystemLoader(base_dir=base))


def band_names(r: AndRepRenderer) -> list:
    return [row["name"] for row in r.template["rows"]]


# ---------------------------------------------------------------------------
# Normal composition
# ---------------------------------------------------------------------------

def test_ifnot_imports_missing_bands(tmp_path):
    main = make_template({"band": ["x"]}, composition=[{"rule": "IfNot", "target": "std"}])
    std = make_template({"band": ["std"], "page_footer": ["footer"]})
    r = composed(main, {"std": std}, tmp_path)
    assert band_names(r) == ["band", "page_footer"]


def test_custom_dir_overrides_base(tmp_path):
    main = make_template({"band": ["x"]}, composition=[{"rule": "Replace", "target": "hdr"}])
    r = composed(
        main,
        {"hdr": make_template({"band": ['["standard"]']})},
        tmp_path,
        custom={"hdr": make_template({"band": ['["custom"]']})},
    )
    r.emit("band")
    assert emitted_values(r) == ["custom"]


def test_subdirectory_inside_base_is_allowed(tmp_path):
    main = make_template({"band": ["x"]}, composition=[{"rule": "IfNot", "target": "shared/std"}])
    base = write_templates(tmp_path / "base", {"main": main})
    write_templates(base / "shared", {"std": make_template({"page_footer": ["f"]})})
    r = AndRepRenderer("main", loader=FilesystemLoader(base_dir=base))
    assert band_names(r) == ["band", "page_footer"]


def test_symlink_inside_base_is_allowed(tmp_path):
    main = make_template({"band": ["x"]}, composition=[{"rule": "IfNot", "target": "alias"}])
    base = write_templates(tmp_path / "base", {"main": main, "std": make_template({"page_footer": ["f"]})})
    (base / "alias.json").symlink_to(base / "std.json")
    r = AndRepRenderer("main", loader=FilesystemLoader(base_dir=base))
    assert band_names(r) == ["band", "page_footer"]


def test_missing_target_is_skipped_silently(tmp_path):
    """Documented behavior: a composition rule can be an optional override."""
    main = make_template({"band": ["x"]}, composition=[{"rule": "Replace", "target": "not_there"}])
    r = composed(main, {}, tmp_path)
    assert band_names(r) == ["band"]


# ---------------------------------------------------------------------------
# Perimeter — targets outside the loader directories are explicit errors
# ---------------------------------------------------------------------------

@pytest.fixture
def outside(tmp_path):
    """A valid template that exists outside the loader directories."""
    write_templates(tmp_path / "outside", {"secret": make_template({"band": ["outside"]})})
    return tmp_path / "outside" / "secret"


def test_target_with_dotdot_is_rejected(tmp_path, outside):
    main = make_template({"band": ["x"]}, composition=[{"rule": "Replace", "target": "../outside/secret"}])
    with pytest.raises(ValueError, match="outside"):
        composed(main, {}, tmp_path)


def test_absolute_target_is_rejected(tmp_path, outside):
    main = make_template({"band": ["x"]}, composition=[{"rule": "Replace", "target": str(outside)}])
    with pytest.raises(ValueError, match="outside"):
        composed(main, {}, tmp_path)


def test_symlink_leading_outside_is_rejected(tmp_path, outside):
    main = make_template({"band": ["x"]}, composition=[{"rule": "Replace", "target": "link"}])
    base = write_templates(tmp_path / "base", {"main": main})
    (base / "link.json").symlink_to(outside.with_suffix(".json"))
    with pytest.raises(ValueError, match="outside"):
        AndRepRenderer("main", loader=FilesystemLoader(base_dir=base))


def test_custom_dir_is_a_perimeter_too(tmp_path, outside):
    """custom_dir defaults to base_dir/custom: '..' from there must not reach elsewhere."""
    main = make_template({"band": ["x"]}, composition=[{"rule": "Replace", "target": "../../outside/secret"}])
    with pytest.raises(ValueError, match="outside"):
        composed(main, {}, tmp_path)


def test_template_name_outside_is_rejected(tmp_path, outside):
    """The name passed by the programmer is trusted, but the same check covers it."""
    base = write_templates(tmp_path / "base", {})
    with pytest.raises(ValueError, match="outside"):
        FilesystemLoader(base_dir=base).load("../outside/secret")
