# Batch Operations - `batch_path` Parameter Implementation

## Overview

The `batch_path` parameter enables automatic batch operations support in API Foundry with a single configuration parameter. When set, it generates a complete batch operations endpoint with dependency resolution, reference substitution, and transaction management.

## What Was Implemented

### 1. API Foundry Infrastructure (`api_foundry` workspace)

#### A. APIFoundry Class (`api_foundry/iac/pulumi/api_foundry.py`)
**Change**: Added `batch_path` parameter to `__init__()`

```python
def __init__(
    self,
    name,
    *,
    api_spec: Union[str, list[str]],
    batch_path: Optional[str] = None,  # NEW: Optional batch endpoint path
    secrets: Optional[str] = None,
    # ... other params
):
    # ... Pass to APISpecEditor
    gateway_spec = APISpecEditor(
        open_api_spec=api_spec_dict,
        function=self.api_function,
        batch_path=batch_path  # Pass batch_path
    )
```

**Impact**: Users can now enable batch operations with one parameter

#### B. APISpecEditor Class (`api_foundry/iac/gateway_spec.py`)
**Changes**:
1. Added `batch_path` instance variable
2. Modified `rest_api_spec()` to conditionally generate batch endpoint
3. Created `generate_batch_operation()` method

**Key Features**:
- Generates `/batch` POST endpoint (or custom path)
- Adds 5 component schemas: `BatchRequest`, `BatchOperation`, `BatchResponse`, `OperationError`, `ErrorResponse`
- Includes full OpenAPI documentation with examples
- Only activates when `batch_path` is set (opt-in design)

```python
def rest_api_spec(self) -> str:
    # ... existing schema generation ...

    # NEW: Generate batch operation endpoint if batch_path is specified
    if self.batch_path:
        self.generate_batch_operation(self.batch_path)

    # ... continue with spec finalization
```

### 2. Query Engine Runtime (`api_foundry_query_engine` workspace)

#### A. OperationDAO (`dao/operation_dao.py`)
**Change**: Added batch operation detection and routing in `execute()` method

```python
def execute(self, connector, operation=None):
    op = operation if operation is not None else self.operation

    # NEW: Check if this is a batch operation
    if op.entity == "batch" and op.action == "create":
        from api_foundry_query_engine.dao.batch_operation_handler import (
            BatchOperationHandler,
        )

        batch_request = op.store_params
        handler = BatchOperationHandler(
            batch_request, connector, self.engine
        )
        return handler.execute()

    # Continue with standard operations...
```

**Impact**: Batch requests are automatically routed to BatchOperationHandler

#### B. GatewayAdapter (`adapters/gateway_adapter.py`)
**Change**: Added batch request unmarshalling in `unmarshal()` method

```python
def unmarshal(self, event):
    # ... extract entity, method, claims ...

    # NEW: Handle batch requests
    if entity == "batch" and method == "POST":
        body = event.get("body")
        if body:
            batch_request = json.loads(body)
            return Operation(
                entity="batch",
                action="create",
                store_params=batch_request,
                claims=claims,
            )

    # Continue with standard unmarshalling...
```

**Impact**: Batch requests from API Gateway are properly parsed

## Usage

### Basic Usage (Enable Batch Operations)

```python
from api_foundry import APIFoundry

api = APIFoundry(
    "my-api",
    api_spec="chinook_api.yaml",
    secrets=secrets_json,
    batch_path="/batch"  # ← Enables batch operations at /batch
)
```

This single parameter:
- ✅ Generates `/batch` POST endpoint in OpenAPI spec
- ✅ Adds all 5 batch component schemas
- ✅ Routes batch requests to BatchOperationHandler
- ✅ Enables dependency resolution and reference substitution
- ✅ Provides atomic transaction support

### Custom Path

```python
api = APIFoundry(
    "my-api",
    api_spec="chinook_api.yaml",
    batch_path="/operations/bulk"  # Custom batch endpoint
)
```

### Without Batch Support (Default)

```python
api = APIFoundry(
    "my-api",
    api_spec="chinook_api.yaml"
    # No batch_path = No batch endpoint generated
)
```

## Generated OpenAPI Specification

When `batch_path="/batch"` is set, the following is automatically added to your API spec:

### Endpoint

```yaml
paths:
  /batch:
    post:
      summary: Execute batch operations
      description: Execute multiple database operations in a single request with
        dependency resolution and transaction management.
      tags:
        - Batch Operations
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/BatchRequest'
      responses:
        '200':
          description: Batch execution completed
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/BatchResponse'
        '400':
          description: Invalid batch request
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
```

