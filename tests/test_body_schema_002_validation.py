"""Boundary tests for validation exposure; never generate an organism."""
import json
from pathlib import Path
import pytest
from learning import body_schema_002_validation as validation


def test_validation_freeze_cannot_be_overwritten(tmp_path,monkeypatch):
    frozen=tmp_path/'manifest.json'; frozen.write_text('{}')
    monkeypatch.setattr(validation,'FROZEN',frozen)
    with pytest.raises(ValueError,match='immutable'): validation.freeze()
    assert frozen.read_text()=='{}'


def test_validation_refuses_changed_source_before_bank_access(tmp_path,monkeypatch):
    manifest=json.loads(validation.FROZEN.read_bytes())
    frozen=tmp_path/'manifest.json'; frozen.write_text(json.dumps(manifest))
    bank=tmp_path/'bank'
    monkeypatch.setattr(validation,'FROZEN',frozen); monkeypatch.setattr(validation,'VALID',bank)
    monkeypatch.setattr(validation,'current_tests',lambda: ({'changed':True},{}))
    with pytest.raises(ValueError,match='changed since'): validation.run_validation()
    assert not bank.exists()


def test_validation_bank_is_not_silently_reopened(tmp_path,monkeypatch):
    manifest=json.loads(validation.FROZEN.read_bytes())
    frozen=tmp_path/'manifest.json'; frozen.write_text(json.dumps(manifest))
    bank=tmp_path/'bank'; bank.mkdir()
    monkeypatch.setattr(validation,'FROZEN',frozen); monkeypatch.setattr(validation,'VALID',bank)
    monkeypatch.setattr(validation,'current_tests',lambda: (manifest['source_frozen'],manifest['tests_frozen']))
    with pytest.raises(ValueError,match='already exposed'): validation.run_validation()
    assert not list(bank.iterdir())
