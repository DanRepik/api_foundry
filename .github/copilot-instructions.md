# AI Coding Agent Instructions for API Foundry

API Foundry converts OpenAPI specs with custom `x-af-*` attributes into AWS REST APIs with auto-generated CRUD operations and database integration.

## Core Architecture
- **Main orchestrator**: `api_foundry/iac/pulumi/api_foundry.py` (APIFoundry Pulumi component)
- **OpenAPI processor**: `api_foundry/iac/gateway_spec.py` transforms specs for AWS API Gateway
- **Database mapper**: `api_foundry/utils/model_factory.py` converts schemas to DB models
- **Scripts**: `api_foundry/scripts/` contains `install_secret` and `postgres_to_openapi` utilities

## Essential Development Commands
```bash
source dev_helpers.sh    # Load aliases (infra_up, up, down)
infra_up                 # Start PostgreSQL + create secrets
up                       # Deploy API to LocalStack
pytest -m unit          # Unit tests (no DB)
pytest -m integration   # Integration tests (requires DB)
```

## Critical OpenAPI Patterns
Schema objects auto-generate 7 REST endpoints when annotated:
```yaml
components:
  schemas:
    album:
      type: object
      x-af-database: chinook          # Required: DB connection name
      x-af-primary-key: auto          # Key strategy: auto|manual|uuid|sequence
      x-af-concurrency-control: version  # Optional: optimistic locking
```

## Database Integration
- **Secrets**: Use `install_secret` script to create AWS Secrets Manager entries
- **Deployment**: `APIFoundry("name", api_spec="spec.yaml", secrets=json.dumps({"db": "secret_arn"}))`
- **Relationships**: `x-af-parent-property` (1:1), `x-af-child-property` (1:many)

## Testing Infrastructure
- Uses `fixture_foundry` for Docker orchestration (PostgreSQL, LocalStack)
- Database fixtures in `tests/conftest.py` handle DDL loading via `exec_sql_file()`
- Key fixtures: `chinook_db`, `chinook_api_endpoint`
- Transform URLs with `to_localstack_url()` for LocalStack testing
- Test data loaded from `tests/Chinook_Postgres.sql`

## File Navigation
- **Core logic**: `api_foundry/iac/`, `api_foundry/utils/`
- **Examples**: `resources/` directory
- **Generated code**: `temp/` directories
- **Tests**: `tests/` with integration fixtures and Chinook test data

## Security
Role-based access via JWT tokens with `x-af-permissions` on schema objects and standard OpenAPI `security` on path operations.

### Permission System
- **Structure**: provider → action → role → rule hierarchy
- **Actions**: `read`, `write` (normalized from create/update), `delete`
- **Formats**:
  - Concise: `read: "property1|property2"` for simple property filtering
  - Verbose: `read: {properties: "regex", where: "SQL_condition"}` for row-level security
- **Claim Templating**: WHERE clauses support `${claims.property}` substitution
- **Backward Compatibility**: Legacy role-first format automatically normalized
