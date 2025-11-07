# Property Value Injection

API Foundry supports automatic injection of property values from JWT claims and other sources using the `x-af-inject-value` and `x-af-inject-on` attributes.

## Overview

Property value injection allows you to automatically populate field values without requiring them in the request body. This is particularly useful for:

- **Audit fields**: `created_by`, `updated_by`, `created_at`, `updated_at`
- **Multi-tenancy**: `tenant_id`, `organization_id`
- **User context**: `owner_id`, `user_email`
- **Tracking**: `record_version`, `correlation_id`

## Attributes

### `x-af-inject-value`

Specifies the source of the value to inject. Supported sources:

| Source Pattern | Description | Example |
|---------------|-------------|---------|
| `claim:<key>` | Extract from JWT token claims | `claim:sub`, `claim:tenant`, `claim:email` |
| `timestamp` | Current UTC timestamp (ISO 8601) | `2024-11-06T14:30:00.000Z` |
| `date` | Current UTC date (ISO 8601) | `2024-11-06` |
| `uuid` | Generate a new UUID v4 | `550e8400-e29b-41d4-a716-446655440000` |
| `env:<key>` | Environment variable value | `env:REGION`, `env:APP_VERSION` |

### `x-af-inject-on`

Specifies when to inject the value. Can be an array containing:

- `create` - Inject only on INSERT operations
- `update` - Inject only on UPDATE operations

**Default behavior** (if `x-af-inject-on` is omitted):
- Properties starting with `created_`: default to `["create"]`
- Properties starting with `updated_`: default to `["update"]`
- Properties ending with `_by` or `_at`: default to `["create"]`
- Tenant/owner fields (`tenant_id`, `owner_id`, etc.): default to `["create"]`
- All other properties: default to `["create"]`

## Examples

### Audit Tracking

```yaml
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
        
        # WHO created the record (immutable)
        created_by:
          type: string
          x-af-inject-value: "claim:sub"
          # x-af-inject-on: ["create"]  # Inferred from property name
        
        # WHEN was it created (immutable)
        created_at:
          type: string
          format: date-time
          x-af-inject-value: "timestamp"
          # x-af-inject-on: ["create"]  # Inferred from property name
        
        # WHO last updated (changes on every update)
        updated_by:
          type: string
          x-af-inject-value: "claim:sub"
          x-af-inject-on: ["update"]  # Only on updates
        
        # WHEN was it last updated (changes on every update)
        updated_at:
          type: string
          format: date-time
          x-af-inject-value: "timestamp"
          x-af-inject-on: ["update"]  # Only on updates
```

### Multi-Tenant Isolation

```yaml
components:
  schemas:
    document:
      type: object
      x-af-database: app
      properties:
        id:
          type: integer
          x-af-primary-key: auto
        title:
          type: string
        content:
          type: string
        
        # Tenant ID is auto-injected and immutable
        tenant_id:
          type: string
          required: true
          x-af-inject-value: "claim:tenant"
          # x-af-inject-on: ["create"]  # Inferred from property name
      
      # Combine with permissions for row-level security
      x-af-permissions:
        default:
          read:
            user:
              properties: ".*"
              where: "tenant_id = ${claims.tenant}"
          write:
            user:
              properties: "title|content"  # tenant_id NOT writable
              where: "tenant_id = ${claims.tenant}"
```

### Ownership Tracking

```yaml
components:
  schemas:
    project:
      type: object
      x-af-database: app
      properties:
        id:
          type: integer
          x-af-primary-key: auto
        name:
          type: string
        
        # Owner is set on creation and cannot be changed
        owner_id:
          type: string
          required: true
          x-af-inject-value: "claim:sub"
          # x-af-inject-on: ["create"]  # Inferred from property name
        
        # Owner's email for reference
        owner_email:
          type: string
          x-af-inject-value: "claim:email"
          x-af-inject-on: ["create"]
```

### Versioning and Correlation

