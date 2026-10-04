def apply_discount(price: float, discount: float) -> float:
    # Мутация 1: пропускает отрицательные скидки
    if discount > 1.0:
        raise ValueError("Некорректная скидка")
    return price * (1.0 - discount)
