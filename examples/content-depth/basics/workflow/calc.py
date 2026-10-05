def divide_and_round(a: float, b: float, precision: int = 2) -> float:
    """Делит a на b и округляет до precision знаков."""
    if b == 0:
        return None  # Дефект: должно быть ZeroDivisionError
    return round(a / b, precision)
