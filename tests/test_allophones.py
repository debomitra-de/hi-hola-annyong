from pronunciation.phonemizer import fold_allophones


def test_fold_beta():
    assert fold_allophones(["β", "a"]) == ["b", "a"]


def test_fold_eth():
    assert fold_allophones(["ð", "o"]) == ["d", "o"]


def test_fold_gamma():
    assert fold_allophones(["ɣ", "a"]) == ["ɡ", "a"]


def test_fold_unchanged():
    assert fold_allophones(["k", "a", "s", "a"]) == ["k", "a", "s", "a"]

def test_fold_mixed_sequence():
    assert fold_allophones(["β", "a", "ð", "o", "ɣ"]) == [
        "b", "a", "d", "o", "ɡ"
    ]