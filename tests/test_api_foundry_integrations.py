"""
Regression test: APIFoundry.integrations() must not crash.

APIFoundry declared `api_spec_editor: APISpecEditor` as a class-level type
annotation but only ever assigned the constructed APISpecEditor to the
local variable `gateway_spec` - never to `self.api_spec_editor`. Calling
integrations() (`return self.api_spec_editor.integrations`) therefore
raised AttributeError.

Heavy dependencies (cloud_foundry.python_function, cloud_foundry.rest_api,
which build real Lambda archives and API Gateway resources) are stubbed
out so this test only exercises APIFoundry's own wiring, using pulumi's
mock runtime (no AWS/network access needed).
"""

import pulumi
import pytest

import cloud_foundry
from api_foundry.iac.pulumi.api_foundry import APIFoundry

MINIMAL_SPEC = """
openapi: 3.0.0
info:
  title: Test API
  version: 1.0.0
components:
  schemas:
    album:
      type: object
      x-af-database: chinook
      properties:
        album_id:
          type: integer
          x-af-primary-key: auto
        title:
          type: string
"""


class FakeFunction:
    name = "test-function"
    arn = "arn:aws:lambda:us-east-1:123456789012:function:test-function"


class FakeRestAPI:
    domain = "test.example.com"


@pytest.fixture
def mocked_pulumi():
    class Mocks(pulumi.runtime.Mocks):
        def new_resource(self, args):
            return [args.name + "_id", dict(args.inputs)]

        def call(self, args):
            return {}

    pulumi.runtime.set_mocks(Mocks(), preview=False)


@pytest.mark.unit
def test_integrations_does_not_raise(mocked_pulumi, monkeypatch):
    monkeypatch.setattr(
        cloud_foundry, "python_function", lambda **kwargs: FakeFunction()
    )
    monkeypatch.setattr(
        cloud_foundry, "rest_api", lambda *args, **kwargs: FakeRestAPI()
    )

    api_foundry = APIFoundry("test-api", api_spec=MINIMAL_SPEC)

    # Must not raise AttributeError: 'APIFoundry' object has no attribute
    # 'api_spec_editor'
    result = api_foundry.integrations()
    assert result == api_foundry.api_spec_editor.integrations
