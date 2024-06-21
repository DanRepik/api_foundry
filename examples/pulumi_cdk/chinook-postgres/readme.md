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

## AWS Configuration

In order to make deployments valid AWS credentials must be provided. The devtools.sh script sets AWS_PROFILE to 'localstack' by default however this can be overridden it needed.

To deploy to Localstack you will need to add a 'localstack' profile to you AWS configuration.  To do that add the following to the '~/.aws/credentials' file;

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

## Dev Playground

The Dev Playground is a docker compose file that sets up both Localstack and a collection of databases running in Docker.  The playground provides a local environment where API-MAKER deployments can be made.

The Dev Playground runs with Postgres, Oracle, and MySQL databases and they are initialized with the Chinook open source database.

The playground must be running when making local deployments and using the Chinook example databases.

**Start Playground**

To start the playground run;

```bash
playground_up
```

Individual databases can be started with;

```bash
playground_postgres
playground_oracle
playground_mysql
```


**Stop the Playground**

To stop the playground run;

```bash
playground_down
```

**Reset the Playground**

Reset allows restoring the databases back to their original state.

```bash
playground_reset
```

Resetting the database shuts down all playground containers and removes the database volumes.

# Running an Example Deployment

**Deploy to the Playground**

To make a deployment run;

```bash
up
```

**Destory a Deployment**

To destroy a deployment run;

```bash
down
```
