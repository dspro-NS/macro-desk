from macro_desk.domain.importance import IMPORTANCE_HIGH, IMPORTANCE_LOW, IMPORTANCE_MEDIUM, rank_importance


def _rank(title: str, body: str = "") -> tuple[str, str]:
    result = rank_importance(title, body)
    return result.importance, result.reason


def test_mpc_minutes_are_high() -> None:
    importance, reason = _rank(
        "Minutes of the Monetary Policy Committee Meeting, August 2026",
        "The MPC kept the policy repo rate unchanged.",
    )
    assert importance == IMPORTANCE_HIGH
    assert "monetary policy committee" in reason.lower()


def test_master_direction_is_high() -> None:
    importance, reason = _rank("Master Direction – Know Your Customer (KYC) Direction")
    assert importance == IMPORTANCE_HIGH
    assert "master direction" in reason.lower()


def test_governor_speech_is_high() -> None:
    importance, reason = _rank(
        "Keynote Address delivered by the Governor, Reserve Bank of India",
        "The Governor discussed the policy stance.",
    )
    assert importance == IMPORTANCE_HIGH
    assert "governor" in reason.lower()


def test_deputy_governor_speech_is_medium() -> None:
    importance, reason = _rank(
        "Speech by the Deputy Governor at the NBFC Summit",
        "Remarks on credit growth and NBFCs.",
    )
    assert importance == IMPORTANCE_MEDIUM
    assert "deputy governor" in reason.lower()


def test_upi_circular_is_medium() -> None:
    importance, reason = _rank(
        "Enhancement of UPI transaction limits",
        "The Reserve Bank has issued a circular on the Unified Payments Interface.",
    )
    assert importance == IMPORTANCE_MEDIUM


def test_crr_review_is_high_not_auction_result() -> None:
    importance, _reason = _rank("Review of Cash Reserve Ratio")
    assert importance == IMPORTANCE_HIGH


def test_repo_auction_result_is_low() -> None:
    importance, reason = _rank("Result of Variable Rate Repo Auction")
    assert importance == IMPORTANCE_LOW
    assert "operational" in reason.lower() or "administrative" in reason.lower()


def test_appointment_is_low_even_if_governor_is_mentioned() -> None:
    importance, reason = _rank(
        "Appointment of Governor of the Reserve Bank of India",
        "The Central Government has appointed the Governor.",
    )
    assert importance == IMPORTANCE_LOW
    assert "appointment of" in reason.lower()


def test_unmatched_outreach_is_low() -> None:
    importance, _reason = _rank("RBI organises outreach programme at a college")
    assert importance == IMPORTANCE_LOW
