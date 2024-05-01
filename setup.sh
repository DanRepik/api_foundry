
#export AWS_ENDPOINT_URL=http://localhost.localstack.cloud:4566
export AWS_PROFILE=localstack

alias coverage="API_SPEC=resources/chinook_api.yaml pytest -v --cov=src/api_maker/ --cov-report=xml tests/"
alias quick="API_SPEC=resources/chinook_api.yaml pytest -v --cov=src/api_maker/ --cov-report=xml  -m quick tests/"
