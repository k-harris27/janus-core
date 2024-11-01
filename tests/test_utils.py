"""Test utility functions."""

from pathlib import Path

from ase import Atoms
from ase.io import read
import pytest

from janus_core.cli.utils import dict_paths_to_strs, dict_remove_hyphens
from janus_core.helpers.mlip_calculators import choose_calculator
from janus_core.helpers.struct_io import output_structs
from janus_core.helpers.utils import none_to_dict

DATA_PATH = Path(__file__).parent / "data/NaCl.cif"
MODEL_PATH = Path(__file__).parent / "models/mace_mp_small.model"


def test_dict_paths_to_strs():
    """Test Paths are converted to strings."""
    dictionary = {
        "key1": Path("/example/path"),
        "key2": {
            "key3": Path("another/example"),
            "key4": "example",
        },
    }

    # Check Paths are present
    assert isinstance(dictionary["key1"], Path)
    assert isinstance(dictionary["key2"]["key3"], Path)
    assert not isinstance(dictionary["key1"], str)

    dict_paths_to_strs(dictionary)

    # Check Paths are now strings
    assert isinstance(dictionary["key1"], str)
    assert isinstance(dictionary["key2"]["key3"], str)


def test_dict_remove_hyphens():
    """Test hyphens are replaced with underscores."""
    dictionary = {
        "key-1": "value_1",
        "key-2": {
            "key-3": "value-3",
            "key-4": 4,
            "key_5": 5.0,
            "key6": {"key-7": "value7"},
        },
    }
    dictionary = dict_remove_hyphens(dictionary)

    # Check hyphens are now strings
    assert dictionary["key_1"] == "value_1"
    assert dictionary["key_2"]["key_3"] == "value-3"
    assert dictionary["key_2"]["key_4"] == 4
    assert dictionary["key_2"]["key_5"] == 5.0
    assert dictionary["key_2"]["key6"]["key_7"] == "value7"


@pytest.mark.parametrize("arch", ["mace_mp", "m3gnet", "chgnet"])
@pytest.mark.parametrize("write_results", [True, False])
@pytest.mark.parametrize("properties", [None, ["energy"], ["energy", "forces"]])
@pytest.mark.parametrize("invalidate_calc", [True, False])
@pytest.mark.parametrize(
    "write_kwargs", [{}, {"write_results": False}, {"set_info": False}]
)
def test_output_structs(
    arch, write_results, properties, invalidate_calc, write_kwargs, tmp_path
):
    """Test output_structs copies/moves results to Atoms.info and writes files."""
    struct = read(DATA_PATH)
    struct.calc = choose_calculator(arch=arch)

    if properties:
        results_keys = set(properties)
    else:
        results_keys = {"energy", "forces", "stress"}

    label_keys = {f"{arch}_{key}" for key in results_keys}

    write_kwargs = {}
    output_file = tmp_path / "output.extxyz"
    if write_results:
        write_kwargs["filename"] = output_file

    # Use calculator
    struct.get_potential_energy()
    struct.get_stress()

    # Check all expected keys are in results
    assert results_keys <= struct.calc.results.keys()

    # Check results and MLIP-labelled keys are not in info or arrays
    assert not results_keys & struct.info.keys()
    assert not results_keys & struct.arrays.keys()
    assert not label_keys & struct.info.keys()
    assert not label_keys & struct.arrays.keys()

    output_structs(
        struct,
        write_results=write_results,
        properties=properties,
        invalidate_calc=invalidate_calc,
        write_kwargs=write_kwargs,
    )

    # Check results keys depend on invalidate_calc
    if invalidate_calc:
        assert not results_keys & struct.calc.results.keys()
    else:
        assert results_keys <= struct.calc.results.keys()

    # Check labelled keys added to info and arrays
    if "set_info" not in write_kwargs or write_kwargs["set_info"]:
        assert label_keys <= struct.info.keys() | struct.arrays.keys()
        assert struct.info["arch"] == arch

    # Check file written correctly if write_results
    if write_results:
        assert output_file.exists()
        atoms = read(output_file)
        assert isinstance(atoms, Atoms)

        # Check labelled info and arrays was written and can be read back in
        if "set_info" not in write_kwargs or write_kwargs["set_info"]:
            assert label_keys <= atoms.info.keys() | atoms.arrays.keys()
            assert atoms.info["arch"] == arch

        # Check calculator results depend on invalidate_calc
        if invalidate_calc:
            assert atoms.calc is None
        elif "write_results" not in write_kwargs or write_kwargs["write_results"]:
            assert results_keys <= atoms.calc.results.keys()

    else:
        assert not output_file.exists()


@pytest.mark.parametrize(
    "dicts_in",
    [
        [None, {"a": 1}, {}, {"b": 2, "a": 11}, None],
        (None, {"a": 1}, {}, {"b": 2, "a": 11}, None),
    ],
)
def test_none_to_dict(dicts_in):
    """Test none_to_dict removes Nones from sequence, and preserves dictionaries."""
    dicts = list(none_to_dict(dicts_in))
    for dictionary in dicts:
        assert dictionary is not None

    assert dicts[0] == {}
    assert dicts[1] == dicts_in[1]
    assert dicts[2] == dicts_in[2]
    assert dicts[3] == dicts_in[3]
    assert dicts[4] == {}
