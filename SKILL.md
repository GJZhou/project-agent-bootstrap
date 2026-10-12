---
name: project-agent-bootstrap
description: Create or refresh a project's root AGENTS.md, first-level directory overview, docs inventory, progress.md, and local Git rules, with bounded analysis and rule inheritance for explicitly linked external workspaces.
---

# Project Agent Bootstrap

Use this skill when the user asks to create or maintain project-level agent guidance, project progress tracking, or the associated documentation inventory. It is also available explicitly as `$project-agent-bootstrap`.

Every run has two separate phases. Complete the documentation phase even when the project is not a Git repository or the requirement number is empty; only the commit phase depends on Git and a configured requirement number.

The current project root is the default write boundary. An explicitly registered external workspace is a separate project boundary: inspect it only within the limits in [workspace-boundaries.md](references/workspace-boundaries.md), and edit it only when the current task explicitly includes that workspace.

## Workflow

### Phase A: always refresh project guidance

1. Resolve the existing rule file for the current root. Prefer `AGENTS.md`; also recognize an existing `agents.md` or `agent.md`. If more than one candidate exists, report the conflict and ask the user which file is authoritative before writing.
2. Read [workspace-boundaries.md](references/workspace-boundaries.md). Inspect only explicitly registered or user-provided external workspaces. For each one, determine whether it has one, none, or multiple root-level rule-file candidates, and collect a bounded first-level project summary. Do not write to an external workspace during this inspection.
3. Inspect the current project root, README files, build manifests, top-level module metadata, `progress.md`, `docs/`, and `.gitignore`. Enumerate only the root's immediate children. Preserve user-owned content.
4. Refresh the managed section of the current root rule file using [agent-file-contract.md](references/agent-file-contract.md). If an older file has no markers, migrate its required sections into the managed block first. Record the external workspace status in the managed association section without copying external rules into the current root.
5. Create or refresh the current root `docs/文档清单.md` and `progress.md` using [docs-and-progress.md](references/docs-and-progress.md). User-configured version and requirement fields must remain unchanged.
6. If the current task explicitly includes edits under an external workspace, group those files by workspace, resolve that workspace's rule authority, and apply [workspace-boundaries.md](references/workspace-boundaries.md) before editing. A workspace with its own rule file follows that file; a workspace without one inherits the current root rules. Maintain its own progress and document records when required, and keep its Git changes separate.
7. If the managed output is already current, report that it was checked and unchanged; never skip the refresh merely because the files already exist or are ignored by Git.

### Phase B: conditional local commit

8. Apply [project-management.md](references/project-management.md) and [git-policy.md](references/git-policy.md) to classify non-document changes and decide whether a local commit is allowed independently for each modified project root.
9. Only in a Git root with a configured requirement number and non-document changes, stage only that root's current batch and create its required local commit. Do not combine parent and external workspace files in one commit. For a non-Git root, an actual documentation-sync record may use `N/A（非 Git 项目）`; do not invent a commit for code changes.
10. After a successful commit, append the commit record to the `progress.md` belonging to the same project root and current version. Do not write an external workspace commit into the parent project's progress file.
11. Run `scripts/validate_project_agent.py --root <project-root>` and report unresolved “待补充” facts, external workspace statuses, updated files by root, unchanged managed content, and any uncommitted non-document files.

## Boundaries

- Enumerate at most one directory level. For module purposes, inspect only targeted README, manifest, module descriptor, or obvious entry metadata; do not scan all source files.
- External workspace inspection is read-only by default and limited to the workspace root, its rule-file candidates, README/build metadata, first-level children, `docs/`, `progress.md`, and `.gitignore`. Do not discover or modify arbitrary sibling directories.
- A unique external rule file governs edits inside that workspace. If none exists, inherit the current root rules. A missing external rule file does not by itself require creating one.
- If an external workspace has multiple rule-file candidates, pause work for that workspace and request a primary file; do not merge candidates.
- `ADD` means a new capability; `MOD` means an iteration or change to an existing capability. A mixed non-document batch uses `MOD`.
- A non-Git project never needs a requirement number for guidance or documentation maintenance.
- Parent and external workspace progress files, document inventories, and commits are independent. The parent progress file records only parent-root changes.
- Remote Git operations always require explicit user confirmation. Do not push, pull, fetch, clone, alter remotes, or change upstream tracking as part of this skill.

## Completion criteria

The task is complete only when the current root rule file, `progress.md`, `docs/文档清单.md`, and required `.gitignore` entries have been checked and refreshed as needed; every explicitly linked workspace has a reported rule-source status; any authorized external edits have been maintained under the correct rule source and project root; managed blocks are valid; each root's conditional commit outcome is reported; and the validator passes or its findings are listed.
