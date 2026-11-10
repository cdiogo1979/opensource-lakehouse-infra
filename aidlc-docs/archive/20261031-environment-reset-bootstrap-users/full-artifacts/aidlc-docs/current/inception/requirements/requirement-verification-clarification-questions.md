# Requirements Clarification Questions — Environment Reset and Bootstrap Users

## Ambiguity 1: When user defaults are enforced (Q5: A, Q6: Other)
You want the user bootstrap to reset passwords and group assignments to the defaults when it runs again. `bootstrap-realm.py` runs on every `scripts/lakehouse.sh start`. If enforcement lives there, every routine start would reset all bootstrap users' passwords to `ChangeM3!` and their groups to the defaults, undoing any password change.

### Clarification Question 1
When should the enforcing user bootstrap run?

A) As a separate explicit step, `scripts/bootstrap-users.sh`, which `bootstrap-default-product.sh` runs after a reset. A routine `lakehouse.sh start` never resets passwords or groups. Running the explicit step again re-applies the default passwords and exact group assignments (Recommended)

B) On every `lakehouse.sh start`: passwords and groups are reset to the defaults at each start

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Ambiguity 2: Replacing `write-service-account` (Q7: B)
Airflow's writer token broker and the Spark workloads authenticate to Polaris as the `write-service-account` client (client-credentials grant). They receive writer rights because that client's service-account user belongs to `role-default-writer`. Removing that membership stops Airflow and Spark from writing, unless the workloads move to another identity. A password user cannot use the client-credentials flow, so moving them would mean new client and broker changes.

### Clarification Question 2
How should the writer identities work?

A) Keep `write-service-account` in `role-default-writer` for Airflow and Spark, and add `srv-default-writer` as the password user for the writer role (Recommended)

B) Remove `write-service-account` from the group and migrate Airflow and Spark to `srv-default-writer`. This is a large scope change: a password grant client, broker and Spark adapter changes, and a weaker credential type

C) Remove the membership and accept that Airflow and Spark writes break until a later intent

X) Other (please describe after [Answer]: tag below)

[Answer]: B

## Ambiguity 3: Interactive confirmation and automated runs (Q4: B, Q9: A)
The reset asks the operator to type `reset`. Build and Test must also run it non-interactively.

### Clarification Question 3
How should non-interactive runs confirm?

A) Interactive prompt by default, plus an explicit `--yes` flag for non-interactive use. Both print the full inventory first, and `--dry-run` changes nothing (Recommended)

B) Prompt only; automated runs pipe `reset` into standard input

X) Other (please describe after [Answer]: tag below)

[Answer]: A
