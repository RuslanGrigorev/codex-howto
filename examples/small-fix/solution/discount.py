def apply_discount(price: float, discount: float) -> float:
    """Применяет скидку к цене.
    
    Скидка должна быть в диапазоне от 0.0 до 1.0 (0% - 100%).
    При некорректном значении скидки выбрасывает ValueError.
    """
    if discount < 0.0 or discount > 1.0:
        raise ValueError("Некорректная скидка")
    return price * (1.0 - discount)
