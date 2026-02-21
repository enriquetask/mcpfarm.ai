"""Tests for API schemas."""

import pytest
from pydantic import ValidationError

from mcpfarm_gateway.api.schemas import ServerCreate


def test_server_create_valid():
    s = ServerCreate(name="Echo", namespace="echo", image="echo-server")
    assert s.name == "Echo"
    assert s.namespace == "echo"
    assert s.port == 9001
    assert s.auto_restart is True


def test_server_create_namespace_validation():
    # Must start with lowercase letter, only [a-z0-9_]
    with pytest.raises(ValidationError):
        ServerCreate(name="Bad", namespace="Echo", image="img")  # uppercase
    with pytest.raises(ValidationError):
        ServerCreate(name="Bad", namespace="1echo", image="img")  # starts with digit
    with pytest.raises(ValidationError):
        ServerCreate(name="Bad", namespace="", image="img")  # empty


def test_server_create_defaults():
    s = ServerCreate(name="Test", namespace="test", image="img")
    assert s.env_vars == {}
    assert s.port == 9001
