"""
Throttling: every stage gets a default limit, which the spec's top-level
``x-af-throttle`` replaces, and a path operation's own ``x-af-throttle`` sets that
route's limit. The limits become API Gateway method settings on the stage.
"""

import asyncio

import pulumi
import pytest

import cloud_foundry
from api_foundry.iac.pulumi.api_foundry import (
    DEFAULT_THROTTLE,
    APIFoundry,
    throttle_limits,
)

SPEC = {
    "openapi": "3.0.0",
    "paths": {
        "/anchors/{anchor_id}/partitions": {
            "get": {"x-af-throttle": {"rate": 5, "burst": 10}},
        },
        "/partitions/search": {"get": {}},
    },
}


@pytest.mark.unit
def test_default_limit_covers_the_stage():
    assert throttle_limits({"openapi": "3.0.0"}) == {
        "*/*": {
            "rate": float(DEFAULT_THROTTLE["rate"]),
            "burst": DEFAULT_THROTTLE["burst"],
        }
    }


@pytest.mark.unit
def test_spec_and_operation_limits():
    limits = throttle_limits(
        {**SPEC, "x-af-throttle": {"rate": 50, "burst": 100}}, "/api"
    )
    assert limits == {
        "*/*": {"rate": 50.0, "burst": 100},
        # The prefixed resource path, its slashes written as "~1".
        "~1api~1anchors~1{anchor_id}~1partitions/GET": {"rate": 5.0, "burst": 10},
    }
    assert "~1anchors~1{anchor_id}~1partitions/GET" in throttle_limits(SPEC)


@pytest.mark.unit
@pytest.mark.parametrize(
    "limit",
    [
        {"rate": 5},
        {"rate": 0, "burst": 10},
        {"rate": 5, "burst": 2.5},
        {"rate": "5", "burst": 10},
        {"rate": True, "burst": 10},
        10,
    ],
)
def test_bad_limits_are_refused(limit):
    with pytest.raises(ValueError, match="x-af-throttle"):
        throttle_limits({"openapi": "3.0.0", "x-af-throttle": limit})
    with pytest.raises(ValueError, match="GET /x"):
        throttle_limits(
            {"openapi": "3.0.0", "paths": {"/x": {"get": {"x-af-throttle": limit}}}}
        )


class FakeFunction:
    name = "test-function"
    arn = "arn:aws:lambda:us-east-1:123456789012:function:test-function"


class FakeRestAPI:
    domain = "test.example.com"
    rest_api_id = "test-api-id"
    stage_name = "test-api"


@pytest.mark.unit
def test_limits_become_method_settings(monkeypatch):
    created = []

    class Mocks(pulumi.runtime.Mocks):
        def new_resource(self, args):
            if args.typ == "aws:apigateway/methodSettings:MethodSettings":
                created.append(args.inputs)
            return [args.name + "_id", dict(args.inputs)]

        def call(self, args):
            return {}

    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())
    pulumi.runtime.set_mocks(Mocks(), preview=False)
    monkeypatch.setattr(
        cloud_foundry, "python_function", lambda **kwargs: FakeFunction()
    )
    monkeypatch.setattr(
        cloud_foundry, "rest_api", lambda *args, **kwargs: FakeRestAPI()
    )

    @pulumi.runtime.test
    def program():
        return APIFoundry("test-api", api_spec=[], path_prefix="/api").domain

    monkeypatch.setattr(
        "api_foundry.iac.pulumi.api_foundry.load_api_spec", lambda _spec: SPEC
    )
    program()

    settings = {c["methodPath"]: c for c in created}
    assert set(settings) == {"*/*", "~1api~1anchors~1{anchor_id}~1partitions/GET"}
    route = settings["~1api~1anchors~1{anchor_id}~1partitions/GET"]
    assert route["restApi"] == "test-api-id" and route["stageName"] == "test-api"
    assert route["settings"] == {"throttlingRateLimit": 5.0, "throttlingBurstLimit": 10}
