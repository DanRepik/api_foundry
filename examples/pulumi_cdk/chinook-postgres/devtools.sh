alias up="pulumi up --yes --stack local"
alias down="pulumi down --yes --stack local"

alias playground_up="docker-compose -f ../../../dev_playground/playground_compose.yaml up -d"
alias playground_down="docker-compose -f ../../../dev_playground/playground_compose.yaml down"

export AWS_PROFILE=localstack
