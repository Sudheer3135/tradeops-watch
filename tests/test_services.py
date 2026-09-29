import random

import pytest

from services.market_feed import next_price
from services.order_service import order_side


@pytest.mark.parametrize("price", [0, 0.01, 1, 24000, 1_000_000])
@pytest.mark.parametrize("change", [-2, -1, -0.001, 0, 0.001])
def test_price_is_positive_even_at_floor(price, change):
    assert next_price(price, change) >= 1


def test_random_walk_bounds_over_many_steps():
    random.seed(42)
    price = 24000.0
    for _ in range(10000):
        updated = next_price(price)
        assert updated >= 1
        assert abs(updated - price) <= price * 0.001 + 0.0051
        price = updated


@pytest.mark.parametrize(
    ("price", "previous", "expected"), [(99, 100, "BUY"), (100, 100, "BUY"), (101, 100, "SELL")]
)
def test_order_rule(price, previous, expected):
    assert order_side(price, previous) == expected
