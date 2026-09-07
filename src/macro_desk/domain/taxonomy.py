from __future__ import annotations

from enum import Enum


class Category(str, Enum):
    """Controlled taxonomy from the project brief."""

    MONETARY_POLICY = "Monetary Policy"
    LIQUIDITY = "Liquidity"
    BANKING = "Banking"
    REGULATION = "Regulation"
    INFLATION = "Inflation"
    GROWTH = "Growth"
    FX_EXTERNAL = "FX/External Sector"
    FINANCIAL_STABILITY = "Financial Stability"
    PAYMENTS = "Payments"
    OTHER = "Other"


# First listed category wins a tied score.
TIE_BREAK_ORDER = (
    Category.MONETARY_POLICY,
    Category.PAYMENTS,
    Category.FINANCIAL_STABILITY,
    Category.FX_EXTERNAL,
    Category.INFLATION,
    Category.GROWTH,
    Category.LIQUIDITY,
    Category.REGULATION,
    Category.BANKING,
    Category.OTHER,
)

TAXONOMY_VALUES = tuple(category.value for category in Category)
