"""Tests for codex_backend protocol layer."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))


def test_decode_jwt_payload_invalid_returns_none():
    from codex_backend import _decode_jwt_payload
    assert _decode_jwt_payload("garbage") is None
    assert _decode_jwt_payload("foo.bar") is None  # base64 decode fails
    assert _decode_jwt_payload("") is None


def test_ref_ext_whitelist_excludes_svg_bmp_gif():
    from codex_backend import _REF_EXT_WHITELIST
    assert "png" in _REF_EXT_WHITELIST
    assert "jpeg" in _REF_EXT_WHITELIST
    assert "jpg" in _REF_EXT_WHITELIST
    assert "webp" in _REF_EXT_WHITELIST
    assert "svg" not in _REF_EXT_WHITELIST
    assert "bmp" not in _REF_EXT_WHITELIST
    assert "gif" not in _REF_EXT_WHITELIST


def test_detect_returns_dict_with_available_or_missing():
    from codex_backend import detect
    info = detect()
    assert isinstance(info, dict)
    assert "available" in info
    if info["available"]:
        assert "credit" in info
    else:
        assert "missing" in info


def test_read_token_no_auth_file(monkeypatch, tmp_path):
    """When ~/.codex/auth.json doesn't exist, _read_token returns None."""
    import codex_backend
    monkeypatch.setattr(codex_backend, "CODEX_AUTH_PATH", tmp_path / "nonexistent.json")
    assert codex_backend._read_token() is None


def test_read_token_oversized_returns_none(monkeypatch, tmp_path):
    """auth.json > 1MB rejected."""
    import codex_backend
    fake_auth = tmp_path / "auth.json"
    fake_auth.write_bytes(b"x" * 1_500_000)
    monkeypatch.setattr(codex_backend, "CODEX_AUTH_PATH", fake_auth)
    assert codex_backend._read_token() is None


def test_read_token_invalid_json_returns_none(monkeypatch, tmp_path):
    import codex_backend
    fake_auth = tmp_path / "auth.json"
    fake_auth.write_text("not json")
    monkeypatch.setattr(codex_backend, "CODEX_AUTH_PATH", fake_auth)
    assert codex_backend._read_token() is None


def test_read_token_jwt_decode_failure_returns_none(monkeypatch, tmp_path):
    """Bug 2 fix: JWT decode failure now hard-rejects, not silent fallthrough."""
    import codex_backend, json
    fake_auth = tmp_path / "auth.json"
    fake_auth.write_text(json.dumps({"tokens": {"access_token": "garbage_not_jwt"}}))
    monkeypatch.setattr(codex_backend, "CODEX_AUTH_PATH", fake_auth)
    assert codex_backend._read_token() is None


def test_read_token_missing_exp_returns_none(monkeypatch, tmp_path):
    """Fix 4: missing or zero exp claim now rejected (was: silently passed)."""
    import codex_backend, json, base64
    # JWT with no exp
    payload = base64.urlsafe_b64encode(json.dumps({"foo": "bar"}).encode()).decode().rstrip("=")
    token = f"header.{payload}.sig"
    fake_auth = tmp_path / "auth.json"
    fake_auth.write_text(json.dumps({"tokens": {"access_token": token}}))
    monkeypatch.setattr(codex_backend, "CODEX_AUTH_PATH", fake_auth)
    assert codex_backend._read_token() is None


def test_read_token_zero_exp_returns_none(monkeypatch, tmp_path):
    """Fix 4: exp=0 explicitly rejected."""
    import codex_backend, json, base64
    payload = base64.urlsafe_b64encode(json.dumps({"exp": 0}).encode()).decode().rstrip("=")
    token = f"header.{payload}.sig"
    fake_auth = tmp_path / "auth.json"
    fake_auth.write_text(json.dumps({"tokens": {"access_token": token}}))
    monkeypatch.setattr(codex_backend, "CODEX_AUTH_PATH", fake_auth)
    assert codex_backend._read_token() is None
