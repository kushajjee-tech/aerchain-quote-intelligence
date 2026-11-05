"""M0: storage guard (architecture §5.1 control 1, PRD NF-9)."""
import os

import pytest

from app.storage import Storage, StorageGuardError


def test_read_write_inside_root(data_root):
    st = Storage(data_root)
    st.write_bytes("inbox/a.eml", b"hello")
    assert st.read_bytes("inbox/a.eml") == b"hello"
    assert list(st.iter_files("inbox")) == ["inbox/a.eml"]


@pytest.mark.parametrize("bad", ["../escape.txt", "inbox/../../escape.txt", "/etc/passwd"])
def test_escape_refused(data_root, bad):
    st = Storage(data_root)
    with pytest.raises(StorageGuardError):
        st.safe_path(bad)


def test_symlink_escape_refused(data_root, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.json").write_text("{}")
    os.symlink(outside, data_root / "link")
    st = Storage(data_root)
    with pytest.raises(StorageGuardError):
        st.read_bytes("link/secret.json")
    os.symlink(outside / "secret.json", data_root / "file_link.json")
    with pytest.raises(StorageGuardError):
        st.read_bytes("file_link.json")


def test_open_binary_requires_binary_mode(data_root):
    st = Storage(data_root)
    with pytest.raises(ValueError):
        st.open_binary("x.txt", "w")
