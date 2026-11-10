# Functional Design Plan — data-product-provisioning

## Plan
- [x] Read the approved requirements (incl. CR-1), application design, and the canonical baselines (`lakehouse-product-access.md`, `starrocks-sql-access.md`, `jenkins-ci-access.md`)
- [x] Check workloads for namespace creation (none in the repository use it)
- [x] Collect answers (FD-Q1..Q3)
- [x] Generate `domain-entities.md`
- [x] Generate `business-rules.md`
- [x] Generate `business-logic-model.md`

## Questions

### FD-Q1 Namespace creation by product roles
A) None: each product has exactly the three namespaces in its file (Recommended)
B) Owner and writer may create nested namespaces in their product namespace
X) Other

[Answer]: A

### FD-Q2 Removal while groups have members
A) Proceed; the confirmation lists the members who lose access (Recommended)
B) Refuse until the groups are empty
X) Other

[Answer]: A

### FD-Q3 Grants on managed roles that no file describes
A) Revoke and report, in Polaris and StarRocks; unmanaged roles are never touched (Recommended)
B) Refuse and report
X) Other

[Answer]: A
