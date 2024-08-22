
export AWS_ENDPOINT_URL=http://localhost.localstack.cloud:4566
export AWS_PROFILE=localstack

alias test="API_SPEC=resources/chinook_api.yaml pytest -v --cov=src/api_foundry/ --cov-report=xml tests/; coverage html"
