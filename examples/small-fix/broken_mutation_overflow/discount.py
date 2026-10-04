def apply_discount(price: float, discount: float) -> float:
    # Мутация 2: пропускает скидки более 100%
    if discount < 0.0:
        raise ValueError("Некорректная скидка")
    return price * (1.0 - discount)
