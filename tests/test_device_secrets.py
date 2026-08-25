import os

import pytest

from tools.generate_device_secrets import c_string, write_pair_atomic


def test_c_string_escapes_quotes_and_backslashes():
    assert c_string('a"b\\c') == '"a\\"b\\\\c"'


def test_c_string_rejects_newlines():
    with pytest.raises(ValueError, match="NUL/newline"):
        c_string("secret\nvalue")


def test_pair_rotation_rolls_back_both_files_on_replace_failure(tmp_path, monkeypatch):
    first = tmp_path / "esp32_secrets.h"
    second = tmp_path / "wvab_edge.env"
    first.write_text("old-header", encoding="utf-8")
    second.write_text("old-env", encoding="utf-8")

    real_replace = os.replace
    failed = {"done": False}

    def flaky_replace(src, dst):
        if not failed["done"] and str(dst) == str(second) and ".tmp-" in os.path.basename(str(src)):
            failed["done"] = True
            raise OSError("simulated second-file replace failure")
        return real_replace(src, dst)

    monkeypatch.setattr(os, "replace", flaky_replace)

    with pytest.raises(OSError, match="simulated"):
        write_pair_atomic([(first, "new-header"), (second, "new-env")])

    assert first.read_text(encoding="utf-8") == "old-header"
    assert second.read_text(encoding="utf-8") == "old-env"
    assert not list(tmp_path.glob("*.tmp-*"))
    assert not list(tmp_path.glob("*.backup-*"))


def test_pair_rotation_writes_both_files(tmp_path):
    first = tmp_path / "esp32_secrets.h"
    second = tmp_path / "wvab_edge.env"
    write_pair_atomic([(first, "header"), (second, "env")])
    assert first.read_text(encoding="utf-8") == "header"
    assert second.read_text(encoding="utf-8") == "env"
