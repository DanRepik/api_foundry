# API-Foundry

The `api_foundry` project is a powerful tool designed to automate the deployment of REST APIs on AWS using Lambda services to access and interact with relational databases (RDBMS). This project leverages the OpenAPI specification to define and manage the APIs.

### Key Features:

- **AWS REST API Deployment**: `api_foundry` simplifies the deployment of RESTful APIs on AWS by integrating with AWS Lambda, allowing seamless interaction with various relational databases.

- **OpenAPI Specification**: The project uses the OpenAPI standard for defining API endpoints, request/response structures, and data schemas. This ensures that the APIs are well-documented, standardized, and easy to maintain.

- **Automatic Record Management**: When OpenAPI schema objects are linked to database tables, `api_foundry` automatically generates record management services. This includes the creation of standard CRUD (Create, Read, Update, Delete) operations, providing a robust and scalable solution for managing database records through the API.

- **Custom SQL Integration**: `api_foundry` allows developers to define custom SQL queries and associate them with specific OpenAPI path operations. This feature provides flexibility to perform complex queries and operations beyond standard CRUD functionalities, tailored to specific application requirements.

- **Role Based Permissions**: Within OpenAPI schema objects and path operations `api_foundry` permissions can be defined based on roles restricting whether a user may delete records and what properties a may be read or written.

### Summary:

The `api_foundry` project streamlines the process of deploying APIs on AWS that interact with relational databases. By utilizing the OpenAPI specification, it not only ensures consistency and clarity in API design but also automates the creation of database-driven services and allows for custom SQL operations. This makes `api_foundry` an invaluable tool for developers looking to quickly deploy and manage data-centric APIs on the AWS platform.


## Guide

This guide provides a overview of key API-Foundry features, including:

* **Building an API** - A quick introduction to implementing APIs with API-Foundry, featuring a concise example of deploying an API.
* **Exploring the Deployment** - An overview of the infrastructure deployed to support the API.
* **Exploring the Services** - A deep dive into the API services built, including basic operations and enhanced record selection capabilities.
* **Using Metadata Parameters** - How to use metadata parameters in requests to customize the results returned by the services.
* **Managing Concurrency** - An explanation of how API-Foundry handles concurrency among application clients.
* **Object and List Properties** - Demonstrations of how API-Foundry can return objects with nested objects or lists as properties, and how to configure these properties.
* **Authorization** - API foundry provides role based security allowing restrictions down to the property level.

The examples in this guide use data from the Chinook database. The examples presented here are a subset of a complete working example available in the examples directory.

## Build an API in Five Minutes

There are three steps to building an API-Foundry api;

1. Define the resources to be exposed in an OpenAPI document.
1. Create a secret containing the connection parameters to access the database.
1. Deploy the API-Foundry as part of a IAC resource to AWS.

This section provides a quick overview of building an minimal API using API-Foundry.  The examples presented here a accessing data in a Chinook database.  What is presented is an subset of a complete working example that can be found in the examples.

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
      x-af-database: chinook
      properties:
        album_id:
          type: integer
          x-af-primary-key: auto
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
      x-af-database: chinook
      properties:
        artist_id:
          type: integer
          x-af-primary-key: auto
        name:
          type: string
          maxLength: 120
      required:
        - artist_id
```

The above is standard OpenAPI specification with additional custom attributes.  API-Foundry always prefixes custom attributes it uses with 'x-af-'.

In this example the following API-Foundry attributes have been added;

* x-af-database - This indicates what database should be accessed for the built services.
* x-af-primary-key - This attribute can be attached to one of the object properties to indicate that property is the primary key for the component object.  The value of this property is the key generation strategy to use for record creation.

In this example table names, albums and artists, is same as the component object names and in turn in the API path operations.  API-Foundry provides additional custom attributes that allow explicit naming of the table.

> TODO: Link to custom attribute documentation

**Define the Database Access Secret**

For the second step you will need to supply API-Foundry with connection parameters for access to databases.

With API-Foundry the connection parameters needed to access the backend database is obtained using a AWS secretsmanager secret.  This secret should be a JSON string defining the connection parameters needed. The following script creates a secret for accessing the Chinook database running on Postgres.

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
from api_foundry import APIFoundry

api_foundry = APIFoundry(
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

## What API-Foundry Deploys

Once the API-Foundry deployment is complete

```plantuml
@startuml
title Deployment Diagram for API-Foundry api with External Database

actor Client as client