```yaml
components:
  schemas:
    order:
      type: object
      x-af-database: app
      properties:
        id:
          type: integer
          x-af-primary-key: auto
        
        # Generate new UUID on every change for tracking
        version_id:
          type: string
          format: uuid
          x-af-inject-value: "uuid"
          x-af-inject-on: ["create", "update"]  # Both operations
        
        # Track deployment environment
        environment:
          type: string
          x-af-inject-value: "env:ENVIRONMENT"
          x-af-inject-on: ["create"]
```

## Security Considerations

### Injected Properties are Immutable by Users

Properties with `x-af-inject-value` **cannot be set by users** in request bodies:

```bash
# ❌ This will fail with 403 Forbidden
POST /album
{
  "title": "New Album",
  "created_by": "hacker"  # Error: Property is auto-injected
}

# ✅ This works - created_by is auto-populated from JWT
POST /album
{
  "title": "New Album"
}
```

### Combine with Permissions for Defense-in-Depth

Use `x-af-inject-value` for **value injection** and `x-af-permissions` with `where` clauses for **row-level filtering**:

```yaml
tenant_id:
  type: string
  x-af-inject-value: "claim:tenant"  # Auto-injected on create

x-af-permissions:
  default:
    read:
      user:
        properties: ".*"
        where: "tenant_id = ${claims.tenant}"  # RLS filtering
    write:
      user:
        properties: "title|content"  # Exclude tenant_id
        where: "tenant_id = ${claims.tenant}"
```

This provides:
1. **Injection**: `tenant_id` is automatically set from claims on CREATE
2. **Exclusion**: Users cannot write to `tenant_id` (not in write properties)
3. **Filtering**: All operations automatically filter by the user's tenant

## API Behavior

### On CREATE (POST)

```bash
POST /album
Authorization: Bearer <token with sub="user123">
Content-Type: application/json

{
  "title": "Dark Side of the Moon"
}
```

**Result**: Record inserted with:
```json
{
  "album_id": 1,
  "title": "Dark Side of the Moon",
  "created_by": "user123",           // Injected from claim:sub
  "created_at": "2024-11-06T14:30:00Z", // Injected from timestamp
  "updated_by": null,                // Not injected on create
  "updated_at": null                 // Not injected on create
}
```

### On UPDATE (PUT)

```bash
PUT /album/1
Authorization: Bearer <token with sub="user456">
Content-Type: application/json

{
  "title": "Dark Side of the Moon (Remastered)"
}
```

**Result**: Record updated with:
```json
{
  "album_id": 1,
  "title": "Dark Side of the Moon (Remastered)",
  "created_by": "user123",           // Unchanged (not injected on update)
  "created_at": "2024-11-06T14:30:00Z", // Unchanged
  "updated_by": "user456",           // Injected from claim:sub
  "updated_at": "2024-11-06T15:45:00Z"  // Injected from timestamp
}
```

## Error Handling

### Missing Required Claim

If a `required` property's injection source is not available:

```yaml
tenant_id:
  type: string
  required: true
  x-af-inject-value: "claim:tenant"
```

**Without `tenant` claim in JWT**:
```
HTTP 400 Bad Request
{
  "error": "Required injected property 'tenant_id' could not be populated from 'claim:tenant'"
}
```

### User Attempts to Override

```
HTTP 403 Forbidden
{
  "error": "Property 'created_by' is auto-injected and cannot be set manually"
}
```

## Best Practices

1. **Use Naming Conventions**: Follow `created_*` and `updated_*` patterns for automatic inference
2. **Make Audit Fields Optional**: Don't require `updated_by` or `updated_at` since they're null on creation
3. **Combine with Permissions**: Use permissions to exclude injected fields from write operations
4. **Document Injected Fields**: Add descriptions indicating fields are auto-populated
5. **Test with Different Tokens**: Verify injection works with various claim combinations

## Migration from Manual Fields

If you have existing tables with audit fields that users currently populate:

1. Add `x-af-inject-value` to the schema
2. Exclude these fields from write permissions
3. Existing records will be unaffected
4. New/updated records will use injected values

```yaml
# Before: Users provide created_by
created_by:
  type: string

# After: API populates created_by
created_by:
  type: string
  x-af-inject-value: "claim:sub"
  
# And exclude from write permissions
x-af-permissions:
  default:
    write:
      user: "^(?!created_by|updated_by).*"  # Exclude audit fields
```
