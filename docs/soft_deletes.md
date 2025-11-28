# Soft Deletes in API Foundry

Soft deletes allow you to mark records as "deleted" without physically removing them from the database. This approach maintains data integrity, enables audit trails, and allows for data recovery while keeping deleted records hidden from normal operations.

## Overview

API Foundry supports soft deletes through the `x-af-soft-delete` extension attribute on schema object properties. When configured, API Foundry automatically excludes "soft deleted" records from read operations and provides mechanisms to restore or permanently delete them.

## Soft Delete Strategies

API Foundry supports four different soft delete strategies:

### 1. Null Check Strategy

Records are considered deleted when a specific field is `NULL`.

```yaml
components:
  schemas:
    user:
      type: object
      x-af-database: mydb
      properties:
        id:
          type: integer
          x-af-primary-key: auto
        name:
          type: string
        deleted_at:
          type: string
          format: date-time
          x-af-soft-delete:
            strategy: null_check
```

**Behavior:**
- **Active records**: `deleted_at` is `NULL`
- **Soft deleted**: `deleted_at` contains a timestamp
- **Read operations**: Automatically excludes records where `deleted_at IS NOT NULL`

### 2. Boolean Flag Strategy

Records are marked as deleted using a boolean field.

```yaml
components:
  schemas:
    product:
      type: object
      x-af-database: mydb
      properties:
        id:
          type: integer
          x-af-primary-key: auto
        name:
          type: string
        is_deleted:
          type: boolean
          x-af-soft-delete:
            strategy: boolean_flag
```

**Behavior:**
- **Active records**: `is_deleted` is `false`
- **Soft deleted**: `is_deleted` is `true`
- **Read operations**: Automatically excludes records where `is_deleted = true`

### 3. Exclude Values Strategy

Records are considered deleted when a status field contains specific values.

```yaml
components:
  schemas:
    order:
      type: object
      x-af-database: mydb
      properties:
        id:
          type: integer
          x-af-primary-key: auto
        customer_id:
          type: integer
        status:
          type: string
          enum: [pending, processing, shipped, delivered, cancelled, refunded]
          x-af-soft-delete:
            strategy: exclude_values
            values: [cancelled, refunded]
```

**Behavior:**
- **Active records**: `status` is any value except `cancelled` or `refunded`
- **Soft deleted**: `status` is `cancelled` or `refunded`
- **Read operations**: Automatically excludes records where `status IN ('cancelled', 'refunded')`

### 4. Audit Field Strategy

Records are marked with an audit field that tracks deletion status and metadata.

```yaml
components:
  schemas:
    document:
      type: object
      x-af-database: mydb
      properties:
        id:
          type: integer
          x-af-primary-key: auto
        title:
          type: string
        audit_status:
          type: string
          x-af-soft-delete:
            strategy: audit_field
```

**Behavior:**
- **Active records**: `audit_status` is `NULL` or `'active'`
- **Soft deleted**: `audit_status` contains deletion metadata
- **Read operations**: Automatically excludes records with non-null/non-active audit status

## Configuration Examples

### Basic Soft Delete with Timestamp

```yaml
components:
  schemas:
    employee:
      type: object
      x-af-database: hr
      properties:
        employee_id:
          type: integer
          x-af-primary-key: auto
        first_name:
          type: string
        last_name:
          type: string
        email:
          type: string
        deleted_at:
          type: string
          format: date-time
          description: Timestamp when the employee was soft deleted
          x-af-soft-delete:
            strategy: null_check
```

### Status-Based Soft Delete

```yaml
components:
  schemas:
    job_posting:
      type: object
      x-af-database: jobs
      properties:
        job_id:
          type: integer
          x-af-primary-key: auto
        title:
          type: string
        description:
          type: string
        status:
          type: string
          enum: [draft, active, paused, expired, cancelled]
          description: Job posting status
          x-af-soft-delete:
            strategy: exclude_values
            values: [cancelled]
```

### Multiple Exclusion Values

```yaml
components:
  schemas:
    subscription:
      type: object
      x-af-database: billing
      properties:
        subscription_id:
          type: integer
          x-af-primary-key: auto
        user_id:
          type: integer
        plan:
          type: string
        status:
          type: string
          enum: [active, paused, cancelled, expired, terminated]
          x-af-soft-delete:
            strategy: exclude_values
            values: [cancelled, expired, terminated]
```

## Automatic Behavior

When soft deletes are configured, API Foundry automatically modifies SQL queries:

