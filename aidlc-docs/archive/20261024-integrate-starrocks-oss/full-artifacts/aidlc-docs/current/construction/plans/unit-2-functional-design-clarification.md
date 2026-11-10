# Unit 2 Functional Design Clarification

## Ambiguity — First startup versus missing persistent state

Your answer to Question 2 in `unit-2-functional-design-plan.md` selected failing startup when an FE or BE volume is missing, invalid, or incompatible, while preserving state. A new StarRocks deployment also begins with empty FE and BE volumes, so the design needs to distinguish legitimate first initialization from a later missing or damaged volume.

### Clarification Question 1

How should a normal first startup with empty FE/BE volumes work?

A) Initialize both nodes when both volumes are empty on first startup; fail and preserve data if only one side is unexpectedly empty or if existing state is invalid/incompatible.

B) Require a separate explicit operator initialization step for empty volumes; normal runtime startup must not initialize them.

C) Initialize any empty FE or BE volume automatically, including when its peer already has persisted state.

D) Other (please describe after `[Answer]:` below)

[Answer]: A
