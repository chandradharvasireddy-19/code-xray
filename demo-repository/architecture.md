# System Architecture & Layering Policy

## Architectural Layers & Allowed Flows

The system strictly enforces a layered architecture:

`Controller -> Service -> Repository`

### Rules
1. **Controllers** handle HTTP requests, input validation, and route parameters. Controllers must delegate business logic to Services.
2. **Controllers must NOT directly import or call Repositories.** Direct database access from the controller layer is strictly prohibited.
3. **Services** contain core business logic, orchestrate authentication, and call Repositories.
4. **Repositories** encapsulate data persistence and database operations.
5. **Auth & Validation** components are consumed exclusively by Services.