node "AWS" {
    node "API-Foundry" {
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

## Using API-Foundry Services

API-Foundry provides a robust API that allows clients flexibility in selecting and modifying records. This section explores the API services offered by API-Foundry.

There are four sections that cover the available services:
1. **Basic Operations**: CRUD operations on single records.
2. **Enhanced Record Selection**: Advanced querying capabilities.
3. **Metadata Parameters**: Tailoring the content of responses.

Most examples will use an abbreviated API specification, but some will reference the complete Chinook API specification.

### Basic Operations

API-Foundry supports basic CRUD services using RESTful HTTP methods. Data passed via requests and responses is in JSON format.

Successful operations return the status via response headers. The response body contains an array of the selected objects. For POST, PUT, and DELETE operations, the body contains the modified or deleted records.

The operation paths are as follows:

```
# for POST
/{entity}
# for GET, PUT and DELETE
/{entity}/{id}
```

Where:
- **entity**: The schema component object name from the API specification (e.g., album, artist).
- **id**: The primary key of the selected record.

### Enhanced Record Selection

In addition to basic CRUD operations, API-Foundry offers enhanced record selection using query strings. This feature allows selection of multiple records and does not apply to create operations. The path for these services is:

```
# for GET, PUT and DELETE
/{entity}
```

Records are selected using query string parameters, where the name can be any property defined in the component schema object.

Examples for the Chinook database:

```
# get an artist, same as /artist/3
GET /artist?artist_id=3

# get an album, same as /album/5
GET /album/album_id=5

# get the albums by an artist
GET /album?artist_id=3

# get the invoices where the billing country is USA and the total was $3.96
GET /invoice?total=3.96&billing_country=USA
```

**Relational Expressions**

Relational operands can be prefixed to the value of a parameter. These operands allow selecting records based on criteria rather than exact matches. The available operands are:

- `lt` (less than)
- `le` (less than or equal to)
- `eq` (equal to)
- `ne` (not equal to)
- `ge` (greater than or equal to)
- `gt` (greater than)
- `in` (in a list of values)
- `between` (between a range of values)
- `not-between` (not between a range of values)

Examples:

```
# read albums with an album_id of less than 100
GET /album?album_id=lt::100

# read invoices that total either $3.96 or $5.94
GET /invoice?total=in::5.94,3.96

# read invoices that are between $3.00 and $6.00
GET /invoice?total=between::3,6
```

### Using Metadata Parameters

Requests can include metadata parameters in query strings to provide additional instructions. Metadata parameters are prefixed with double underscores `__`.

**__properties**

The `__properties` metadata parameter restricts the properties of objects returned by API-Foundry. By default, API-Foundry returns all authorized properties of an object, excluding object and array properties. These properties must be explicitly selected using this parameter.

The format of the parameter value is a space-delimited list of regular expressions. Only authorized properties matching any of the expressions are included in the result set.

When this parameter is omitted, API-Foundry uses the expression `.*` to select all non-object or non-array properties. When included, API-Foundry does not include any properties by default, and all properties must be explicitly selected.

For example, to select specific properties of the Chinook invoice, you could use the following request:

```yaml
GET {endpoint}/invoice?__properties=invoice_id%20billing_.*%20price
```

With this expression, the `invoice_id`, `price`, and all billing address properties will be included in the result set objects.

When selecting properties from object or array objects, the property selection regular expression must be prefixed with the property name, delimited by a colon (`:`). An example of selecting the `customer` property in an invoice would be:

```yaml
GET {endpoint}/invoice?__properties=.*%20customer:.*
```

In this example, there are two regular expressions: `.*` and `customer:.*`. The first expression, `.*`, selects all the invoice's non-object or array fields. The second expression selects all the properties of the `customer` object.

To select both the `customer` and `invoice_line_items` properties in an invoice, you would use:

```yaml
GET {endpoint}/invoice?__properties=.*%20customer:.*%20invoice_line_items:.*
```

> Nesting of property selectors for objects and arrays is not supported. For example, in the Chinook invoice, invoices have `invoice_line_items`, and `invoice_line_items` then have a `track`. The expression `invoice_line_items:track:.*` logically sets the `track` property on the `invoice_line_items` in each invoice. This is not supported at this time.

**__count**

When present, returns the count of the records selected instead of the list of records. This parameter applies only to `GET` requests. The result is a JSON object with a single attribute `count`.

Example:

```
GET {endpoint}/invoices?customer_id=5&__count
```

Response:

```json
{"count": 7}
```

**__sort**

Specifies the order of records returned in the response. This parameter applies only to `GET` requests. The sort order is specified with a comma-delimited list of property names. Optionally, append `:asc` or `:desc` to the property name to specify ascending or descending order, respectively. The default is ascending.

Example:

```
GET {endpoint}/invoice?__sort=invoice_date:desc,total
```

Sorting can also be applied to properties in object fields using a dot `.` delimiter.

Example:

```
GET {endpoint}/invoice?__sort=customer.support_rep_id
```

> Sorting on properties of array properties is not supported.

**__offset**

Skips records before beginning the response result set. This parameter applies only to `GET` requests. The value must be a positive integer. If the offset is greater than the total records selected, an empty result set is returned.

Example:

```
GET {endpoint}/invoice?__sort=invoice_id&__offset=50
```

**__limit**

Limits the number of records returned. This parameter applies only to `GET` requests. The value must be a positive integer. The response result set maximum length will be the specified limit.

Example:

```
GET {endpoint}/invoice?__sort=invoice_id&__limit=20
```

# Developing

As illustrated in the example there are three main components to implementing an API using API-Foundry;

* **Build the API Specification** First is the development of the API specification for the application.  The focus will be on mapping SQL tables along with any custom SQL into the OpenAPI specification.

* **Configuration** Then we will look at how API-Foundry accesses databases the application references, and how to setup the configuration needed for making connections.

* **Deployment** Finally we will look at the deployment and how to integrate the resulting provisioned infrastructure the cloud environment.

## Building an API Definition

With API-Foundry, development is focused on creating an application API specification using the OpenAPI Specification. API-Foundry uses this specification to configure the REST API gateway and in the Lambda function that's provides the implementation of the services.

The API implementation with API-Foundry is driven by data sources, with the database resources of the application guiding the API design. Database resources can be exposed in an API in two primary ways:

1. **Table Integration**:
   When integrating with a table resource, API-Foundry generates services to support CRUD (Create, Read, Update, Delete) operations, along with advanced querying capabilities. This integration is accomplished by defining objects in the component schema section of the API specification.

2. **Custom SQL Integration**:
   While table integration covers most record management needs, relational databases (RDBMs) offer additional functionality that may require custom SQL. API-Foundry enables the specification of custom SQL for individual services by defining path operations in the application's OpenAPI specification.

By focusing on the OpenAPI Specification and leveraging API-Foundry's features, developers can efficiently build robust APIs that interact with relational databases, reducing the need for extensive custom service development.


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

### Table Integration

#### API-Foundry Integration Guidelines

API-Foundry integrates component schema objects with database tables using the following guidelines:

- **Schema Object Naming**: The name of the schema object is used as both the operation path for the built services and the database table name.
- **Database Specification**: A database name must be specified to indicate where the table is located. An application API can span multiple databases.
- **Property Mapping**: Object properties are mapped to table columns. In addition to data types, properties can indicate primary keys and support concurrency management.
- **Defining Object and Array Properties**: Schema objects can have properties that are either objects or arrays or objects.  Some additional configuration is needed to enable this capability.

Since most schema object definitions involve a straightforward mapping between database table columns and schema object properties,

> API-Foundry provides [tooling](#generating-openapi -schemas) to build an initial starting point API specification. This specification should be considered a starting point.

> **Note**: The gateway API has limitations on the number of operation paths (routes) allowed in a single API. As of this writing, the limit is 300 routes (extensions are available). Each schema object definition results in seven operation paths or routes, so the effective limit per API is approximately 40 schema objects.

#### Schema Object Naming

The name of the schema object by default is always used as the API path and by default the table name.  If needed name of the table can be changed using the 'x-af-table-name' attribute.

#### Database Specification

At a minimum API-Foundry requires that a database be specified using an 'x-af-database' attribute.  Only schema objects with this attribute will have services built.  This attribute is used to obtain the AWS secret that contains the engine type (Postgres, Oracle or MySQL) and the connection configuration.

#### Property Mapping

API-Foundry leverages the property types from the schema object to generate SQL and convert query result sets into JSON responses. The set of types in OpenAPI is simpler compared to the larger set of database types.

For each table column exposed in the API, a corresponding property must be defined in the properties section of the schema object. These property definitions map database column types to their corresponding OpenAPI schema type.

> It is also a good time and a good practice to include descriptions and examples for the properties.

Below is an illustration of how different PostgreSQL, Oracle, and MySQL types are mapped into OpenAPI types:


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



##### Example Conversion

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
          x-af-primary-key: auto
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





#### Object and Array Properties

API-Foundry supports returning objects that can have properties as objects or arrays of objects. From a relational database perspective, an object property represents a one-to-one relationship, while an array of objects represents a one-to-many relationship.

Additional configuration in the API specification document can incorporate these types of properties into service result sets. The schema object types for these properties must refer to the same database.

By default, these properties are not included in the result set. They must be explicitly selected in the request using the `__properties` metadata parameter. This allows for the specification of circular properties in the application API. For example, in the Chinook API, an invoice has a customer object property, and a customer, in turn, has an array of invoices property. In this case, services returning invoices can include the customer as a property, but that object will not include the invoices associated with the customer. Similarly, when selecting customers, the invoices associated with the customer can be included, but those invoices cannot contain a customer property.

#### Object Properties

In OpenAPI specifications, object properties typically use a `$ref` attribute to reference the component schema object for the property. When the referenced schema object is part of the same database, API-Foundry can automatically populate that property with additional configuration. Specifically, the keys that define the relationship must be identified. The following attributes allow configuring object properties:

* **x-af-parent-property**: Identifies the schema object property containing the key used to select the referenced property value. This attribute is required for object properties.

* **x-af-child-property**: Identifies the property in the referenced schema object to select on. This attribute is optional and defaults to the primary key if omitted. Normally, the parent property key references the primary key, but this attribute can be used if that is not the case.

Here's an example of the customer field from the Chinook invoice schema object:

```yaml
customer_id:
  type: integer
customer:
  $ref: '#/components/schemas/customer'
  x-af-parent-property: customer_id
  description: Customer associated with the invoice.
```

Note how the `x-af-parent-property` identifies the `customer_id` property to use as the key value for selecting the customer.  Since a the `x-af-child-property` was omitted API Foundry will match the `customer_id` to the primary key of the `customer` schema object.

#### Array of Object Properties

Array properties allow the inclusion of lists of related records representing one-to-many relations within the database. Most of the setup for these properties uses standard OpenAPI conventions. Like object properties, these properties must reference a schema object accessing the same database.

The same additional attributes for defining the relationship as object properties are used:

* **x-af-parent-property**: Identifies the schema object property containing the key used to select the referenced property value. This attribute is optional and defaults to the primary key property.

* **x-af-child-property**: Required attribute that identifies the property in the referenced schema object to select on.

The following illustrates the specification of an `invoice_line_items` property in the invoice schema object. In this example, the `invoice_line` schema object has a property `invoice_id` (x-af-child-property). API-Foundry will use the invoice primary key property `invoice_id` to select `invoice_line` records with the matching `invoice_id`.

```yaml
invoice_line_items:
  type: array
  items:
    $ref: '#/components/schemas/invoice_line'
    x-af-child-property: invoice_id
  description: List of invoice_line items associated with this invoice.
```

#### Handling Primary Keys

Within the schema component, a property can be designated as the primary key.   API-Foundry offers support for multiple primary key generation strategies.


> Schema objects with multiple primary keys is not currently supported.

A property can be specified as a primary key by adding the 'x-af-primary-key' attribute to the property.  In the value the key generation strategy must be definied it can be any of;

| Value    | Description |
|----------|-------------|
| manual   | The responsibility for providing the key rests with the requesting application. |
| uuid     | The database uuid generator is usted to  generate the key. |
|auto      | The database table automatically generates the key.
| sequence | Employed in databases like Oracle, where a sequence object serve as the source of keys. |

Here is an example of the primary key for the invoice schema object;

```
    invoice:
      type: object
      properties:
        invoice_id:
          type: integer
          x-af-primary-key: auto
          description: Unique identifier for the invoice.
          example: 1
```

If the key generation strategy is 'sequence' the the 'x-af-sequence-name' attribute must also be defined.

#### Concurrency Management

Optionally, a property within the schema component can be identified as a concurrency control property.  This property is utilized to prevent clients from overriding mutations to objects made by other clients.

When a schema object includes a concurrency control property the following occurs;

* API-Foundry manages the value of the property, clients may not change the value.
* For each mutation of the object the value of the property is changed.
* Clients making mutations to objects must provide both the key and the control property.  If the control property does not match the request will fail.

A concurrency control property is set by adding the 'x-af-concurrency-control' attribute to the schema object definition.  The value must be the name of either a string or integer property of the schema object. API-Foundry applies the following strategies depending on the property type and format specified for the control property:

| Property Type | Property Format | Column Type | Description |
|---------------|-----------------|-------------|-------------|
| string        | date-time       | timestamp   | Timestamp: API-Foundry inserts the current time in the control field, and applications must provide that timestamp. |
| string        |                 |string       | Uses database UUID function in the control value. |
| interger      |                 | integer     |  When created the value is set to one.  Incremented by one on subsequent updates |

Here is an example of using a timestamp as a control object;

```yaml
    invoice:
      type: object
      x-af-database: chinook
      x-af-concurrency-control: last_updated
      properties:
        invoice_id:
          type: integer
          x-af-primary-key: auto
          description: Unique identifier for the invoice.
          example: 1
        last_updated:
          type: string
          format: date-time
```

### Custom SQL Integration

Integrating custom SQL into your application is achieved by defining path operations within the application's OpenAPI specification. When setting up a path operation to invoke custom SQL, you need to define the following:

- **Inputs**: Request parameters that are used to parameterize the custom SQL.
- **SQL to Execute**: The actual SQL query to be executed.
- **Output Response Structure**: The structure of the returned results.

#### Defining Path Operations in the OpenAPI Specification

In the OpenAPI specification, path operations correspond to specific HTTP methods (e.g., `GET`, `POST`, `PUT`, `DELETE`) that define how your API interacts with resources. Each path operation is associated with a specific path (URL) and method, and it specifies the behavior of the API when that path and method are invoked.

For example:
- **GET** operations typically retrieve data.
- **POST** operations create new resources.
- **PUT** operations update existing resources.
- **DELETE** operations remove resources.

In the context of custom SQL integration, you define the path operation with a method (e.g., `GET`, `POST`) in the OpenAPI specification, along with the necessary input parameters, the SQL query to execute, and the expected response format.

#### Deployment and Path Operation Precedence

During deployment, API-Foundry builds an OpenAPI specification document that configures the AWS API Gateway. This document combines path operations explicitly defined in the API specification with those needed to support the record management functions associated with any component schema objects.

When combining these two sets of path operations, API-Foundry gives precedence to path operations with custom SQL over the default component schema record management functions. This feature allows you to explicitly override API-Foundry's default behavior. However, it can also become a potential 'gotcha' if not managed carefully, as custom path operations may inadvertently override essential default operations.

#### Request Inputs

Request inputs can be declared either in the path operation's parameters or in the request body sections of the OpenAPI definition. These inputs are used to parameterize the custom SQL.

- **Path Operation Parameters**: Parameters are generally used for record selection. API-Foundry often uses these parameters to filter or identify specific records within the database that match the criteria specified in the custom SQL.

- **Request Body**: The request body is typically used to provide data for storage or updates, and it only applies to `PUT` and `POST` operations. These operations involve creating new records or updating existing ones, and the data to be stored or updated is passed through the request body.

In API-Foundry, the names of the inputs defined in the path operation's parameters or request body are used to match placeholders in the custom SQL query. Placeholders in the SQL query are denoted by a colon (`:`) followed by the input name. For example, if you define an input named `user_id`, you would reference this in your custom SQL as `:user_id`. This ensures that the appropriate values are substituted into the SQL query when the API is called.

While API-Foundry is designed to obtain parameters from either the path operation parameters or the request body, the convention is to use path operation parameters for selecting records and the request body for storing or updating data. This separation ensures that the custom SQL receives the appropriate inputs depending on the type of operation being performed.

#### SQL to Execute

In your path operation, you must define the following attributes:

* **x-af-database**: Identifies the database on which the custom SQL will be executed, functioning similarly to its use in component schema objects.
* **x-af-sql**: Contains the SQL query to be executed for the request.

For the integration to function correctly, the definition must map input parameters to the custom SQL's placeholders and ensure the SQL response aligns with the defined response structure.

Placeholders can be included in the custom SQL query. These placeholders begin with a colon (:) followed by the name of the input parameter. This input parameter must be defined either in the path operation's parameters or in the request body, depending on the request method.

#### Response Outputs

Upon successful execution of the custom SQL, API-Foundry expects a cursor containing the SQL results. It will then attempt to map the cursor's contents into an array of objects to be returned as the path operation result. This mapping must be defined in the responses section of the path operation.

The path operation must specify a response with a status code in the 200's, using application/json content type, and a schema that defines an array of objects. The properties defined in the array are used by API-Foundry to convert the custom SQL cursor into the API response.

When mapping from the SQL result to the API response, there are two strategies to handle mismatches between property names:

1. **Preferred Strategy**: Rename the columns returned in the SQL using the AS keyword. For example:
```sql
SELECT
    a.album_id as album_id,
    a.title AS album_title,
    COUNT(il.invoice_line_id) AS total_sold
FROM
    ...
```

2. **Alternative Strategy**: If the custom SQL doesn't allow for column renaming, use the x-af-column-name attribute in the response properties. For example:
```sql
SELECT
    a.album_id,
    a.title,
    COUNT(il.invoice_line_id)
FROM
    ...
```

Then, in the property definitions for the response contain 'x-af-column-name' attributes to access the SQL columns:

```yaml
responses:
  '200':
    description: A list of top-selling albums
    content:
      application/json:
        schema:
          type: array
          items:
            type: object
            properties:
              album_id:
                type: integer
                description: The ID of the album
                x-af-column-name: a.album_id
              album_title:
                type: string
                description: The title of the album
                x-af-column-name: a.title
              total_sold:
                type: integer
                description: The number of albums sold
                x-af-column-name: COUNT(il.invoice_line_id)
```

#### Example Path Operation

Here's a complete example of a path operation that invokes custom SQL;

```yaml
paths:
  /top_selling_albums:
    get:
      summary: Get top-selling albums
      description: Returns the top selling albums within a specified datetime range.
      # define the inputs
      parameters:
        - in: query
          name: start
          schema:
            type: string
            format: date-time
          required: true
          description: Start datetime for the sales period.
        - in: query
          name: end
          schema:
            type: string
            format: date-time
          required: true
          description: End datetime for the sales period.
        - in: query
          name: limit
          schema:
            type: integer
          default: 10
          description: The number of albums to return.
      # define the SQL to be processed
      x-af-database: chinook
      x-af-sql: >
        SELECT
            a.album_id AS album_id,
            a.title AS album_title,
            COUNT(il.invoice_line_id) AS total_sold
        FROM
            invoice_line il
        JOIN invoice i ON
            il.invoice_id = i.invoice_id
        JOIN
            track t ON il.track_id = t.track_id
        JOIN
            album a ON t.album_id = a.album_id
        WHERE
            i.invoice_date >= :start
            AND i.invoice_date <= :end
        GROUP BY
            a.album_id
        ORDER BY
            total_sold DESC
        LIMIT :limit
      # define the outputs
      responses:
        # a response with the status in 200-299 must be defined
        '200':
          description: A list of top-selling albums
          content:
            application/json:
              schema:
                type: array
                items:
                  type: object
                  properties:
                    album_id:
                      type: integer
                      description: The id of the album
                    album_title:
                      type: string
                      description: The title of the album
                    total_sold:
                      type: integer
                      description: The number of albums sold
```

### Security

Until now, the illustrated `api_foundry` deployments have omitted applying any authorization of requests. While the AWS infrastructure deployed has been protected using AWS security mechanisms, the API itself has been publicly accessible, with unrestricted access to all path operations.

In real-world applications it is essential to ensure that requestors are restricted to the operations they are allowed to perform and what data they may access. With `api_foundry`, these authorizations are defined in the API specification, allowing fine-grained control of access to data resources.

`api_foundry` utilizies the underlying token based authorization services provided by the AWS RestAPI.

There are three parts to controlling access to the application API;

* **Token Validation Functions** In this part the Lambda functions that validate the token presented with the request are registered with the application API.


* **Setting Security In the API Specification** Here the token validation functions are associated with the schema objects and path operations in the application OpenAPI specification.

* **Setting Role Based Permissions** In this part restrictions can be set to what data can be read, written, or deleted based on role.

Services are publicly available until until security is set in the API specification, allowing the API to have both public and private services.  Once security for a component has been set access to it is available to all validated requests.  Permissions allow restricting access further based on the requests roles.

An API can utilize multiple validation functions.

##### Registering Validation Functions

`api_foundry` uses the underlying Rest API token based validation to for restricting access to the API.  With this mechanism the token validator function decodes the JWT bearer token that was presented with the request in the `Authorization` header.  If the token validation function successfully validates the token it then returns the roles associated with the user, or subject as a Oauth object.

`api_foundry` does not provide the token validation functions and those be provided by the API implementor.

> Code samples here use the Simple Oauth Server project that includes a token validation function that can be found here.

Token validation functions can be added to the application `API_Foundry` object using the `token_validators` parameter.  This parameter accepts a list of validation entries where each entry contains;

* `name` - this must be unique to the scope of the API and will be used when identifying validators for components in the API's specification.
* `function` - this is a Cloud Foundry function.

> Cloud Foundry is a companion project that simplifies deployment of cloud centric applications.  Functions can be defined inline with Cloud Foundry handling the packaging and deployment.

In the following example the Simple Oauth Server provides a validation Cloud Foundry function that will be used in the API specification.

```python
api_foundry = APIFoundry(
    "chinook",
    api_spec= "./chinook_api_authorized.yaml",
    secrets= json.dumps({"chinook": "chinook/postgres"}),
    token_validators=[{
        "name": "simple-auth",
        "function": my_oauth.validator()
    }]
)
```

To use an existing token validation function Cloud foundry allows importing it.  Here is and example of using an existing token valudation function;

```python

from cloud_foundry import import_function

api_foundry = APIFoundry(
    "chinook",
    api_spec= "./chinook_api_authorized.yaml",
    secrets= json.dumps({"chinook": "chinook/postgres"}),
    body=oauth.authorizer_api_spec,
    token_validators=[{
        "name": "simple-auth",
        "function": import_function("my-validator")
    }]
)
```

#### Extending the API Specfication with Security Instructions

API components remain publically accessable until associated with a token validation function using OpenAPI security instructions.

These security instructions can be applied globally across the API or specifically to individual schema objects (table integrations) or path operations (custom SQL). This section explains how to configure these security associations for your API.

##### Global Security Instructions

To enforce security globally for all API operations, you can define security requirements at the top level of the OpenAPI specification. This is done using the standard security attribute in the OpenAPI specification.

For example:

```yaml
security:
  - my-oauth: []
```

In this example:

* All operations in the API will require the my-oauth token validation function.
* The user must have one or more of the read or write scopes.

Global security requirements are automatically inherited by all operations in the API unless explicitly overridden by a specific schema object or path operation.

### Security Instructions for Schema Object

For schema objects or table integrations, **API-Foundry** provides the extended `x-af-security` attribute within the schema definition. This attribute defines validation rules for CRUD (Create, Read, Update, Delete) operations, allowing fine-grained access control for the API-generated services.

The keys under `x-af-security` (e.g., `my-oauth`) reference validators configured earlier. Validators authenticate and authorize requests by validating bearer tokens and extracting claims such as roles and permissions. During runtime, these security rules are applied to ensure that only authorized users can perform specific operations.

---

### Using `x-af-security` for Table Operations

The `x-af-security` attribute specifies roles and their associated permissions for CRUD actions. Each role defines which properties of a table can be accessed or modified for specific operations.

#### **Example**

Below is an example of the `x-af-security` attribute applied to an `invoice` schema:

```yaml
components:
  schemas:
    invoice:
      type: object
      x-af-database: chinook
      x-af-security:
        my-oauth:
          sales_reader:
            read: "^(customer_id|total)$"
          sales_associate:
            read: "*"
            write: "^(customer_id|total|status)$"
          sales_manager:
            read: "*"
            write: "*"
            delete: "*"
      properties:
        invoice_id:
          type: integer
          x-af-primary-key: auto
        customer_id:
          type: integer
        total:
          type: number
        status:
          type: string
```

#### **Explanation**:
- **`x-af-security`**:
  - A dictionary where each key represents a security mechanism (e.g., `my-oauth`).
  - Under `my-oauth`, roles such as `sales_reader`, `sales_associate`, and `sales_manager` are defined with their permissions.
- **Permissions**:
  - **`read`**: Specifies which fields can be read by a role.
  - **`write`**: Specifies which fields can be modified using POST or PUT operations.
  - **`delete`**: Grants permission to delete records.
- **Regex-Based Field Access**:
  - Fields can be matched using regular expressions. For example, `^(customer_id|total)$` allows access to only the `customer_id` and `total` fields.

#### **Key Highlights**:
- `"*"` grants unrestricted access for an operation (e.g., `read: "*"` means the role can read all fields).
- Operations with no matching rules will be denied by default.

---

### Token Validation Workflow

When a request is received, **API-Foundry** processes security rules as follows:

1. **Token Validation**:
   - The validator (e.g., `my-oauth`) validates the token provided in the request.
   - The token is checked for authenticity, expiration, and claims (e.g., `sub`, `scope`, and custom claims).

2. **Claim Matching**:
   - Roles in `x-af-security` are matched against claims in the token.
   - The validator verifies whether the user's roles and scopes permit the requested operation (e.g., `read`, `write`, `delete`).

3. **Permission Enforcement**:
   - If the requested operation matches the permissions defined in `x-af-security`, the operation is allowed.
   - Otherwise, the request is denied.

---

### Role-Based Access Control (RBAC)

The `x-af-security` attribute enables Role-Based Access Control (RBAC), where roles map directly to specific permissions:

- **Example Roles**:
  - **`sales_reader`**:
    - Can only read specific fields (e.g., `customer_id`, `total`).
  - **`sales_associate`**:
    - Can read all fields and modify limited fields (`customer_id`, `total`, `status`).
  - **`sales_manager`**:
    - Has full read, write, and delete access.

---

### Example Use Case: Invoice Management

**Scenario**:
- A `sales_reader` wants to view an invoice.
- The API receives the request with a bearer token.
- The token is validated, and the user's role (`sales_reader`) is extracted.
- The role is checked against the `x-af-security` rules.
- The user can only view `customer_id` and `total` fields as per the defined permissions.

---

### Debugging Tips

1. **Ensure Token Contains Required Claims**:
   - Verify that the token includes the expected roles or permissions.
   - Use tools like `jwt.io` to decode and inspect the token.

2. **Check `x-af-security` Configuration**:
   - Validate that the `x-af-security` attribute is correctly defined in the OpenAPI specification.
   - Ensure roles and permissions are aligned with business requirements.

3. **Role and Scope Mismatch**:
   - If a role in the token does not match a defined role in `x-af-security`, the request will be denied. Double-check the role configuration.

4. **Logging**:
   - Enable detailed logging in your validator to trace token validation and permission checks.

---

### Summary

The `x-af-security` attribute allows fine-grained control over table operations by combining Role-Based Access Control with token validation. Using the attribute:
- Permissions can be tailored for specific roles and operations.
- Validators enforce security rules based on token claims.

By leveraging this mechanism, you ensure robust access control while maintaining flexibility in your API's security configuration.

##### Security Instructions for Custom SQL

For custom SQL path operations, security is defined using the standard security attribute in OpenAPI specifications. The security attribute specifies which validators (e.g., oauth) and scopes (e.g., read, write) are required to access the operation.

Here’s an example:

```yaml
paths:
  /top_selling_albums:
    get:
      summary: Get top-selling albums
      description: Returns the top-selling albums within a specified date range.
      security:
        - oauth:
            - read
      parameters:
        - in: query
          name: start
          schema:
            type: string
            format: date-time
          required: true
        - in: query
          name: end
          schema:
            type: string
            format: date-time
          required: true
      x-af-database: chinook
      x-af-sql: >
        SELECT
            a.album_id AS album_id,
            a.title AS album_title,
            COUNT(il.invoice_line_id) AS total_sold
        FROM
            album a
        JOIN track t ON a.album_id = t.album_id
        JOIN invoice_line il ON t.track_id = il.track_id
        WHERE i.invoice_date BETWEEN :start AND :end
        GROUP BY a.album_id
        ORDER BY total_sold DESC
        LIMIT 10
      responses:
        '200':
          description: A list of top-selling albums
          content:
            application/json:
              schema:
                type: array
                items:
                  type: object
                  properties:
                    album_id:
                      type: integer
                      description: The ID of the album
                    album_title:
                      type: string
                      description: The title of the album
                    total_sold:
                      type: integer
                      description: The number of albums sold
```
Explanation:

* The security attribute specifies that the oauth validator is required, and the user must have the read scope to access this operation.
* The rest of the definition describes the operation, including request parameters, custom SQL, and response format.

##### Combining Global and Local Security Instructions
When both global and local security instructions are defined, local instructions take precedence over global settings for the specific operation. This allows flexibility in enforcing security at different levels.

For example:

* A global security attribute may enforce oauth validation for all operations.
* A specific path operation or table integration can override this with more restrictive or permissive rules.

#### Configuring Security Validators
In API-Foundry, a security validator is a function that validates the bearer token and extracts claims from it. These claims are then used to determine if the request is authorized.

Adding a Validator
1. To add a validator, define a Lambda function that performs the following steps:
Decode the bearer token.
1. Validate the token’s signature and expiration.
1. Extract claims such as sub (subject), scope, and permissions.
1. Return the claims if valid or raise an error if invalid.

For example:

```python
import jwt

def validate_token(token):
    try:
        decoded = jwt.decode(token, key="your-secret-key", algorithms=["HS256"])
        return decoded
    except jwt.ExpiredSignatureError:
        raise Exception("Token expired")
    except jwt.InvalidTokenError:
        raise Exception("Invalid token")

```

#### Best Practices

* **Start with Global Security:** Apply global security instructions to enforce a base level of access control across the entire API.
* **Use Specific Rules for Sensitive Operations:** Add local security instructions to enforce stricter controls on operations that handle sensitive data or require elevated privileges.
* **Document Security Instructions:** Clearly document the roles, scopes, and permissions required for each path operation to make it easier for developers to understand and maintain the API.
By combining these techniques, you can build secure and robust APIs with API-Foundry while maintaining flexibility and control over access permissions.

# Configuration

During the implementation of the API specification, schema objects and operation paths were associated with a database name using the `x-af-database` attribute.

In this section, we will cover how API-Foundry uses that attribute to connect to the database and perform the operations needed to complete requests.

First, the connection data that API-Foundry uses to establish database connections is never 'built-in' to the Lambda function or any other part of the deployment. Instead, API-Foundry obtains the connection data from an AWS Secrets Manager secret. Secrets are loaded on demand and only once per instance.

As part of the deployment, a secrets map will need to be provided. This mapping allows API-Foundry to determine the secret name using the `x-af-database` attribute value as the key.  An API can span multiple databases and the secrets map must contain a mapping for all databases referenced.

Thus, there are two main configuration tasks: creating the secrets and providing the secrets map in the deployment code.

## Configuring Secrets

When API-Foundry accesses connection data in a secret, it expects a JSON string containing the required connection parameters.

| Parameter     | Description                                               | Value                                                           |
|---------------|-----------------------------------------------------------|-----------------------------------------------------------------|
| engine        | Designates the SQL dialect to use for the database.       | Required; must be one of: `postgres`, `oracle`, `mysql`         |
| host          | The host name of the database.                            | Required                                                        |
| port          | The port for the database.                                | Optional; defaults to the default for the database engine       |
| database      | The database name to access.                              | Optional; defaults to the same as the username                  |
| username      | The username to connect as.                               | Required                                                        |
| password      | The password to connect with.                             | Required                                                        |
| configuration | Additional database-specific configuration parameters.    | Optional; an object mapping parameters to values                |

[Postgres Connection](https://www.postgresql.org/docs/current/libpq-connect.html#LIBPQ-CONNSTRING)

# Deployment

# Reference

## API Definition

### Schema Component Objects

#### Schema Component Object Attributes

These attributes map the componnent object to a database table.

| Attribute | Description | Usage |
|-------|--------|---------|
| x-af-database | The name of the database where the table is located.   | Required, value is used to access database configuration from the runtime secrets map. |
| x-af-engine | The type of database being accessed. Determines SQL dilect to use.  | Required, must be one of 'postgres', 'oracle' or 'mysql' |
| x-af-table | The table name to perform the operations on. | Optional, defaults to schema component object name if not provided.  Must be a valid table name |
| x-af-concurency-control | The name of the property

#### Schema Component Object Property Attributes

| Attribute             | Description                                                                                            | Usage                                                                                   |
|-----------------------|--------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------|
| x-af-column-name      | Specifies the database column name if it differs from the property name.                                | Optional                                                                                |
| x-af-primary-key      | Indicates that this property serves as the primary key for the object and defines how the key is obtained. | Required; must be one of the following: manual, auto, or sequence.                       |
| x-af-sequence-name    | Specifies the database sequence to be used for generating primary keys.                                     | Required only when the primary key type is "sequence".                                    |
#### Schema Component Object Associations

When defining the api using schema objects the Open API specication allows properties that can be either objects or array of objects in addition to the other basic types.  With additional custom attributes API-Foundry can populate these properties saving the client application the need to make multiple requests to construct objects with these properties.

**Including an Object Property**

Consider the following api spec;

```yaml
components:
  schemas:
    customer:
      type: object
      x-af-engine: postgres
      x-af-database: chinook
      properties:
        customer_id:
          type: integer
          x-af-primary-key: auto
        company:
          type: string
          maxLength: 80
    invoice:
      type: object
      x-af-engine: postgres
      x-af-database: chinook
      properties:
        invoice_id:
          type: integer
          x-af-primary-key: auto
        customer_id:
          type: integer
        customer:
          $ref: '#/components/schemas/customer'
          x-af-parent-property: customer_id
```

In this example, the `customer` property of the `invoice` schema is an object type after reference resolution. By setting the `x-af-parent-property` attribute to a sibling property, API-Foundry will use the value of that property to resolve the object value. Specifically, in this example, the `customer_id` value of the invoice will be used to select the corresponding customer.

> Internally API-Foundry uses inner joins to select these objects using a single database operation.

**Including an Array Propety**


Consider the following api spec:
```
    invoice:
      type: object
      x-af-engine: postgres
      x-af-database: chinook
      properties:
        invoice_id:
          type: integer
          x-af-primary-key: auto
        line_items:
          type: array
          items:
            $ref: "#/components/schemas/invoice_line"
            x-af-child-property: invoice_id
    invoice_line:
      type: object
      x-af-engine: postgres
      x-af-database: chinook
      properties:
        invoice_line_id:
          type: integer
          x-af-primary-key: auto
        invoice_id:
          type: integer
        track_id:
          type: integer
```

In this example, the `line_items` property of the `invoice` schema is an array of `invoice_lines` type after reference resolution.  By setting the `x-af-child-property` attribute to a property in the `invoice_line` schema, API-Foundry will use the primary key value of the invoice to select on that property.  Specifically, in this example, the `invoice_id` values from the selected `invoice`s will be used to filter on the `invoice_id` property of the associated `invoice_line` items.


| Attribute             | Description                                          | Usage             |
|-----------------------|------------------------------------------------------|-------------------|
| x-af-parent-property  | The name of the 'primary' property that identifies the selection key.  | Optional, defaults to `parent` primary key.  Normally needed for 1:1 associations. |
| x-af-child-property   | The name of the property in the `secondary` object used as the selection key | Optional, defaults to primary key of  defaults to the child if not specified |

##### One-to-One Associations

When defining an association property for a one-to-one (1:1) association, the associated schema component can be included as a property of the object being returned.

In the Chinook database, an example of this type of association can be found in the `invoice` table, where the `customer_id` serves as a foreign key referencing the customer record.

In the schema component object model, this relationship can be specified, allowing the resultant invoice objects to have a `customer` property containing a customer object.


Here's an example of how the `customer` property would be specified in the `invoice` schema component object;


    invoice:
      type: object
      x-af-engine: postgres
      x-af-database: chinook
      properties:
        invoice_id:
          type: integer
          x-af-primary-key: auto
        customer_id:
          type: integer
        customer:
          x-af-type: relation
          x-af-schema-object: customer
          x-af-parent-property: customer_id

In this example the `customer` property type is specified as being a relation to the schema component object `customer'.  When fetching data API-Make will then use

With API-Foundry

| Attribute | | Description |
|-----------|-|-------------|
| x-af-schema | Required | The name of the schema component object to use as the source of the relation. |
| x-af-cardinality | Optional | Can be either single or multiple, defaults to single |
| x-af-parent-property | Required | The name of the sibling property to use as the selection key in the relation |
| x-af-child-property | Optional |


# Appendix

# Generating OpenAPI Schemas

## PostgreSQL Database Schemas


This section provides instructions on how to use the `postgres_to_openapi` script, which is included in the `api_foundry` package, to generate OpenAPI schemas from PostgreSQL database schemas. The generated OpenAPI schemas will include the necessary components to represent the database tables, columns, primary keys, and foreign key relationships.

#### Prerequisites

- Python 3.x
- `psycopg2-binary` library for PostgreSQL connectivity
- `pyyaml` library for YAML processing

You can install the `api_foundry` package and its dependencies using the following command:
```sh
pip install api_foundry psycopg2-binary
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

The generated OpenAPI schema will include component schema objects representing the database tables and their columns. Primary keys will be marked with the `x-af-primary-key` attribute, and foreign key relationships will include references to related schemas with the `x-af-parent-property` attribute.

Here is an example of the generated schema for a table named `invoice`:

```yaml
components:
  schemas:
    # The name of the schema object is used for
    # both the API path (/invoice) and the table
    # name
    invoice:
      type: object
      x-af-database: chinook-auto-increment
      properties:
        invoice_id:
          type: integer
          # indicates the property is a primary key
          x-af-primary-key: auto
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
          x-af-parent-property: customer_id
          description: Customer associated with the invoice.
```


# Attic

With API-Foundry, developing RESTful API's is first focused on defining components and services in the form of an Open API specification.  Objects in this specification then can be enhanced by either;

* Schema component objects can be enhanced with database table configuration, allowing API-Foundry to provide RESTful CRUD services on table records.
* Path operations can be enhanced with database connection and SQL configuration to provide service based on custom SQL.

For data read operations using HTTP GET, API-Foundry provides robust data selection capability reducing the need for building custom services. To achieve this API-Foundry provides the following features;

* Comparison oprands can be applied to a property when selecting data.  These operand such as; less than, between, and in, can be applied to any property for record selection.
* Associations between component objects can be defined allowing retrieval of complex objects containing associated data in a single request.
* Requesting applications can restrict the properties being returned.
* Requesting applications can select the case convention (snake or lower camel) of the ressponse results.

API-Foundry is not a traditional object relational model (ORM) library but rather operates by generating and executing SQL queries to perform its services.  Generating operations this way keeps marshaling and unmarshaling objects to a minimum, ensuring efficient data retrieval and manipulation.

Deploying APIs with API-Foundry involves the following steps:

1. Store the annotated API specification on Amazon S3.
2. Configure and deploy the Lambda archive.
3. Retrieve an enhanced API specification from the Lambda function.
4. Deploy the AWS Gateway API using the enhanced specification.


# Usage

When utilizing API-Foundry to construct APIs, the primary focus of development lies in defining component schema objects and path operations.

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

When processing requests, API-Foundry categorizes parameters into three categories: query, store, and metadata.

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

When schema objects are enhanced with database configuration API-Foundry builds the following services.


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
then API-Foundry restricts updates to single records.  Without a version property then normal record selection occurs allowing bulk updates
of records.


## Query Parameters

| Methon | Operation | Query Parameters | Store Parameters | Metadata Parameters |
|--------|-----------|------------------|------------------|---------------------|
| GET    | read      |
| POST   | create    | Not accepted     | Required         |
| PUT    | update    |
| DELETE | delete    |

Request parameters for services provided by API-Foundry

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

API-Foundry uses a token based schema to determine authorization. Authentication and authorization with the API follows the following sequence.

![Authorization Sequence](./resources/uml/authorization-flow.png)

<div hidden>
@startuml
title API Request Authentication and Authorization Flow

actor Client as "Client Application"
participant "Authorization Service" as AuthService
participant "API Gateway" as Gateway
participant "Validation Service" as ValidationService
participant "API Foundry Query Engine" as Server

== Token Request Flow ==

Client -> AuthService : Request Bearer Token (credentials)
note right of AuthService : Authorization Service validates\nclient credentials and grants access token
AuthService --> Client : Response with Bearer Token (JWT)

== Request Authentication and Authorization Flow ==

Client -> Gateway : Request API Resource (/path/operation) with Bearer Token
note right of Gateway : Client sends a request to the API Gateway\nincluding the Bearer token (JWT) in the Authorization header

alt No Authorization header or token is missing
    Gateway -> Client : 401 Unauthorized
else Token provided
    Gateway -> ValidationService : Verify JWT Token
    note right of ValidationService : Validation Service verifies the token\nand decodes it to check claims

    alt Token is invalid or expired
        ValidationService --> Gateway : 401 Unauthorized
        Gateway -> Client : 401 Unauthorized
    else Token is valid
        ValidationService --> Gateway : Valid Token (JWT claims)
        note right of Gateway : Token is verified. Extract claims\nsuch as 'sub', 'scope', and 'permissions'

        alt Scope and permissions not allowed
            Gateway -> Client : 403 Forbidden
        else Scope and permissions allowed
            Gateway -> Server : Forward request to /path/operation
            note right of Server : Server performs the operation\nbased on user permissions
            Server --> Gateway : Operation Result (e.g., data, success)
            Gateway --> Client : Respond with result
        end
    end
end

@enduml
</div>

**Explanation**

* **Token Request Flow:**

  * The Client requests a Bearer token from and external Authorization Service by providing credentials.
  * The Authorization Service verifies the credentials and issues a JWT as a Bearer token if valid.
  * The Client receives the Bearer token.

* **Request Authentication and Authorization Flow:**
  * Client uses the Bearer token to request an API resource from the API Gateway.
  * API Gateway verifies the presence of the token and forwards it to the Validation Service for verification.
  * Validation Service checks the token validity:
  * If invalid or expired, 401 Unauthorized is returned.
  * If valid, token claims (sub, scope, permissions) are extracted.

* **Authorization Check:**
  * If the required scope or permissions are missing, a 403 Forbidden response is sent to the Client.
  * If permissions are adequate, the request is forwarded to the API Server.

* **API-Foundy Query Server:**
  * Performs the operation, and the result is returned to the Client.
  * Uses the token claims (sub, scope, permissions) to determine if the operation is permitted for the user and perform any redactions to the response data.

Configuring authorization in API_Foundry consist of two parts.  First a token validator function must be configured in the foundry server.  And then authorization instructions can be added to the API specification.  These instructions allow configuring the operations an data a user can access.
