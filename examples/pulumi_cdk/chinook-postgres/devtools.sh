alias up="pulumi up --yes --stack local"
alias down="pulumi destroy --yes --stack local"

# import playground commands
source "$(dirname "$0")/../../../dev_playground/devtools.sh"

export AWS_PROFILE=localstack
