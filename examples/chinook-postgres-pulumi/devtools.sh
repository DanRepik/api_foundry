alias up="pulumi up --yes --stack dev"
alias down="pulumi destroy --yes --stack dev"

# import playground commands
source "$(dirname "$0")/../../../localstack_playground/devtools.sh"

alias dev_up="playground_postgres; ./install_secrets.py"
alias dev_down="playground_down"
alias dev_reset="playground_reset"

export AWS_PROFILE=localstack
