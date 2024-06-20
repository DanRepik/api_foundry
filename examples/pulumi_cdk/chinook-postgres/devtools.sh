alias up="pulumi up --yes --stack local"
alias down="pulumi destroy --yes --stack local"

echo "echo $(dirname "$0")/../../../dev_playground/devtools.sh"

source "$(dirname "$0")/../../../dev_playground/devtools.sh"

export AWS_PROFILE=localstack
