import json

from api_maker.iac.pulumi.api_maker import APIMaker

api_maker = APIMaker(
    "chinook_postgres",
    props={
        "api_spec": "./chinook_api.yaml",
        "secrets": json.dumps({"chinook": "postgres/chinook"}),
    },
)
