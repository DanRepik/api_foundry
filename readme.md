# API-MAKER

Welcome to API-Maker, an open-source tool designed for rapidly building and exposing relational database resource as RESTful services.  The project's primary objective is to offer a solution that requires minimal coding effort to query and manipulate data stored in relational databases.

Database resources that API-MAKER can expose as services can be tables or custom SQL.

With database table resources API-MAKER provides services to support the normal CRUD operations.  Additionally with table resourses API-MAKER provides a rich record selection API that reduces the need to build custom functions.

Custom SQL operations can also be exposed.

In the following sections we will provide a brief overview of the following API-MAKER features;

* [Build an API](#Build an API in Five Minutes) - this section provides an abbreviated example of building an API.
* [Exploring the API deployment](#What API-Maker Deploys) - Briefly looks at resulting the API-MAKER deployment.
* **Exploring the Services** - This section delves into the API services that that was built, covered are basic operations and the enhanced record selection capabilities provided.
* **Using Metadata Parameters** - These parameters allow requesting application to customize the results returned from the services.
* **Managing Concurrency** - This section illustrates how API-MAKER handles currency between application clients.
* **Object and List Properties** - API-MAKER can return objects that have objects or list of objects as properties.  This section demonstrates how to configure such properties.

The examples presented here are accessing data in a Chinook database.  What is presented in the example is an subset of a complete working example that can be found in the examples.

## Build an API in Five Minutes

There are three steps to building an API-MAKER api;

1. Define the resources to be exposed in an OpenAPI document.
1. Create a secret containing the connection parameters to access the database.
1. Deploy the API-Maker as part of a IAC resource to AWS.

This section provides a quick overview of building an minimal API using API-MAKER.  The examples presented here a accessing data in a Chinook database.  What is presented is an subset of a complete working example that can be found in the examples.

**Define Schema Objects**

The first step is to define the database table as a component schema object in the API specification. This specfication uses the OpenAPI specfication.

In the abbreviated specification we are only building services albums and artists.

```yaml
# filename: chinook_postgres.yaml
openapi: 3.1.0
info:
  title: Chinook RestAPI
  version: 1.0.0
components:
  schemas:
    album:
      type: object
      x-am-database: chinook
      properties:
        album_id:
          type: integer
          x-am-primary-key: auto
        title:
          type: string
          maxLength: 160
        artist_id:
          type: integer
      required:
        - album_id
        - title
        - artist_id
    artist:
      type: object
      x-am-database: chinook
      properties:
        artist_id:
          type: integer
          x-am-primary-key: auto
        name:
          type: string
          maxLength: 120
      required:
        - artist_id
```

The above is standard OpenAPI specification with the except ion of the custom attributes.  API-MAKER always prefixes its custom attributes with 'x-am-'.

In this example the following API-MAKER attributes have been added;

* x-am-database - This indicates what database should be accessed for the built services.
* x-am-primary-key - This attribute can be attached to one of the object properties to indicate that property is the primary key for the component object.  The value of this property is the key generation strategy to use for record creation.

In this example table names, albums and artists, is same as the component object names and in turn in the API path operations.  API-MAKER provides additional custom attributes that allow explicit naming of the table.

> TODO: Link to custom attribute documentation

**Define the Database Access Secret**

For the second step you will need to supply API-MAKER with connection parameters for access to databases.

With API-MAKER the connection parameters needed to access the backend database is obtained using a AWS secretsmanager secret.  This secret should be a JSON string defining the connection parameters needed. The following script creates a secret for accessing the Chinook database running on Postgres.

```python
import boto3

# Create a Secrets Manager client
client = boto3.client("secretsmanager")

client.create_secret(
  Name="postgres/chinook",
  SecretString=json.dumps(
    {
        "engine": "postgres",
        "dbname": "chinook",
        "username": "chinook_user",
        "password": "chinook_password",
        "host": "postgres_db",
    }
  )
)

```

**Deploy the API**

The final step is to deploy the API.  In the example the deployment is made using Pulumi.

```python
#filename: __main.py__
from api_maker.iac.pulumi.api_maker import APIMaker

api_maker = APIMaker(
    "chinook-postgres",
    props={
        # this references the OpenAPI file created
        # in the first step
        "api_spec": "./chinook_api.yaml",

        # This parameter maps databases referenced in
        # the api_spec to secret names
        "secrets": json.dumps({"chinook": "postgres/chinook"}),
    },
)
```

## What API-Maker Deploys

Once the API-Maker deployment is complete

```plantuml
@startuml
title Deployment Diagram for API-MAKER api with External Database

actor Client as client

node "AWS" {
    node "API-MAKER" {
      [API Gateway] as apigw
      [Lambda Function] as lambda
    }
    [Secret] as secret
}

database "External Database" as db

client --> apigw : API Request
apigw --> lambda : Invoke Lambda
lambda --> db : Database Query
lambda --> secret : reads
db --> lambda : Database Response
lambda --> apigw : Lambda Response
apigw --> client : API Response

@enduml
```

## Using API-Maker Services

In this section we will explore the API services that API-MAKER provides.  Most of the examples will be restricted to the abbreviated example API specification.  However some examples will use resources defined in the complete Chinook API specification.

### Basic Operations

First basic CRUD services are supported.

These services are RESTful using the HTTP method to determine the operation.  Data passed via requests and response is of course in JSON.

Services return the operation status via response headers.  For successful operations the response body contains an array of the selected objects.  When mutating records via POST, PUT, and DELETE the body contains the array of modified or deleted records.

For these sevices the operation path is of the form;

```
# for POST
/{entity}
# for GET, PUT and DELETE
/{entity}/{id}
```

Where;

* entity - is the schema compoenent object name from the API  specification.  In the example case this would be either album or artist.
* id - is the primary key of the selected record.

> TODO: put link to tests

### Enhanced Record Selection

In addition to basic CRUD operations API-MAKER offers a set of services that provide enhanced record selection using query strings.  With this feature multiple records can be selected and does not apply to create operations.  The path for these services is;

```
# for GET, PUT and DELETE
/{entity}
```

Records are then selected using query string parameters. Where the name for the name value pair of a parameter can be any property defined the component schema object.

Thus for the Chinook database we could execute the following operations;

```
# get an artist, same as /artist/3
GET /artist?artist_id=3

# get an album, same as /album/5
GET /album/album_id=5

# get the albums by an artist
GET /album/artist_id=3

# using the complete specification
# get the invoices where the billing country is USA and the total was $3.96
GET /invoice?total3.96&billing_country=USA
```

**Relational Expressions**

Additionally, a relational operand can be prefixed to the value of a parameter. These operands allow records to be selected based on specific criteria, rather than being restricted to exact matches. The available relational operands listed below and are used by prefixing them to the value and separated by ::.

* lt (less than)
* le (less than or equal to)
* eq (equal to)
* ne (not equal to)
* ge (greater than or equal to)
* gt (greater than)
* in (in a list of values)
* between (between a range of values)
* not-between (not between a range of values)

Below are examples of API requests using these operands:

```
# read ablums with an album_id of less than 100
GET /ablum?album_id=lt::100

# read invoices that total either $3.96 or $5.94
GET /invoice?total=in::5.94,3.96

# read invoices that are between $3.00 and $6.00
GET /invoice?total=between::3,6
```

### Using Metadata Parameters

Additionally requests can include metadata parameters in query strings.  These parameters allow the requesting application to send additional instructions to apply to the request.

Metadata parameters are always prefixed with a double underscore '__'.

**__properties**

This parameter allows restricting the contents of objects returned.  The value of this paremeter is a spce delimited list of regular expressions.  When provided result sets are restricted to only properties that match any of the expressions provided.


By default API-Maker returns all properties excluding object and array properties.  The retrieve those types properties must be explicitly selected.


**__count**

When the __count parameter is present the count of the records selected is returned instead of the list of records.  This parameter only applies to 'GET' requests.  The result is a JSON object with a single attribute of 'count'.

An example of a request for the count of invoices for customer_id of five would be;

```
GET {endpoint}/invoices?customer_id=5&__count
```

The response would be;

```json
{'count': 7}
```

**__sort**

The __sort parameter allows specifying the order of records returned in the response.  This parameter only applies to 'GET' requests.

The sort order is specified with a comma delimited list of property names.  Optionally the sort direction can be appended to the property name using a ':' delimiter.  Valid sort directions are either 'asc' for ascending and 'desc' for descending order, if omitted 'asc' is default.

An example of a request that would return invoices order by most recent date and value would be;

```
GET {endpoint}/invoice?__sort=invoice_date:desc,value
```

Additionally sorting can be applied to properties found in object fields.  In this case the object and property should be delimited with a '.'.

For example the following requests returns invoices ordered by support representative;

```
GET {endpoint}/invoice?__sort=customer.support_rep_id
```

> Sorting on properties of array properties is not supported.

**__offset**

**__limit**

This property allows limiting the number of records returned.

**__case**

### Object and Array Properties

API-Maker supports returning objects that can have properties that are objects or an array of objects.  The availability of these types of properties depends the configuration in the API specfication.  An example of such properties can be found in the invoice schema object where the 'customer' property is a customer object and the 'line_items' is a array of line_item objects.



# Developing

As illustrated in the example there are three main parts to a APIU-Maker implementation;

First is the development of the application API specification.  Here the focus will be on mapping SQL tables and other resources into OpenAPI elements.

Then we will look at how connection configuration is managed using secrets.

Finally we will look at deployment and the resulting provisioned infrastructure.

## Building an API Definition

With API-Maker, development is focused on creating an application API specification using the OpenAPI Specification. API-Maker uses this specification to configure the REST API gateway and in the Lambda function that's provides the implementation of the services.

The API implementation with API-Maker API's is data source driven.  The database resources the application exposes drives the API design.  Database resources can be exposed in an API two ways;

1. **Table Integration**:
   When integrating with a table resource, API-Maker will generate services to support CRUD (Create, Read, Update, Delete) record management functions along with extended querying capabilities. Integration with tables is done by creating objects in the component schema section of the API specification.

2. **Custom SQL Integration**:
   While table integration can provide a majority of the basic functionality, there are times when building individual services cannot be avoided. To accommodate this, API-Maker also allows specifying individual services and associating custom SQL with those services. Integration with custom SQL is done by specifying path operations in the API specification.

By focusing on the OpenAPI Specification and leveraging API-Maker's capabilities, developers can efficiently build robust APIs that interact with relational databases, minimizing the need for custom service development.

```plantuml
@startuml
title OpenAPI Specification Structure

package "OpenAPI Specification" {
    class "OpenAPI Document" {
        - info
        - servers
        - paths
        - components
    }

    package "Components" {
        class "Schemas" {
            - schema_objects
        }
    }

    package "Paths" {
        class "Path Operations" {
            - GET
            - POST
            - PUT
            - DELETE
        }
    }
}

package "Relational Database" {
    class "Tables" {
        - table1
        - table2
        - ...
    }
    class "Custom SQL" {
        - custom_query1
        - custom_query2
        - ...
    }
}

"OpenAPI Document" --> "Schemas" : contains
"OpenAPI Document" --> "Path Operations" : contains
"Schemas" --> "Tables" : maps to
"Path Operations" --> "Custom SQL" : maps to

@enduml
```

## Table Integration

### API-Maker Integration Guidelines

API-Maker integrates component schema objects with database tables using the following guidelines:

- **Schema Object Naming**: The name of the schema object is used as both the operation path for the built services and the database table name.
- **Database Specification**: A database name must be specified to indicate where the table is located. An application API can span multiple databases.
- **Property Mapping**: Object properties are mapped to table columns. In addition to data types, properties can indicate primary keys and support concurrency management.
- **Defining Object and Array Properties**: Schema objects can have properties that are either objects or arrays or objects.  Some additional configuration is needed to enable this capability.

Since most schema object definitions involve a straightforward mapping between database table columns and schema object properties, API-Maker provides scripts to build an initial best-guess application API specification. This specification should be considered a starting point.

> **Note**: The gateway API has limitations on the number of operation paths (routes) allowed in a single API. As of this writing, the limit is 300 routes (extensions are available). Each schema object definition results in seven operation paths or routes, so the effective limit per API is approximately 40 schema objects.

### Generating OpenAPI Schemas from PostgreSQL Database Schemas

This section provides instructions on how to use the `postgres_to_openapi` script, which is included in the `api_maker` package, to generate OpenAPI schemas from PostgreSQL database schemas. The generated OpenAPI schemas will include the necessary components to represent the database tables, columns, primary keys, and foreign key relationships.

#### Prerequisites

- Python 3.x
- `psycopg2-binary` library for PostgreSQL connectivity
- `pyyaml` library for YAML processing

You can install the `api_maker` package and its dependencies using the following command:
```sh
pip install api_maker psycopg2-binary
```

#### Script Overview

The `postgres_to_openapi` script connects to a PostgreSQL database, queries the schema information, and generates an OpenAPI specification. The generated specification includes component schema objects that map to database tables and their columns. It also adds references to related schemas when foreign key relationships are detected.

#### Usage

1. **Run the Script**

   You can run the script from the command line using the entry point provided by the `api_make` package. The script requires arguments to connect to your PostgreSQL database and generate the OpenAPI schema. The output will be saved to the specified file path.

   ```sh
   python -m api_make.postgres_schema_to_openapi --host <db_host> --database <db_name> --user <db_user> --password <db_password> --schema <db_schema> --output <output_file>
   ```

   Replace `<db_host>`, `<db_name>`, `<db_user>`, `<db_password>`, `<db_schema>`, and `<output_file>` with your PostgreSQL database connection details and desired output file path.

#### Example

To generate an OpenAPI schema for a PostgreSQL database hosted at `localhost`, with the database name `mydatabase`, user `myuser`, password `mypassword`, and schema `public`, and save the output to `openapi_schema.yaml`, run:

```sh
postgres_to_openapi --host localhost --database mydatabase --user myuser --password mypassword --schema public --output openapi_schema.yaml
```

#### Generated OpenAPI Schema

The generated OpenAPI schema will include component schema objects representing the database tables and their columns. Primary keys will be marked with the `x-am-primary-key` attribute, and foreign key relationships will include references to related schemas with the `x-am-parent-property` attribute.

Here is an example of the generated schema for a table named `invoice`:

```yaml
components:
  schemas:
    # The name of the schema object is used for
    # both the API path (/invoice) and the table
    # name
    invoice:
      type: object
      x-am-database: chinook-auto-increment
      properties:
        invoice_id:
          type: integer
          # indicates the property is a primary key
          x-am-primary-key: auto
          description: Unique identifier for the invoice.
          example: 1001
        customer_id:
          type: integer
          description: Unique identifier for the customer.
          example: 1
        # This property is an customer object, it can be
        # included in query results.
        customer:
          $ref: '#/components/schemas/customer'
          x-am-parent-property: customer_id
          description: Customer associated with the invoice.
```

### Schema Object Naming

The name of the schema object by default is always used as the API path and by default the table name.  If needed name of the table can be changed using the 'x-am-table-name' attribute.

### Database Specification

At a minimum API-Maker requires that a database be specified using an 'x-am-database' attribute.  Only schema objects with this attribute will have services built.  This attribute is used to obtain the AWS secret that contains the engine type (Postgres, Oracle or MySQL) and the connection configuration.

### Property Mapping

### Database to OpenAPI Type Conversion

Property Type Mapping in API-Maker
API-Maker leverages the property types from the schema object to generate SQL and convert query result sets into JSON responses. The set of types in OpenAPI is simpler compared to the more complex database types.

For each table column exposed in the API, a corresponding property must be defined in the properties section of the schema object. This property definition maps the database column type to its corresponding OpenAPI schema type.

> It is also a good time and a good practice to include descriptions and examples for the properties.

Below is an illustration of how different PostgreSQL, Oracle, and MySQL types are converted to OpenAPI types:


| PostgreSQL Type                     | Oracle Type               | MySQL Type                    | OpenAPI Type            | Description |
|-------------------------------------|---------------------------|-------------------------------|-------------------------|-------------|
| `character varying`, `varchar`      | `VARCHAR2`, `VARCHAR`     | `VARCHAR`, `CHAR`, `TEXT`     | `string`                | Variable-length character string |
| `character`, `char`                 | `CHAR`                    | `CHAR`                        | `string`                | Fixed-length character string |
| `text`                              | `CLOB`                    | `TEXT`, `LONGTEXT`            | `string`                | Variable-length text |
| `integer`, `bigint`, `smallint`     | `NUMBER`, `INTEGER`       | `INT`, `BIGINT`, `SMALLINT`   | `integer`               | Integer number |
| `numeric`, `real`, `double precision` | `NUMBER`, `FLOAT`         | `DECIMAL`, `FLOAT`, `DOUBLE`  | `number`                | Floating-point number |
| `boolean`                           | `NUMBER` (1 or 0)         | `TINYINT(1)`                  | `boolean`               | Boolean value (true/false) |
| `date`                              | `DATE`                    | `DATE`                        | `string`, `format: date` | Date (ISO 8601 format) |
| `timestamp without time zone`       | `TIMESTAMP`               | `TIMESTAMP`                   | `string`, `format: date-time` | Timestamp without time zone (ISO 8601 format) |
| `timestamp with time zone`          | `TIMESTAMP WITH TIME ZONE`| `TIMESTAMP`                   | `string`, `format: date-time` | Timestamp with time zone (ISO 8601 format) |
| `uuid`                              | `RAW`                     | `CHAR(36)`                    | `string`, `format: uuid` | Universally unique identifier (UUID) |

#### Example Conversion

Given a PostgreSQL table with the following definition:

```sql
CREATE TABLE public.example (
    id serial PRIMARY KEY,
    name varchar(255) NOT NULL,
    description text,
    created_at timestamp with time zone DEFAULT current_timestamp
);
```

The corresponding OpenAPI schema object would be:

```yaml
components:
  schemas:
    example:
      type: object
      properties:
        id:
          type: integer
          x-am-primary-key: auto
          description: Unique identifier for the example.
          example: 1
        name:
          type: string
          maxLength: 255
          description: Name of the example.
          example: "Example Name"
        description:
          type: string
          description: Description of the example.
          example: "This is an example description."
        created_at:
          type: string
          format: date-time
          description: Timestamp when the example was created.
          example: "2021-10-05T14:48:00.000Z"
      required:
        - id
        - name
```

### Custom Attributes

In addition to standard OpenAPI properties, the script also adds custom attributes for specific functionalities:

- **`x-am-primary-key`**: Indicates that the property is a primary key. If the key is auto-generated, it is marked with the value `auto`.
- **`x-am-parent-property`**: Used to indicate foreign key relationships with other schema objects.


To accomplish this, attention must be given to several configuration aspects:

- **Database Configuration**: This involves addressing three primary configuration components:
  - The engine: This determines the SQL dialect to be employed.
  - The database: Indicates the database where the table resides.
  - Table name: Specifies the name of the table.

- **Primary Key**: Within the schema component, a property can be designated as the primary key. API-Maker offers support for three primary key generation strategies:
  - Manual: The responsibility for providing the key rests with the requesting application.
  - Auto: The database table autonomously generates the key.
  - Sequences: Employed in databases like Oracle, where sequence objects serve as the source of keys.

- **Concurrency Control**: Optionally, a property within the schema component can be identified as a concurrency control property this is utilized to prevent service requests from overriding updates made by earlier requests. When a schema object includes a concurrency control property, that property must be provided as a query parameter. If the value provided does not match the one in the database, the update request will fail.  API-Maker applies the following strategies depending on the property type and format:

| Property Type | Property Format | Column Type | Description |
|---------------|-----------------|-------------|-------------|
| string        | date-time       | timestamp   | Timestamp: API-Maker inserts the current time in the control field, and applications must provide that timestamp. |
| string        |                 |string       | Uses database UUID function in the control value. |
| interger      |                 | integer     |  When created the value is set to one.  Incremented by one on subsequent updates |



When building the application API specification
Within the API specification being built there are two main

### Handling Primary Keys

### Concurrency Management Columns

### Object and Array Properties

## Custom SQL Integration

# Reference

## API Definition

### Schema Component Objects

#### Schema Component Object Attributes

These attributes map the componnent object to a database table.

| Attribute | Description | Usage |
|-------|--------|---------|
| x-am-database | The name of the database where the table is located.   | Required, value is used to access database configuration from the runtime secrets map. |
| x-am-engine | The type of database being accessed. Determines SQL dilect to use.  | Required, must be one of 'postgres', 'oracle' or 'mysql' |
| x-am-table | The table name to perform the operations on. | Optional, defaults to schema component object name if not provided.  Must be a valid table name |
| x-am-concurency-control | The name of the property

#### Schema Component Object Property Attributes

| Attribute             | Description                                                                                            | Usage                                                                                   |
|-----------------------|--------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------|
| x-am-column-name      | Specifies the database column name if it differs from the property name.                                | Optional                                                                                |
| x-am-primary-key      | Indicates that this property serves as the primary key for the object and defines how the key is obtained. | Required; must be one of the following: manual, auto, or sequence.                       |
| x-am-sequence-name    | Specifies the database sequence to be used for generating primary keys.                                     | Required only when the primary key type is "sequence".                                    |
#### Schema Component Object Associations

When defining the api using schema objects the Open API specication allows properties that can be either objects or array of objects in addition to the other basic types.  With additional custom attributes API-Maker can populate these properties saving the client application the need to make multiple requests to construct objects with these properties.

**Including an Object Property**

Consider the following api spec;

```yaml
components:
  schemas:
    customer:
      type: object
      x-am-engine: postgres
      x-am-database: chinook
      properties:
        customer_id:
          type: integer
          x-am-primary-key: auto
        company:
          type: string
          maxLength: 80
    invoice:
      type: object
      x-am-engine: postgres
      x-am-database: chinook
      properties:
        invoice_id:
          type: integer
          x-am-primary-key: auto
        customer_id:
          type: integer
        customer:
          $ref: '#/components/schemas/customer'
          x-am-parent-property: customer_id
```

In this example, the `customer` property of the `invoice` schema is an object type after reference resolution. By setting the `x-am-parent-property` attribute to a sibling property, API-Maker will use the value of that property to resolve the object value. Specifically, in this example, the `customer_id` value of the invoice will be used to select the corresponding customer.

> Internally API-Maker uses inner joins to select these objects using a single database operation.

**Including an Array Propety**


Consider the following api spec:
```
    invoice:
      type: object
      x-am-engine: postgres
      x-am-database: chinook
      properties:
        invoice_id:
          type: integer
          x-am-primary-key: auto
        line_items:
          type: array
          items:
            $ref: "#/components/schemas/invoice_line"
            x-am-child-property: invoice_id
    invoice_line:
      type: object
      x-am-engine: postgres
      x-am-database: chinook
      properties:
        invoice_line_id:
          type: integer
          x-am-primary-key: auto
        invoice_id:
          type: integer
        track_id:
          type: integer
```

In this example, the `line_items` property of the `invoice` schema is an array of `invoice_lines` type after reference resolution.  By setting the `x-am-child-property` attribute to a property in the `invoice_line` schema, API-Maker will use the primary key value of the invoice to select on that property.  Specifically, in this example, the `invoice_id` values from the selected `invoice`s will be used to filter on the `invoice_id` property of the associated `invoice_line` items.


| Attribute             | Description                                          | Usage             |
|-----------------------|------------------------------------------------------|-------------------|
| x-am-parent-property  | The name of the 'primary' property that identifies the selection key.  | Optional, defaults to `parent` primary key.  Normally needed for 1:1 associations. |
| x-am-child-property   | The name of the property in the `secondary` object used as the selection key | Optional, defaults to primary key of  defaults to the child if not specified |

##### One-to-One Associations

When defining an association property for a one-to-one (1:1) association, the associated schema component can be included as a property of the object being returned.

In the Chinook database, an example of this type of association can be found in the `invoice` table, where the `customer_id` serves as a foreign key referencing the customer record.

In the schema component object model, this relationship can be specified, allowing the resultant invoice objects to have a `customer` property containing a customer object.


Here's an example of how the `customer` property would be specified in the `invoice` schema component object;


    invoice:
      type: object
      x-am-engine: postgres
      x-am-database: chinook
      properties:
        invoice_id:
          type: integer
          x-am-primary-key: auto
        customer_id:
          type: integer
        customer:
          x-am-type: relation
          x-am-schema-object: customer
          x-am-parent-property: customer_id

In this example the `customer` property type is specified as being a relation to the schema component object `customer'.  When fetching data API-Make will then use

With API-Maker

| Attribute | | Description |
|-----------|-|-------------|
| x-am-schema | Required | The name of the schema component object to use as the source of the relation. |
| x-am-cardinality | Optional | Can be either single or multiple, defaults to single |
| x-am-parent-property | Required | The name of the sibling property to use as the selection key in the relation |
| x-am-child-property | Optional |



# Attic

With API-Maker, developing RESTful API's is first focused on defining components and services in the form of an Open API specification.  Objects in this specification then can be enhanced by either;

* Schema component objects can be enhanced with database table configuration, allowing API-Maker to provide RESTful CRUD services on table records.
* Path operations can be enhanced with database connection and SQL configuration to provide service based on custom SQL.

For data read operations using HTTP GET, API-Maker provides robust data selection capability reducing the need for building custom services. To achieve this API-Maker provides the following features;

* Comparison oprands can be applied to a property when selecting data.  These operand such as; less than, between, and in, can be applied to any property for record selection.
* Associations between component objects can be defined allowing retrieval of complex objects containing associated data in a single request.
* Requesting applications can restrict the properties being returned.
* Requesting applications can select the case convention (snake or lower camel) of the ressponse results.

API-Maker is not a traditional object relational model (ORM) library but rather operates by generating and executing SQL queries to perform its services.  Generating operations this way keeps marshaling and unmarshaling objects to a minimum, ensuring efficient data retrieval and manipulation.

Deploying APIs with API-Maker involves the following steps:

1. Store the annotated API specification on Amazon S3.
2. Configure and deploy the Lambda archive.
3. Retrieve an enhanced API specification from the Lambda function.
4. Deploy the AWS Gateway API using the enhanced specification.


# Usage

When utilizing API-Maker to construct APIs, the primary focus of development lies in defining component schema objects and path operations.

Annotations on component schema objects enable seamless operations on database tables. At a minimum, these annotations configure the database and table name. However, additional annotations are available to enhance functionality:

- Renaming exposed API properties to table column names.
- Implementing concurrency control on record updates using either timestamps. UUIDs or serial numbers.
- Supporting auto-generated primary keys.
- Establishing associations with other component schema objects to enable parent-child retrievals.

Annotations to the OpenAPI specification document provides the means of mapping from API elements to database resources.

This is done via two primary methods.
::
* Component Schema Objects to Database Tables - These objects can be mapped to database tables.  When this mapping is available api-maker will build supporting CRUD services.

* Path Operations to Custom SQL - This method allows attaching custom SQL to a specific operation.


## Using API Services

When processing requests, API-Maker categorizes parameters into three categories: query, store, and metadata.

**Qeury Parameters**

These paramters are always used in selecting the set of records that the operation applies to.  Generally these parameters are passed as query string elements in the request, however with some of services provided these can appear as path elements.

When selecting records using request query string elements relational operands can be applied by prefixing the operand to the value.  For example using the Chinook example API invoices with a total price of less then five dollars would be;

```
GET https://bobsrecords.com/invoice?total=lt::5
```

**Store Parameters**

Store parameters are always passed in the request body using json format and represents data to be stored in the request.  These parameters only apply to create and update operations.

**Metadata Parameters**

Metadata parameters allow sending of additional instructions in the request.  These paraemters are always passed in the request query string and are always prefixed with an underscore '_'.


### Schema Object Services

When schema objects are enhanced with database configuration API-Maker builds the following services.


| Operation | URI                     | Method | Description |
|-----------|-------------------------|--------|-------------------------------|
| read      | <endpoint>              | GET    | Query for a set of data |
| read      | <endpoint>/{id}         | GET    | Selects a single record by ID.              |
| create    | <endpoint>              | POST   | Insert record(s).|
| update    | <endpoint>              | PUT    | Update a set of records    |
| update    | <endpoint>/{id}         | PUT    | Update a record by id    |
| update    | <endpoint>/{id}/{stamp} | PUT    | Update a record with concurrency management by id    |
|delete     | <object_endpoint>       | DELETE | Delete a set of records |
| delete    | <endpoint>/{id}         | DELETE | Update a record by id    |

Here, \<object_endpoint> represents the API endpoint followed by the schema object name. For example, 'https://bobsrecords.com/albums'.

The service to select a record by its ID is self-explanatory.

> Note: {id} always represents the primary key property of the schema object.

#### Reading Records

For more flexibility in selecting sets of data, query parameters can be passed via the request query string. Additionally, requests can include relational operands to refine selection criteria.

Any property in the schema object can be used as a parameter name in the request query string. The value component can be either a simple value or a relational value.

**Simple Parameters**

For simple parameters, the implied relation is equality. Using the Chinook database, customers in Florida can be selected using the following URL:

```
https://bobsrecords.com/customer?state=FL
```

Multiple request parameters can be submitted. For example, to further restrict the set to customers in Florida with a specific support representative:

```
https://bobsrecords/customer?state=FL&support_rep_id=4
```

When the component schema object has a one-to-one association with another component schema object, requests can also search on properties of the associated object.

For example, in the Chinook invoice schema object, where the customer property is a one-to-one associated object, invoices for customers in Florida can be selected with the following URL:

```
https://bobsrecords/invoice?customer.state=FL
```

> This feature is not applicable to one-to-many associations.

**Relational Parameters**

Relational parameters provide the means of applying relational operands to query string parameters.

For these parameters, the query string value has the relational operand followed by '::' prepended to it. The supported operands include: 'lt', 'le', 'eq', 'ne', 'ge', 'gt', 'in', 'between', 'not-in', 'not-between'.

For example, to select all employees hired after a certain date:

```
https://bobsrecords/employee?hire_date=gt::2024-01-01
```

When using range operands that require multiple values ('in', 'between', 'not-in', and 'not-between'), those values are passed as a comma-delimited list.

For example, to request employees hired in 2023;

```
https://bobsrecords.com/employee?hire_date=between::2024-01-01,2024-12-31
```

### Inserting Data

### Updating Data

Updating data is done via PUT method requests.  If in the schema component object a property has been ehanced with a version type attribute
then API-Maker restricts updates to single records.  Without a version property then normal record selection occurs allowing bulk updates
of records.


## Query Parameters

| Methon | Operation | Query Parameters | Store Parameters | Metadata Parameters |
|--------|-----------|------------------|------------------|---------------------|
| GET    | read      |
| POST   | create    | Not accepted     | Required         |
| PUT    | update    |
| DELETE | delete    |

Request parameters for services provided by API-Maker

### Selecting Data - GET

The `_properties` metadata parameter enables the service requester to specify the desired properties in the response. This parameter is optional, and if not provided, the service result will include objects with all properties including relational properties selected by default.

When utilized, the `_properties` parameter should be a string comprising a delimited list of regular expressions. If a property matches any of these expressions, it will be incorporated into the response. Moreover, if the schema component object contains relational properties, the composition of those properties can also be selected. In such cases, the relation name is prepended with a ':' delimiter followed by a regular expression for selecting properties of the related object.

Consider the following examples with the Chinnook invoice schema object;

| _properties | Description|
|-------------|------------|
| .*          | Returns all invoice properties |
| .* line_items | Returns all invoice properties and the line_items associated with the invoice |
| invoice_id total | Returns just the invoice id and total |


### Metadata Parameters

| Name | Description |
| _properties | Optional, allows selecting a subset of properties returned by the request.
A space delimited list of regular expressions |


## Open API Specification Extensions

# Services

For annotated compoenent schema objects API-Make provides RESTful services supporting the full CRUD based record lifecycle.

When interacting with these services there are three catagories of data being supplied in the request.  These catagories are;

**Query Parameters** - These parameters are generally passed in the request query string or path parameters.  With query string values relational expressions can be applied to filter sets of records.  These parameters can be applied to GET, PUT, and DELETE methods.

Fundanmental relational expressions are supported when selecting records using a query string.  When passing a query string parameter the value can be prefixed with an relational operator separated by a ':'.  For example a parameter of 'laditude=lt:30' would select records those records with a laditude of less than 30. The supported operations are lt, le, eq, ne, ge, gt, in, between, not-in, not-between.

**Store Parameters** - These parameters are always passed in the request body in JSON format and represent data to be stored.  These parameters are only accepted only by POST and PUT methods.

**Metadata Parameters** - These parameters are alway passed via the request query string and are used to supply directives for processing the request.  The names of these parameters are always prefixed with an '_'.

| Name | Methods | Description |
|------|---------|-------------|
| _count | GET   | Returns the count of records selected. |
| _properties | GET | Allows tailoring the output results.  |
| _case | GET | Return the results properties in camel case |



| Operation | Method | Description |
|-----------|--------|-------------|
| Query     | GET    | Query and Metadata parameters are passed via either path parmeters or the query string. |
| Create    | POST   | Values to be stored are passed in the request body in JSON format. |
| Update    | PUT    | Values to be stored are passed in the request body in JSON format. Query and Metadata parameters for record selection are passed via either path parmeters or the query string. |
| Delete   | DELETE | Query and Metadata parameters are passed via either path parmeters or the query string. |

## GET - Record Selection

## POST - Record Creation

## PUT - Record Modification

## DELETE - Record Deletion
