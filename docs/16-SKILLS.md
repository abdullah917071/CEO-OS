# Skills

Tools are primitives; skills are versioned procedures that coordinate tools toward repeatable outcomes. A skill package contains `SKILL.md`, metadata, workflow definition, scripts, tests, examples, ownership, version, required capabilities, permissions, and success metrics.

Skills run through the normal task, permission, evidence, and audit layers. They cannot grant themselves new authority. Changes create a new version and pass sandbox/evaluation checks before promotion; rollback selects a previously verified version.

Later teaching mode can observe an owner workflow and propose a skill, but observation data remains untrusted and generated procedures require review. Self-improvement may propose and test changes but never silently rewrite production core logic.

The skills engine is Milestone 18; Phase 1 reserves the package boundary only.

