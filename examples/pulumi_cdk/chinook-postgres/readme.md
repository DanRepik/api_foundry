# Pulumi - Chinook Example

This folder contains a working API-MAKER deployment.

# Installation

1. Install the Python modules.  The example uses Pipenv to manage python virtual environments and resources.  To install those resources run;

```bash
pipenv install
```

2. The devtools.sh file contains alias and settings that streamline develop activaties.  To initialize a terminal environment with the devtools.sh run;

```bash
source devtools.sh
```

# Usage

## Dev Playground

The Dev Playground is a docker compose file that sets up both Localstack and a collection of databases running in Docker.  The playground provides a local environment where API-MAKER deployments can be made.

The Dev Playground runs with Postgres, Oracle, and MySQL databases and they are initialized with the Chinook open source database.

The playground must be running if your making local deployments and using the Chinook example databases.

**Start Playground**

To start the playground run;

```bash
playground_up
```

This is equivalent to;

```bash
docker-compose -f ../../../dev_playground/playground_compose.yaml up -d'
```

**Stop the Playground

To stop the playground run;

```bash
playground down
```

This is equivalent to;

```bash
docker-compose -f ../../../dev_playground/playground_compose.yaml down'
```

**Reset the Playground**

Reset allows restoring the databases back to their original state.

```bash
playground_reset
```

This is equivalent to;

```bash
playground_down; \
docker volume rm dev_playground_postgres_data dev_playground_oracle_data dev_playground_mysql_data; \
playground_up
```

# Running an Example Deployment

**AWS Configuration**

The devtools.sh script sets AWS_PROFILE to 'localstack' by default.

> Other AWS profiles can be used to make deployments to real AWS.

To deploy to Localstack you will need to add that profile to you AWS configuration.  To do that add the following to the '~/.aws/credentials' file;

```
[localstack]
aws_access_key_id = test
aws_secret_access_key = test
```

And to your '~/.aws/config' file add the following profile;

```
[profile localstack]
region = us-east-1
endpoint_url = http://localhost.localstack.cloud:4566
```

**Deploy to the Playground**

To make a deployment run;

```bash
up
```

This is equivalent to;

```bash
pulumi up --yes --stack local
```

**Destory a Deployment**

To destroy a deployment run;

```bash
down
```

This is equivalent to;

```bash
pulumi destroy --yes --stack local
```
