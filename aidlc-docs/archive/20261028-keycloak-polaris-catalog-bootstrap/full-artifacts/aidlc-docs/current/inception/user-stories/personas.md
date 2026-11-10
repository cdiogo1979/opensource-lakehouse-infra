# Personas — `default` Data Product Bootstrap

## Platform Administrator

- **Type:** Human operator with authority to run the product bootstrap.
- **Goals:** Create a data product consistently across production, dev, and UAT; verify that setup is complete; avoid manual service-by-service configuration.
- **Responsibilities:** Run the documented CLI using a protected platform-admin identity; initiate product creation; review the result.
- **Boundaries:** The platform-admin identity is distinct from Keycloak realm-admin and RustFS root. The creating operator receives product-owner membership after creating the product.

## Data Product Owner

- **Type:** Human product steward, possibly the same person as the platform administrator.
- **Goals:** Manage the data product’s objects and product-level grants across all environments.
- **Responsibilities:** Own data/catalog administration within `default` and manage product-level grants.
- **Boundaries:** Product ownership does not confer Keycloak realm administration or RustFS root access.

## Developer

- **Type:** Human user assigned to `role-default-developer`.
- **Goals:** Read product data in all environments and develop/write in the dev environment.
- **Responsibilities:** Use authorized catalog and object-store access for development work.
- **Boundaries:** Can write only to dev; cannot administer product grants or write production/UAT.

## Analyst

- **Type:** Human user assigned to `role-default-analyst`.
- **Goals:** Read production data for analysis.
- **Responsibilities:** Query/read production catalog data and corresponding objects.
- **Boundaries:** No dev/UAT access and no writes in any environment.

## Automated Writer

- **Type:** Non-interactive service identity assigned to `role-default-writer`.
- **Goals:** Execute authorized Spark/bootstrap writes across all three environments.
- **Responsibilities:** Obtain service OAuth credentials and read/write product data through the approved catalog and object-store interfaces.
- **Boundaries:** Not a human login, Keycloak realm administrator, or RustFS root identity. Credentials are protected and never printed.
