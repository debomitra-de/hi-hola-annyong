from pronunciation.phonemizer import normalize_ipa


def align_phonemes(
    reference: list[str],
    hypothesis: list[str],
) -> list[tuple[str | None, str | None]]:
    """Align expected and detected phonemes using Levenshtein distance."""

    rows = len(reference) + 1
    cols = len(hypothesis) + 1

    dp = [[0] * cols for _ in range(rows)]

    for i in range(rows):
        dp[i][0] = i

    for j in range(cols):
        dp[0][j] = j

    for i in range(1, rows):
        for j in range(1, cols):
            cost = 0 if reference[i - 1] == hypothesis[j - 1] else 1

            dp[i][j] = min(
                dp[i - 1][j] + 1,       # Deletion
                dp[i][j - 1] + 1,       # Insertion
                dp[i - 1][j - 1] + cost,  # Match or substitution
            )

    # Backtrack to recover the alignment.
    alignment = []
    i, j = len(reference), len(hypothesis)

    while i > 0 or j > 0:
        if (
            i > 0
            and j > 0
            and dp[i][j]
            == dp[i - 1][j - 1]
            + (0 if reference[i - 1] == hypothesis[j - 1] else 1)
        ):
            alignment.append((reference[i - 1], hypothesis[j - 1]))
            i -= 1
            j -= 1

        elif i > 0 and dp[i][j] == dp[i - 1][j] + 1:
            alignment.append((reference[i - 1], None))
            i -= 1

        else:
            alignment.append((None, hypothesis[j - 1]))
            j -= 1

    alignment.reverse()
    return alignment


def calculate_per(
    reference: list[str],
    hypothesis: list[str],
) -> float:
    """Calculate Phoneme Error Rate as a percentage."""

    if not reference:
        raise ValueError("Reference phoneme sequence cannot be empty.")

    alignment = align_phonemes(reference, hypothesis)

    substitutions = sum(
        ref is not None and hyp is not None and ref != hyp
        for ref, hyp in alignment
    )

    deletions = sum(
        ref is not None and hyp is None
        for ref, hyp in alignment
    )

    insertions = sum(
        ref is None and hyp is not None
        for ref, hyp in alignment
    )

    errors = substitutions + deletions + insertions

    return (errors / len(reference)) * 100


STRESS_MARKS = {"ˈ", "ˌ"}


def extract_stress(ipa: str) -> list[tuple[int, str]]:
    """Extract primary and secondary stress positions from IPA."""

    stress_positions = []
    phoneme_index = 0

    for char in ipa:
        if char in STRESS_MARKS:
            stress_positions.append((phoneme_index, char))

        elif char.isspace() or char in {",", ".", "¿", "?", "¡", "!"}:
            continue

        elif not __import__("unicodedata").combining(char):
            phoneme_index += 1

    return stress_positions
def score_ipa(reference_ipa: str, predicted_ipa: str) -> float:
    reference = normalize_ipa(reference_ipa)
    predicted = normalize_ipa(predicted_ipa)
    return calculate_per(reference, predicted)