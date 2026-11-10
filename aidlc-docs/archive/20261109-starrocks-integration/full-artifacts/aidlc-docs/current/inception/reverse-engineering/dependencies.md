# Dependencies

| From | To | Kind | Notes |
|---|---|---|---|
| StarRocks FE/BE | Polaris | Iceberg REST, OAuth2 | Needs a catalog identity, or per-user pass-through if supported |
| StarRocks BE (and FE for planning) | RustFS | S3 | Vended credentials from Polaris, or a dedicated read key with a RustFS policy |
| StarRocks FE | Keycloak | User authentication (option) | JWT/OAuth2 security integration, or none (native users) |
| Product bootstrap | StarRocks FE | SQL DDL | Create catalogs, roles, grants |
| Reset | StarRocks volumes and networks | Delete | Inventory to extend |
| `realm-contract.json` | StarRocks client | Keycloak client | New client if OAuth2/JWT is used |
