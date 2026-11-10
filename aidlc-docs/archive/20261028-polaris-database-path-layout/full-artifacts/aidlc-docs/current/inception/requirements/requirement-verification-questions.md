# Requirements Verification Questions

The requested catalog names are `lakehouse`, `lakehouse_uat`, and `lakehouse_dev`. The requested table layout is `<bucket>/<catalog>/<database>/<table>`, with each segment appearing once. Please answer the remaining requirements and extension questions.

## Question 1: Security Baseline
Should security extension rules be enforced for this project?

A) Yes — enforce all SECURITY rules as blocking constraints (recommended for production-grade applications)

B) No — skip all SECURITY rules (suitable for PoCs, prototypes, and experimental projects)

X) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 2: Property-Based Testing
Should property-based testing rules be enforced for this project?

A) Yes — enforce PBT rules (recommended for data-path construction and normalization logic)

B) Partial — enforce PBT rules only for pure functions and serialization round-trips

C) No — skip PBT rules

X) Other (please describe after [Answer]: tag below)

[Answer]: C

## Question 3: Resiliency Baseline
Should the resiliency baseline be applied to this project as directional design-time guidance?

A) Yes — apply the resiliency baseline

B) No — skip the resiliency baseline

X) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 4: Database names
Which database/namespace name should each catalog use?

A) Use `default` in each catalog (`lakehouse.default`, `lakehouse_uat.default`, and `lakehouse_dev.default`) — recommended for a consistent default database name across environments

B) Keep the existing environment-specific names (`default_lh`, `default_lhuat`, and `default_lhdev`)

C) Use another database name or mapping

X) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 5: Existing bucket contents
The new target paths differ from the current layout. Which data cleanup scope do you authorize before recreating the Polaris objects?

A) Delete only the existing Polaris catalogs/namespaces/tables and the relevant old product prefixes in the three configured buckets; preserve unrelated bucket objects — recommended

B) Empty all three configured buckets, then recreate the catalogs/namespaces/tables

C) Drop and recreate Polaris metadata only; preserve every existing bucket object

X) Other (please describe after [Answer]: tag below)

[Answer]: B
