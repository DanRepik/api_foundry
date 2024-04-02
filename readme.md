# API-MAKER

Welcome to API-Maker, an open-source tool designed for building and deploying RESTful services seamlessly utilizing an AWS Gateway API in conjunction with a Lambda function. Our project's primary objective is to offer a solution that demands minimal coding effort to query and manipulate data stored in relational databases.

API-Maker operates by building and executing SQL queries to perform its services, ensuring efficient data retrieval and manipulation.

With API-Maker, developing APIs is simplified through adherence to OpenAPI standards, where components and paths defining the API are specified. By annotating schema component objects with database table configurations, API-Maker automatically generates CRUD services, including a robust query service. Moreover, specifying and annotating path operations facilitates the creation of services capable of executing custom SQL operations.

Deploying APIs with API-Maker involves the following steps:

1. Store the annotated API specification on Amazon S3.
2. Configure and deploy the Lambda archive.
3. Retrieve an enhanced API specification from the Lambda function.
4. Deploy the AWS Gateway API using the enhanced specification.


# Usage

When utilizing API-Maker to construct APIs, the primary focus of development lies in defining component schema objects and path operations.

Annotations on component schema objects enable seamless operations on database tables. At a minimum, these annotations configure the database and table name. However, additional annotations are available to enhance functionality:

- Renaming exposed API properties to table column names.
- Implementing record versioning using either a last updated timestamp or version number.
- Supporting auto-generated primary keys.
- Establishing relationships with other component schema objects to enable parent-child retrievals.

Annotations to the OpenAPI specification document provides the means of mapping from API elements to database resources.  

This is done via two primary methods.

* Component Schema Objects to Database Tables - These objects can be mapped to database tables.  When this mapping is available api-maker will build supporting CRUD services.

* Path Operations to Custom SQL - This method allows attaching custom SQL to a specific operation. 

What api-maker provides is;

* 

API Services

Selecting Results

The `_properties` metadata parameter enables the service requester to specify the desired properties in the response. This parameter is optional, and if not provided, the service result will include objects with all properties including relational properties selected by default.

When utilized, the `_properties` parameter should be a string comprising a delimited list of regular expressions. If a property matches any of these expressions, it will be incorporated into the response. Moreover, if the schema component object contains relational properties, the composition of those properties can also be selected. In such cases, the relation name is prepended with a ':' delimiter followed by a regular expression for selecting properties of the related object.

Consider the following examples with the Chinnook invoice schema object;

| _properties | Description| 
|-------------|------------|
| .*          | Returns all invoice properties |
| .* line_items | Returns all invoice properties and the line_items associated with the invoice |
| invoice_id total | Returns just the invoice id and total |


Metadata Parameters

| Name | Description |
| _properties | Optional, allows selecting a subset of properties returned by the request.   
A space delimited list of regular expressions |


Open API Specification Extensions

Schema Component Objects

| Attribute | Description |
|-------|--------|
| x-am-database | The name of the database to use for operations on this component object.   |
| x-am-engine | The type of database.  Must be one of 'postgres', 'oracle' or 'mysql' |
| x-am-table | The table name to perform the operations on |


Schema Component Object Properties

| Attribute | Description |
|-----------|-------------|
| x-am-column-name | The database column name if different from the property name.  Optional |


Schema Component Object Relations

| Attribute | | Description |
|-----------|-|-------------|
| x-am-schema | Required | The name of the schema component object to use as the source of the relation. |
| x-am-cardinality | Optional | Can be either single or multiple, defaults to single |
| x-am-parent-property | Required | The name of the sibling property to use as the selection key in the relation |
| x-am-child-property | Optional | 