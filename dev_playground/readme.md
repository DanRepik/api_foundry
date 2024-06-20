# Dev Playground

The Dev Playground is a docker compose file that sets up both Localstack and a collection of databases running in Docker.  The playground provides a local environment where API-MAKER deployments can be made.

The Dev Playground runs with Postgres, Oracle, and MySQL databases and they are initialized with the Chinook open source database.

The playground must be running if your making local deployments and using the Chinook example databases.

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

# Configuration

By default when starting a database with a new volume the playground data set are used for the ininitization.  This folder can be overidden using the following environment variables to allow custom data sets to be used;

* POSTGRES_INIT_DB
* ORACLE_INIT_DB
* MYSQL_INIT_DB

For example;

```bash
POSTGRES_INIT_DB=/my_postgres_db playground_postgres
```
