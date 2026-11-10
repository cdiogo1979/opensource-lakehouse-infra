# Functional Design Plan — ldap-password-login

## Plan
- [x] Read the requirements, application design, and canonical baselines
- [x] Collect answers (FD-Q1, FD-Q2)
- [x] Generate domain-entities.md, business-rules.md, business-logic-model.md
- [x] Identify properties (PBT-01, advisory in partial mode) and record the framework (PBT-09)

## Questions

### FD-Q1 Disabled local users
A) Migrate as disabled (Recommended)
B) Skip them and keep them local
X) Other

[Answer]: A

### FD-Q2 Old Jupyter home volume and old Hub user after a migrated user's copy
A) Keep and report the cleanup commands (Recommended)
B) Delete after the copy is verified
X) Other

[Answer]: B
