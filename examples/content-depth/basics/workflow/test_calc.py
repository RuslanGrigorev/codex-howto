from calc import divide_and_round

def test_divide():
    assert divide_and_round(10, 2) == 5.0
    assert divide_and_round(10, 3, 2) == 3.33
    try:
        divide_and_round(5, 0)
        assert False, "Ожидалось исключение ZeroDivisionError при делении на 0"
    except ZeroDivisionError:
        pass
    print("PASS: B01 calc tests")

if __name__ == "__main__":
    test_divide()
