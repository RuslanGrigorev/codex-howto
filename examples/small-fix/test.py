"""test.py - Автономный проверочный тест для упражнения small-fix."""

import sys
from pathlib import Path

# Импортируем проверяемый модуль
try:
    from discount import apply_discount
except ImportError:
    print("ОШИБКА: Файл discount.py не найден или не содержит apply_discount.", file=sys.stderr)
    sys.exit(1)


def test_normal_discount():
    res = apply_discount(100.0, 0.2)
    assert abs(res - 80.0) < 1e-6, f"Ожидалось 80.0, получено {res}"


def test_zero_discount():
    res = apply_discount(100.0, 0.0)
    assert abs(res - 100.0) < 1e-6, f"Ожидалось 100.0, получено {res}"


def test_full_discount():
    res = apply_discount(100.0, 1.0)
    assert abs(res - 0.0) < 1e-6, f"Ожидалось 0.0, получено {res}"


def test_negative_discount_raises():
    try:
        apply_discount(100.0, -0.1)
    except ValueError:
        return
    assert False, "Скидка < 0 должна вызывать ValueError"


def test_overflow_discount_raises():
    try:
        apply_discount(100.0, 1.5)
    except ValueError:
        return
    assert False, "Скидка > 1.0 должна вызывать ValueError"


def main():
    try:
        test_normal_discount()
        test_zero_discount()
        test_full_discount()
        test_negative_discount_raises()
        test_overflow_discount_raises()
        print("PASS: Все проверки упражнения small-fix пройдены.")
        sys.exit(0)
    except AssertionError as e:
        print(f"FAIL: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Непредвиденная ошибка: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
