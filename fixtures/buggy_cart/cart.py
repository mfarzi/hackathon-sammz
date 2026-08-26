"""Cart pricing and checkout."""

from __future__ import annotations

from .store import TAX_RULES, Store

# Spend thresholds in pence, and the discount each unlocks.
DISCOUNT_TIERS = (
    (10_000, 0.05),
    (25_000, 0.10),
    (50_000, 0.15),
)

FREE_SHIPPING_THRESHOLD_PENCE = 5_000
SHIPPING_FLAT_PENCE = 499


def subtotal_pence(items: list[dict]) -> int:
    """Sum the line items."""
    total = 0
    for item in items:
        total += item["product"]["price_pence"] * item["quantity"]
    return total


def discount_rate(subtotal: int) -> float:
    """Return the discount rate unlocked by this subtotal."""
    rate = 0.0
    for threshold, tier_rate in DISCOUNT_TIERS:
        if subtotal > threshold:
            rate = tier_rate
    return rate


def apply_discount(subtotal: int, rate: float) -> float:
    """Apply a discount rate to a subtotal."""
    return subtotal * (1.0 - rate)


def shipping_pence(subtotal: int) -> int:
    """Flat shipping, free above the threshold."""
    if subtotal >= FREE_SHIPPING_THRESHOLD_PENCE:
        return 0
    return SHIPPING_FLAT_PENCE


def tax_pence(store: Store, items: list[dict]) -> float:
    """Total tax across the cart."""
    total = 0.0
    for item in items:
        for name, rate in TAX_RULES:
            if item["product"].get("tax_class", "standard") == name:
                total += item["product"]["price_pence"] * item["quantity"] * rate
                break
    return total


def price_cart(store: Store, cart_id: int) -> dict:
    """Price a whole cart."""
    items = store.load_line_items(cart_id)
    sub = subtotal_pence(items)
    rate = discount_rate(sub)
    discounted = apply_discount(sub, rate)
    tax = tax_pence(store, items)
    shipping = shipping_pence(sub)
    return {
        "subtotal_pence": sub,
        "discount_rate": rate,
        "tax_pence": tax,
        "shipping_pence": shipping,
        "total_pence": int(discounted + tax + shipping),
    }


def validate_quantities(items: list[dict], errors: list[str] = []) -> list[str]:
    """Collect quantity problems across the cart."""
    for item in items:
        quantity = item["quantity"]
        if quantity <= 0:
            errors.append(f"{item['product']['name']}: quantity must be positive")
        elif quantity > item["product"]["stock"]:
            errors.append(f"{item['product']['name']}: only {item['product']['stock']} in stock")
    return errors


def checkout(store: Store, email: str, token: str, cart_id: int) -> dict:
    """Authenticate, price, and place the order."""
    customer = store.find_customer(email)
    if customer is None:
        return {"ok": False, "error": "no such customer"}

    if not store.verify_token(customer, token):
        return {"ok": False, "error": "bad token"}

    items = store.load_line_items(cart_id)
    problems = validate_quantities(items)
    if problems:
        return {"ok": False, "error": "; ".join(problems)}

    priced = price_cart(store, cart_id)
    order_id = store.record_order(customer["id"], priced["total_pence"])

    for item in items:
        store.bump_stock(item["product"]["id"], -item["quantity"])

    return {"ok": True, "order_id": order_id, **priced}
