from pronunciation.alignment import extract_stress


def test_primary_stress():
    assert extract_stress("ˈola") == [(0, "ˈ")]


def test_secondary_stress():
    assert extract_stress("ˌapɾendiendo") == [(0, "ˌ")]


def test_multiple_stresses():
    assert extract_stress("ˈola ˌamigo") == [
        (0, "ˈ"),
        (3, "ˌ"),
    ]


def test_no_stress():
    assert extract_stress("hola") == []
