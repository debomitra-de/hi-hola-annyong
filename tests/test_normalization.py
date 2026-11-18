from pronunciation.phonemizer import normalize_ipa


def test_normalize_ipa_examples():
    assert normalize_ipa("ˈola") == ["o", "l", "a"]
    assert normalize_ipa("me ʎamo anna") == ["m", "e", "ʎ", "a", "m", "o", "a", "n", "n", "a"]
    assert normalize_ipa("komeɾ βaɾko") == ["k", "o", "m", "e", "ɾ", "b", "a", "ɾ", "k", "o"]
    assert normalize_ipa("t͡ʃ") == ["t͡ʃ"]
    assert normalize_ipa("ã") == ["ã"]
