# Utilities functions for testing


def contain_same_values(cont1, cont2):
    """unittest.TestCase.assertEqual doest not test properly the deep (unsorted) equality of nested dicts:

    a = {'items': [{'x': 1}, {'y': 2}]}
    b = {'items': [{'y': 2}, {'x': 1}]}
    assertEqual(a, b) =>  will raise an AssertionError, since the two lists are not in the same order.

    If we want to test that two nested dicts (or lists) contain the same elements,
    no matter the order of those elements, we can first convert lists and dicts to frozenset,
    before comparing their hash value.
    """

    def freeze_container(obj):
        if isinstance(obj, list):
            return frozenset([freeze_container(el) for el in obj])
        elif isinstance(obj, dict):
            return frozenset((k, freeze_container(v)) for k, v in obj.items())
        else:
            return obj

    return hash(freeze_container(cont1)) == hash(freeze_container(cont2))


if __name__ == "__main__":

    a = {"x": [{"y": 1, "z": 2}, {"z": 3, "t": 5}], "d": {"w": [1, 2, 3]}}

    b = {
        "x": [
            {"z": 3, "t": 5},
            {"z": 2, "y": 1},
        ],
        "d": {"w": [1, 3, 2]},
    }

    assert contain_same_values(a, b)

    c = [
        {"assets": ["CATHERINE", "ERIK", "JOHN"]},
        {
            "assets": [
                {
                    "type": "Asset",
                    "name": "CATHERINE",
                    "asset_type": "character",
                    "children": [],
                },
            ]
        },
    ]

    d = [
        {"assets": ["ERIK", "JOHN", "CATHERINE"]},
        {
            "assets": [
                {
                    "asset_type": "character",
                    "type": "Asset",
                    "children": [],
                    "name": "CATHERINE",
                },
            ]
        },
    ]

    assert contain_same_values(d, c)

    e = [
        {"assets": ["ERIK", "JOHN"]},
        {
            "assets": [
                {
                    "asset_type": "character",
                    "type": "Asset",
                    "children": [],
                    "name": "CATHERINE",
                },
            ]
        },
    ]

    assert not contain_same_values(c, e)

    f = [
        {"assets": ["ERIK", "JOHN", "CATHERINE"]},
        {
            "assets": [
                {
                    "asset_type": "character",
                    "type": "Asset",
                    "children": [],
                    "name": "JOHN",
                },
            ]
        },
    ]

    assert not contain_same_values(c, f)
