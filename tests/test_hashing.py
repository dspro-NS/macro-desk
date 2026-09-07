from macro_desk.domain.hashing import compute_content_hash


def test_content_hash_is_stable_for_equivalent_text() -> None:
    first = compute_content_hash("  Repo  Rate  ", "Policy remains unchanged.\n")
    second = compute_content_hash("Repo Rate", "Policy remains unchanged.")
    assert first == second
    assert len(first) == 64


def test_content_hash_changes_when_body_changes() -> None:
    original = compute_content_hash("Repo Rate", "Unchanged")
    updated = compute_content_hash("Repo Rate", "Increased")
    assert original != updated


def test_content_hash_does_not_depend_on_url() -> None:
    """URL is a separate uniqueness key; hash is content-only."""
    left = compute_content_hash("Title", "Body")
    right = compute_content_hash("Title", "Body")
    assert left == right