### Read Operations (GET)

**Without soft delete:**
```sql
SELECT * FROM employees WHERE department_id = ?
```

**With soft delete (null_check):**
```sql
SELECT * FROM employees
WHERE department_id = ?
  AND deleted_at IS NULL
```

**With soft delete (exclude_values):**
```sql
SELECT * FROM job_postings
WHERE company_id = ?
  AND status NOT IN ('cancelled')
```

### Delete Operations

Instead of physical deletion, API Foundry performs soft deletion:

**Boolean flag strategy:**
```sql
UPDATE products
SET is_deleted = true
WHERE id = ?
```

**Null check strategy:**
```sql
UPDATE employees
SET deleted_at = CURRENT_TIMESTAMP
WHERE employee_id = ?
```

**Exclude values strategy:**
```sql
UPDATE job_postings
SET status = 'cancelled'
WHERE job_id = ?
```

## Advanced Features

### Querying Soft Deleted Records

To include soft deleted records in queries, use the special metadata parameter `__include_soft_deleted`:

```
GET /api/employees?__include_soft_deleted=true
```

This bypasses the automatic soft delete filtering.

### Restoring Soft Deleted Records

API Foundry provides restore functionality for soft deleted records:

```
POST /api/employees/{id}/restore
```

This operation:
- Sets `deleted_at` to `NULL` (null_check strategy)
- Sets `is_deleted` to `false` (boolean_flag strategy)
- Changes status to a non-excluded value (exclude_values strategy)

### Conflict Detection

API Foundry automatically detects when query parameters conflict with soft delete conditions and provides helpful error messages:

```json
{
  "error": "Query conflicts with soft delete configuration",
  "details": "Querying for status='cancelled' conflicts with soft delete exclusion of ['cancelled']",
  "suggestion": "Use __include_soft_deleted=true to query soft deleted records"
}
```

## Best Practices

### 1. Choose the Right Strategy

- **null_check**: Best for audit trails with timestamps
- **boolean_flag**: Simple and efficient for basic soft deletes
- **exclude_values**: Perfect for workflow-based systems with status fields
- **audit_field**: Advanced scenarios requiring detailed deletion metadata

### 2. Database Indexing

Add indexes to soft delete columns for performance:

```sql
-- For null_check strategy
CREATE INDEX idx_employees_not_deleted ON employees (deleted_at) WHERE deleted_at IS NULL;

-- For boolean_flag strategy
CREATE INDEX idx_products_active ON products (is_deleted) WHERE is_deleted = false;

-- For exclude_values strategy
CREATE INDEX idx_jobs_active ON job_postings (status) WHERE status NOT IN ('cancelled');
```

### 3. Documentation

Always document your soft delete strategy in the schema description:

```yaml
deleted_at:
  type: string
  format: date-time
  description: |
    Timestamp indicating when this record was soft deleted.
    NULL means the record is active.
  x-af-soft-delete:
    strategy: null_check
```

### 4. Consistent Naming

Use consistent naming conventions across your API:

- `deleted_at` for timestamp-based soft deletes
- `is_deleted` for boolean flags
- `status` for workflow-based exclusions

## Limitations

1. **Single Field**: Each schema object can only have one soft delete configuration
2. **No Cascading**: Soft deletes don't automatically cascade to related records
3. **Query Complexity**: Complex queries involving soft deleted relationships may require custom SQL

## Migration from Hard Deletes

To migrate from physical deletion to soft deletes:

1. Add the soft delete column to your database table
2. Update your OpenAPI schema with the `x-af-soft-delete` configuration
3. Existing records without soft delete values are treated as active
4. Deploy the updated API specification

```sql
-- Migration example
ALTER TABLE employees ADD COLUMN deleted_at TIMESTAMP NULL;
CREATE INDEX idx_employees_not_deleted ON employees (deleted_at) WHERE deleted_at IS NULL;
```

## Troubleshooting

### Common Issues

**Issue**: Records still appearing after soft deletion
- **Solution**: Verify the soft delete column is properly indexed and the API specification is correctly configured

**Issue**: Cannot query for specific status values that are excluded
- **Solution**: Use `__include_soft_deleted=true` parameter or create a custom path operation

**Issue**: Performance degradation with soft deletes
- **Solution**: Add appropriate database indexes on soft delete columns

### Debugging

Enable debug logging to see the generated SQL:

```yaml
# In your API specification
x-af-debug: true
```

This will log the actual SQL queries being generated, including soft delete conditions.
