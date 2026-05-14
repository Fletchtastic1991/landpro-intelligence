def estimate_price(operations, config):
    """
    Price based on real operational cost + margin
    """

    base_cost = operations["total_operational_cost"]

    # Base markup
    markup = config["base_markup"]

    # Optional: difficulty adjustment
    difficulty = operations.get("difficulty_score", 50)

    if difficulty > 70:
        markup += config["high_difficulty_markup"]
    elif difficulty < 30:
        markup -= config["low_difficulty_discount"]

    price = base_cost * markup

    return round(price, 2)