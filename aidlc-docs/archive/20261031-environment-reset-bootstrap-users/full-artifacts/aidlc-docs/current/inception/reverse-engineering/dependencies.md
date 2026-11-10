# Dependencies — Reset and Identity Bootstrap

```mermaid
flowchart TD
    Reset[reset command] --> Docker[Docker volumes, containers, networks]
    Reset --> Runtime[.runtime credentials and mounts]
    Start[lakehouse.sh start] --> Runtime
    Start --> Realm[bootstrap-realm.py]
    Realm --> Keycloak[keycloak]
    Product[bootstrap-default-product.sh] --> Reconcile[Polaris group reconciliation]
    Reconcile --> Keycloak
```

Text alternative: the reset touches Docker state and runtime files. Start recreates the runtime files and runs the realm bootstrap, where the users would be created. Product bootstrap reconciles Polaris principals from Keycloak groups.
