# Build and Test Summary — Unit 1

## Build status

- Docker BuildKit, Docker Compose V2, and Python 3.14.7 were used.
- Both images built: `local/lakehouse-jupyterhub:6.1.1` and `local/lakehouse-jupyter-singleuser:6.1.1-spark`.
- Compose validation, Python compilation, Bash syntax, and Keycloak realm JSON validation passed.
- The complete transitive Hub dependency lock remains outstanding; image build success does not prove a fully reproducible dependency supply chain.

## Tests and gaps

- 20 focused source tests passed; coverage was not measured.
- Live integration, performance, E2E, and vulnerability scanning were not run at that stage.
- On 2026-10-28 the user explicitly accepted the incomplete Unit 1 verification scope to continue. This was a Unit 1 verification waiver only; those checks were not treated as passed, and it did not waive Unit 2–4 evidence.
- The original Unit 1 summary recorded intermittent Docker API denial and host DNS restrictions during the dependency-lock attempt.