### Component Schemas

Five schemas are automatically added:

1. **BatchRequest** - Request body with operations array and options
2. **BatchOperation** - Individual operation spec with id, entity, action, params, dependencies
3. **BatchResponse** - Response with success flag, results map, and errors
4. **OperationError** - Error details for failed operations
5. **ErrorResponse** - General error response

See `batch_operations.md` for full schema definitions.

## Example Request

```bash
POST /batch
Content-Type: application/json
Authorization: Bearer <token>

{
  "operations": [
    {
      "id": "create_invoice",
      "entity": "invoice",
      "action": "create",
      "store_params": {
        "customer_id": 5,
        "invoice_date": "2024-01-01",
        "total": 2.97
      }
    },
    {
      "id": "create_line_1",
      "entity": "invoice_line",
      "action": "create",
      "store_params": {
        "invoice_id": "$ref:create_invoice.invoice_id",
        "track_id": 1,
        "unit_price": 0.99,
        "quantity": 1
      },
      "depends_on": ["create_invoice"]
    }
  ],
  "options": {
    "atomic": true,
    "continueOnError": false
  }
}
```

## Testing

### Unit Tests

A standalone test suite verifies the implementation:

```bash
python test_batch_standalone.py
```

**Test Coverage**:
- ✅ `batch_path` generates `/batch` endpoint with all schemas
- ✅ Without `batch_path`, no batch endpoint is generated
- ✅ Custom paths work correctly (e.g., `/operations/bulk`)
- ✅ All 5 component schemas are properly structured
- ✅ Required fields are enforced

### Integration Tests

See `api_foundry_query_engine/tests/test_batch_operations.py` for end-to-end tests including:
- Invoice creation with line items
- Dependency resolution
- Reference substitution
- Atomic transactions
- Error handling

## Architecture Benefits

### 1. Opt-In Design
- Zero impact if not used
- No breaking changes to existing APIs
- Simple activation with one parameter

### 2. Clean Separation
- **API Foundry**: Handles OpenAPI spec generation and deployment
- **Query Engine**: Handles runtime execution and business logic
- **Gateway**: Routes batch requests to appropriate handler

### 3. Consistent Patterns
- Follows same patterns as CRUD operations
- Inherits JWT authentication automatically
- Uses same permission model
- Integrates with existing transaction management

### 4. Flexible Configuration
- Custom endpoint paths
- Works with any schema objects in spec
- Supports all existing database configurations

## Files Modified

### `api_foundry` Workspace
1. `api_foundry/iac/pulumi/api_foundry.py` - Added `batch_path` parameter (2 lines)
2. `api_foundry/iac/gateway_spec.py` - Added batch endpoint generation (183 lines)
3. `tests/test_batch_path_integration.py` - Unit tests (NEW, 158 lines)
4. `test_batch_standalone.py` - Standalone verification (NEW, 202 lines)

### `api_foundry_query_engine` Workspace
1. `dao/operation_dao.py` - Added batch routing (14 lines)
2. `adapters/gateway_adapter.py` - Added batch unmarshalling (38 lines)

**Total**: ~597 lines of code across 6 files

## Next Steps

1. ✅ **Implementation Complete** - All integration points working
2. ✅ **Tests Passing** - Unit tests verify spec generation
3. ⏳ **Documentation** - Update main README with batch_path usage
4. ⏳ **Examples** - Add batch operation examples to `resources/`
5. ⏳ **Production Testing** - Deploy to staging and verify end-to-end

## Troubleshooting

### Batch endpoint not appearing in API
**Cause**: `batch_path` not set
**Fix**: Add `batch_path="/batch"` to APIFoundry initialization

### Batch requests returning 404
**Cause**: API Gateway routing not updated
**Fix**: Redeploy the API after adding `batch_path`

### Batch operations failing with "Unknown entity"
**Cause**: Entity names in batch operations don't match schema objects
**Fix**: Verify entity names match exactly (case-sensitive)

### Import errors with BatchOperationHandler
**Cause**: Query engine not installed or outdated
**Fix**: Ensure `api_foundry_query_engine` is in requirements and up to date

## Summary

The `batch_path` parameter provides a **clean, opt-in way** to enable powerful batch operations in API Foundry. With a single configuration line, users get:

- Complete batch operations endpoint
- Automatic dependency resolution
- Reference substitution with `$ref:` syntax
- Atomic transaction support
- Full OpenAPI documentation
- JWT authentication integration

This implementation maintains API Foundry's philosophy of **convention over configuration** while providing flexibility for advanced use cases.
