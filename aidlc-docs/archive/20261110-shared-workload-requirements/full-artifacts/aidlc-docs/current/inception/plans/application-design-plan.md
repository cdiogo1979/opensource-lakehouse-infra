# Application Design Plan — Shared Workload Requirements

## Steps
- [x] Probes in throwaway containers (results in `application-design/application-design.md`, "Probe results")
- [x] Generate components.md
- [x] Generate component-methods.md
- [x] Generate services.md
- [x] Generate component-dependency.md
- [x] Consolidate in application-design.md
- [x] Validate completeness and consistency against FR-1 to FR-8, CR-1 and CR-2

## Questions
Asked interactively on 2026-11-10. The probes settled the other design choices; they are recorded as decisions with their evidence.

### Q1 Product extras: prebuilt wheels only?
A) Wheels only: CI, `install_requirements` and the Jupyter command all use `--only-binary=:all:`; a package without an aarch64 wheel for glibc 2.31 or older fails CI with a clear message (Recommended)

B) Allow source builds

X) Other

[Answer]: A
