# Creating an API Specification

This document provides a guide for creating an OpenAPI specification that defines the API and its interaction with relational databases using API-Foundry. The specification allows developers to describe API endpoints, database mappings, and operational rules.

## Overview

API-Foundry leverages the OpenAPI specification to generate APIs automatically from defined schema objects. Each database table to be exposed through the API must have a corresponding schema object in the specification. These schema objects map table columns to API properties and define the operations that can be performed.

---

## Steps to Create an API Specification

### 1. Define Basic Information

Start with the basic details about the API in the OpenAPI specification:

```yaml
openapi: 3.0.0
info:
  title: Example API
  version: 1.0.0
  description: This is a sample API generated using API-Foundry.
servers:
  - url: https://api.example.com
```

### 2. Define Components and Schemas

Each database table exposed by the API must have a corresponding schema in the `components` section. The schema should map the table columns to properties in the OpenAPI specification. Custom attributes such as `x-af-database` and `x-af-primary-key` are used to define database-specific configurations.

Example:

```yaml
components:
  schemas:
    album:
      type: object
      x-af-database: chinook-db
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
```

### 3. Use Provided Tooling to Generate a Starter Specification

API-Foundry includes tools that generate a starter OpenAPI specification by analyzing the database schema. These tools can:

- Identify database tables and columns.
- Generate schema objects automatically based on the database design.

Command:

```bash
python tools/generate_spec.py --database-url=<DATABASE_URL> --output=spec.yaml
```

The resulting `spec.yaml` file provides a template that can be refined further.

### 4. Mutating Properties

When a record is modified, certain properties can be automatically updated to reflect the modification. These mutating properties provide a consistent way to track changes and maintain record history.

#### ### Identifying Mutating Properties

Mutating properties are attributes that are automatically updated with each modification of a record.  API-Foundry leverages mutating properties for implementing optimistic locking. When updating records, the client must include the mutating property (e.g., `revision`) at either a query string or path parameter. If the provided value does not match the current value stored in the database, the update will be rejected with a `409 Conflict` response. This mechanism ensures that updates are applied only to the latest version of the record, preventing unintended overwrites.

A mutating property affects the resulting API services offered.  Specifically the mutating property must be included either in the query string parameters or the request path. Update of multiple records is prohibited,  only a single record can be selected for updates when using a mutating property.  Additionally, mutating properties can not be updated using the request body.

To define a mutating property, add the `x-af-concurrency` attribute to the schema property. This attribute ensures the property is managed correctly for optimistic locking. Supported property types include:

- **Integer**: For tracking revision numbers or update counts.
- **String**: To store unique identifiers for modifications.
- **Timestamp**: For recording the exact time of the last modification.

&#x20;

Common types of mutating properties include:

- **Timestamps (********`updated_at`********\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*)**: Tracks the last modification time of the record, typically stored in a `date-time` format.
- **Strings (********`updated_by`********\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*)**: Stores identifiers, such as usernames or system identifiers, to record who or what modified the record.
- **Integers (********`revision`********\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*)**: Represents an incrementing counter to track the number of modifications made to a record.

#### Examples of Usage

These properties are defined within the schema and can serve multiple purposes, including audit trails, conflict detection, and historical analysis.

Example:

```yaml
components:
  schemas:
    album:
      type: object
      x-af-database: chinook-db
      properties:
        album_id:
          type: integer
          x-af-primary-key: auto
        title:
          type: string
          maxLength: 160
        artist_id:
          type: integer
        updated_at:
          type: string
          format: date-time
          description: Timestamp of the last update.
        updated_by:
          type: string
          description: Identifier of the user who last modified the record.
        revision:
          type: integer
          description: Incremental revision number for the record.
      required:
        - album_id
        - title
        - artist_id
```

#### Benefits of Mutating Properties

1. **Auditability**: Provides a clear record of who modified the data and when.
2. **Conflict Prevention**: The `revision` property can act as a lightweight alternative to versioning for detecting update conflicts.
3. **History Tracking**: Simplifies the implementation of historical data analysis or rollback functionality.

By including mutating properties in your schema, you can enhance the reliability and maintainability of your API.

### 5. Define Advanced Configuration (Optional)

Custom configurations can be added to support advanced use cases:

- **Custom SQL Operations**: Define operations that run custom SQL queries.
- **Role-Based Access Control (RBAC)**: Add role-specific permissions using attributes in the schema.

Example:

```yaml
paths:
  /search:
    get:
      summary: Search for items
      parameters:
        - name: query
          in: query
          required: true
          schema:
            type: string
      responses:
        '200':
          description: Search results
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/album'
```

---

By following these steps, you can create a robust OpenAPI specification for your project, enabling API-Foundry to generate and deploy a fully functional API seamlessly. Let me know if you would like more details or examples!

