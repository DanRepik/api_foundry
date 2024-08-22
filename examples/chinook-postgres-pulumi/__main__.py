import json

from api_foundry.iac.pulumi.api_foundry import APIMaker

api_foundry = APIMaker(
    "chinook_postgres",
    props={
        "api_spec": "./chinook_api.yaml",
        "secrets": json.dumps({"chinook": "postgres/chinook"}),
    },
)
