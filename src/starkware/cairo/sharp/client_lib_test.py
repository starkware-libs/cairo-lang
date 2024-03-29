import base64
import dataclasses
import json

import pytest
from pytest import MonkeyPatch
from urllib3 import PoolManager

from starkware.cairo.sharp.client_lib import ClientLib


class MockCairoPie:
    """
    Mock classes used in the test.
    """

    def serialize(self):
        return b""


@dataclasses.dataclass
class Response:
    data: bytes


EXPECTED_URL = "https://some_url/"


def test_add_job(monkeypatch: MonkeyPatch):
    expected_data = {
        "action": "add_job",
        "request": {"cairo_pie": base64.b64encode(MockCairoPie().serialize()).decode("ascii")},
    }
    expected_res = "some id"

    # A mock function enforcing expected scenario.
    def check_expected(_, method: str, url: str, body: str):
        assert method == "POST"
        assert url == EXPECTED_URL + expected_data["action"]
        assert json.loads(body) == expected_data
        return Response(json.dumps({"cairo_job_key": expected_res}).encode("utf-8"))

    monkeypatch.setattr(PoolManager, "request", check_expected)

    # Test the scenario.
    client = ClientLib(url=EXPECTED_URL)
    res = client.add_job(MockCairoPie())
    assert res == expected_res


def test_get_status(monkeypatch: MonkeyPatch):
    expected_id = "some id"
    expected_data = {"action": "get_status", "request": {"cairo_job_key": expected_id}}
    expected_res = "the status"

    # A mock function enforcing expected scenario.
    def check_expected(_, method: str, url: str, body: str):
        assert method == "POST"
        assert url == EXPECTED_URL + expected_data["action"]
        assert json.loads(body) == expected_data
        return Response(json.dumps({"status": expected_res}).encode("utf-8"))

    monkeypatch.setattr(PoolManager, "request", check_expected)

    # Test the scenario.
    client = ClientLib(url=EXPECTED_URL)
    res = client.get_status(expected_id)
    assert res == expected_res


def test_error(monkeypatch: MonkeyPatch):
    # A mock function enforcing expected scenario.
    def check_expected(_, method: str, url: str, body: str):
        # Return an empty response - this should be invalid.
        return Response(b"{}")

    monkeypatch.setattr(PoolManager, "request", check_expected)

    # Test the scenario.
    client = ClientLib(url=EXPECTED_URL)

    with pytest.raises(AssertionError, match="Error when sending job to SHARP:"):
        client.add_job(MockCairoPie())

    with pytest.raises(AssertionError, match="Error when checking status of job with key"):
        client.get_status("")
