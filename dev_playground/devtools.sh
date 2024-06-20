# Get the directory of the current script
SCRIPT_DIR="$(dirname "$0")"

alias playground_up="docker-compose --profile all -f $SCRIPT_DIR/playground_compose.yaml up -d"
alias playground_down="docker-compose --profile all -f $SCRIPT_DIR/playground_compose.yaml down"
alias playground_reset="playground_down; docker volume rm dev_playground_postgres_data dev_playground_oracle_data dev_playground_mysql_data"

alias playground_postgres="docker-compose --profile  postgres -f $SCRIPT_DIR/playground_compose.yaml up -d"
alias playground_oracle="docker-compose --profile  oracle -f $SCRIPT_DIR/playground_compose.yaml up -d"
alias playground_mysql="docker-compose --profile  mysql -f $SCRIPT_DIR/playground_compose.yaml up -d"
