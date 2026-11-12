# AI-DLC: the change workflow

Reference for anyone who changes the platform: how every change is planned, approved, recorded, and turned into current design knowledge. Back to the [README](../../README.md). The history of the intents so far: [Platform evolution](../evolution.md).

AI-DLC (AI-Driven Development Life Cycle) is the platform's change component: an AI assistant does the work, following the workflow, and a person approves each stage. It is part of the repository, not a running service.

It is an adaptation of AWS's AI-DLC workflows, version 1 ([awslabs/aidlc-workflows](https://github.com/awslabs/aidlc-workflows)): the inception, construction and deploy stages, approval gates, question format and opt-in extensions come from there. The copy used here adds intent closure (`scripts/aidlc_intent.py compact`), which writes what is now true into the canonical knowledge and archives the intent, with the `aidlc-docs/current/`, `knowledge/` and `archive/` layout it relies on, and the always-on Workflow Conventions extension. Most of this adaptation was not written by the platform's author, and its source can no longer be identified.

| Part | Where | Role |
|---|---|---|
| The workflow | `.claude/skills/aidlc-workflows/` (also `.agents/skills/aidlc-workflows/`) | Stage rules, question format, content validation, and opt-in extensions |
| The open intent | `aidlc-docs/current/` | Its stage documents, `aidlc-state.md` (stage, status, follow-ups) and `audit.md` (every input and decision, timestamped) |
| Canonical knowledge | `aidlc-docs/knowledge/opensource-lakehouse-infra/` | What is true now: `application-design.md` and one functional design per component (`functional-design/*.md`) |
| History | `aidlc-docs/archive/<intent-id>/` | Each closed intent: its full artifacts and audit, and an `intent-summary.md`; archived dependency manifests are stored as `<name>.archived`, so Dependabot ignores them |
| Closing tool | `scripts/aidlc_intent.py` | `compact <intent-id> --dry-run` and `--apply`: archive, update the canonical knowledge, clear the workflow files |

## How a change goes

1. **Start an intent**: ask the assistant for the change. It detects the workspace, reverse-engineers the parts that matter, and opens `aidlc-docs/current/`.
2. **Inception**: requirements (questions as multiple choice with a recommended option), workflow planning (which stages run, and which canonical documents the change affects), and design stages when they add something.
3. **Probes**: when a design depends on behavior nobody has verified, a short, reversible experiment settles it first, with approval when it touches the live platform.
4. **Construction**: functional design, code generation (from an approved plan), and build and test (unit, live and user checks; results reported as they are).
5. **Deploy**: a handoff, a pull request description and ordered deployment steps; nothing is pushed or deployed without approval.
6. **Closure**: the assistant writes the current design into the canonical knowledge, previews the closure with `scripts/aidlc_intent.py compact <intent-id> --dry-run`, and applies it with `--apply`; the intent's record moves to `aidlc-docs/archive/<intent-id>/`.

Each stage ends with an explicit approval; changes requested in between are recorded as change requests. A person can also approve all stages in advance for a small change.

## Rules that keep it safe

- **Approvals**: no stage moves on without one; pushes and live changes need their own.
- **Extensions**: Security Baseline, property-based testing and Resiliency are opted in per intent, and their rules are then enforced at each stage.
- **Records**: the audit keeps the user's words as written; nothing secret goes into it.
- **One intent at a time** per repository; small changes in the platform (for example from a product's needs) get their own small intent.
- **Knowledge stays current**: the canonical design is updated in place at each closure; superseded decisions stay in the archive.

The data product repository (`opensource-lakehouse-sample-dp`) uses the same workflow, with its own `aidlc-docs/`.
