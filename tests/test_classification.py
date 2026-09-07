from macro_desk.domain.classification import classify_document
from macro_desk.domain.taxonomy import Category


def _classify(title: str, body: str) -> tuple[str, str]:
    result = classify_document(title, body)
    return result.category, result.reason


def test_mpc_minutes_are_monetary_policy_even_when_inflation_is_mentioned() -> None:
    category, reason = _classify(
        "Minutes of the Monetary Policy Committee Meeting, August 2026",
        "The MPC kept the policy repo rate unchanged. Members discussed CPI inflation "
        "and GDP growth, and assessed surplus liquidity in the banking system.",
    )
    assert category == Category.MONETARY_POLICY.value
    assert "monetary policy committee" in reason.lower() or "mpc" in reason.lower()
    assert "repo rate" in reason.lower()


def test_variable_rate_repo_auction_is_liquidity() -> None:
    category, reason = _classify(
        "Result of Variable Rate Repo Auction",
        "The Reserve Bank conducted a Variable Rate Repo auction under the LAF. "
        "The operation absorbed surplus liquidity.",
    )
    assert category == Category.LIQUIDITY.value
    assert "variable rate repo" in reason.lower() or "laf" in reason.lower()


def test_crr_review_is_liquidity_not_regulation() -> None:
    category, _reason = _classify(
        "Review of Cash Reserve Ratio",
        "It has been decided to change the cash reserve ratio (CRR) of scheduled banks.",
    )
    assert category == Category.LIQUIDITY.value


def test_cooperative_bank_licence_is_banking() -> None:
    category, reason = _classify(
        "RBI grants licence to an Urban Co-operative Bank",
        "The Reserve Bank of India has granted a banking licence to an urban co-operative bank.",
    )
    assert category == Category.BANKING.value
    assert "licence" in reason.lower() or "co-operative" in reason.lower()


def test_kyc_master_direction_is_regulation() -> None:
    category, reason = _classify(
        "Master Direction – Know Your Customer (KYC) Direction",
        "The Reserve Bank issues the Master Direction on Know Your Customer for regulated entities.",
    )
    assert category == Category.REGULATION.value
    assert "know your customer" in reason.lower() or "kyc" in reason.lower() or "master direction" in reason.lower()


def test_cpi_release_is_inflation() -> None:
    category, reason = _classify(
        "Data on Consumer Price Index released",
        "CPI inflation eased. The wholesale price index was also noted in passing.",
    )
    assert category == Category.INFLATION.value
    assert "cpi" in reason.lower() or "consumer price index" in reason.lower()


def test_gdp_and_iip_are_growth() -> None:
    category, reason = _classify(
        "Provisional estimates of Gross Domestic Product",
        "GDP growth and the Index of Industrial Production (IIP) pointed to a pickup in activity.",
    )
    assert category == Category.GROWTH.value
    assert "gdp" in reason.lower() or "gross domestic product" in reason.lower()


def test_forex_reserves_are_fx_external() -> None:
    category, reason = _classify(
        "RBI's foreign exchange reserves",
        "India's foreign exchange reserves rose. FPI inflows and the USD/INR exchange rate were steady.",
    )
    assert category == Category.FX_EXTERNAL.value
    assert "foreign exchange reserves" in reason.lower() or "forex" in reason.lower()


def test_financial_stability_report_category() -> None:
    category, reason = _classify(
        "Financial Stability Report, June 2026",
        "The report assesses systemic risk and bank stress tests.",
    )
    assert category == Category.FINANCIAL_STABILITY.value
    assert "financial stability" in reason.lower()


def test_upi_limits_are_payments_not_regulation() -> None:
    category, reason = _classify(
        "Enhancement of UPI transaction limits",
        "The Reserve Bank has issued a circular enhancing limits on the Unified Payments Interface (UPI).",
    )
    assert category == Category.PAYMENTS.value
    assert "upi" in reason.lower() or "unified payments interface" in reason.lower()


def test_deputy_governor_appointment_is_other() -> None:
    category, reason = _classify(
        "Appointment of Deputy Governor of the Reserve Bank of India",
        "The Central Government has appointed a Deputy Governor. The appointee has a background in banking regulation.",
    )
    assert category == Category.OTHER.value
    assert "administrative" in reason.lower()


def test_unrelated_text_is_other() -> None:
    category, reason = _classify(
        "RBI organises outreach programme",
        "An outreach programme was organised at a college.",
    )
    assert category == Category.OTHER.value
    assert "no taxonomy keywords" in reason.lower()
