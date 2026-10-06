#!/usr/bin/env python3
"""Тесты верификатора итогового проекта C01: политика diff и независимые тесты (Finding 8)."""
import shutil
import tempfile
from pathlib import Path
from verify_capstone import verify_capstone

CAPSTONE_DIR = Path(__file__).resolve().parent
STARTER = CAPSTONE_DIR / "starter"
SOLUTION = CAPSTONE_DIR / "solution"


def test_starter_fails_independent_tests():
    """Заготовка с дефектом обязана проваливать независимые тесты."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        ws = Path(tmp_dir)
        shutil.copy2(STARTER / "metrics.py", ws / "metrics.py")
        shutil.copy2(STARTER / "test_metrics.py", ws / "test_metrics.py")

        res = verify_capstone(ws, STARTER)
        assert res["status"] == "FAIL"
        assert res["tests_passed"] is False
        assert res["diff_policy"] == "PASS"


def test_solution_passes_verification():
    """Эталонное решение обязано проходить проверку и тесты."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        ws = Path(tmp_dir)
        shutil.copy2(SOLUTION / "metrics.py", ws / "metrics.py")
        shutil.copy2(STARTER / "test_metrics.py", ws / "test_metrics.py")

        res = verify_capstone(ws, STARTER)
        assert res["status"] == "PASS"
        assert res["tests_passed"] is True
        assert res["diff_policy"] == "PASS"


def test_modified_tests_rejected_by_diff_policy():
    """Попытка ослабить или изменить test_metrics.py должна отклоняться политикой diff."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        ws = Path(tmp_dir)
        shutil.copy2(SOLUTION / "metrics.py", ws / "metrics.py")
        bad_test = ws / "test_metrics.py"
        bad_test.write_text("# Weakened tests\nprint('PASS')\n", encoding="utf-8")

        res = verify_capstone(ws, STARTER)
        assert res["status"] == "FAIL"
        assert res["diff_policy"] == "FAIL"
        assert any("Нарушение политики diff" in e for e in res["errors"])


def test_extra_unapproved_files_rejected_by_diff_policy():
    """Появление любых неразрешённых файлов в workspace должно отклоняться политикой diff."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        ws = Path(tmp_dir)
        shutil.copy2(SOLUTION / "metrics.py", ws / "metrics.py")
        shutil.copy2(STARTER / "test_metrics.py", ws / "test_metrics.py")
        (ws / "extra_backdoor.py").write_text("# backdoor\n", encoding="utf-8")

        res = verify_capstone(ws, STARTER)
        assert res["status"] == "FAIL"
        assert res["diff_policy"] == "FAIL"
        assert any("обнаружен неразрешённый файл" in e for e in res["errors"])


def test_missing_test_file_fails_without_mutation():
    """Отсутствие test_metrics.py в workspace не должно автоматически чиниться verifier."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        ws = Path(tmp_dir)
        shutil.copy2(SOLUTION / "metrics.py", ws / "metrics.py")
        # test_metrics.py intentionally omitted

        res = verify_capstone(ws, STARTER)
        assert res["status"] == "FAIL"
        assert res["diff_policy"] == "FAIL"
        assert any("не найден в рабочем каталоге" in e for e in res["errors"])
        # Убеждаемся, что верификатор НЕ скопировал файл в ws (read-only)
        assert not (ws / "test_metrics.py").exists()


if __name__ == "__main__":
    test_starter_fails_independent_tests()
    test_solution_passes_verification()
    test_modified_tests_rejected_by_diff_policy()
    test_extra_unapproved_files_rejected_by_diff_policy()
    test_missing_test_file_fails_without_mutation()
    print("ALL CAPSTONE VERIFIER TESTS PASSED")
