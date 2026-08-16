# Milestone 9 — Multi-agent Runtime Execution Plan

`PLANS.md` remains the immutable governing roadmap. This file defines the concrete delivery and
acceptance contract for its multi-agent runtime milestone.

Status: implemented and verified on 2026-08-15.

## Verification result

- The full suite passed with 55 tests, including restart persistence, template permission/budget
  bounds, parallel execution, ordered synthesis, messaging, pause/resume/clone/termination, timeout,
  cost overrun, active cancellation, API lifecycle, and CEO delegation.
- Strict typing passed across 45 Python source files; Python lint, dashboard tests/type checks,
  production Next.js build, and Compose validation passed.
- A live container request matching the roadmap acceptance created four temporary research workers,
  processed ten fixture competitors concurrently, returned ten evidence entries, synthesized ten
  ordered results in 95 ms, recorded ten cost units, and terminated all temporary workers.
- Every result was labeled `simulation` and included the uncertainty that no live market sources
  were queried.
- PostgreSQL and Redis were ready, the Agents dashboard returned HTTP 200, and agent/assignment
  records remained available after an API container restart.

## Objective

Add a durable, bounded agent workforce behind contracts owned by CEO OS. CEO delegates structured
assignments; workers receive scoped context and return evidence-bearing results. Provider-specific
research, communication, and business logic remain outside the orchestration kernel.

## Acceptance criteria

- A persistent registry stores permanent and temporary agents, parent relationships, role, template
  version, allowed capabilities, data scope, model class, spawn authority, budgets, and lifecycle.
- Versioned templates define safe defaults for researcher, analyst, developer, and verifier workers.
- CEO can create, clone, update, pause, resume, and terminate temporary agents through typed APIs.
- Structured assignments are persisted and run through a replaceable worker-executor protocol.
- A delegation splits bounded items across workers, runs them concurrently, and synthesizes ordered
  results, evidence, confidence, uncertainty, runtime, and cost.
- Runtime, cost, worker-count, and concurrency budgets are validated and enforced; workers cannot
  broaden template capabilities or spawn authority.
- Pausing blocks new work, termination cancels active work, and shutdown cancels owned tasks.
- Agent messages are persisted as structured sender/recipient envelopes and retrievable by inbox.
- Agent and assignment lifecycle changes emit operational events.
- The CEO capability registry exposes delegation without depending on a worker provider.
- The Agents dashboard displays live hierarchy, budgets, assignments, and truthful empty/error states.
- A deterministic ten-competitor simulation proves multi-worker delegation, parallel execution,
  synthesis, evidence, and cleanup without claiming live market facts.
- Restart persistence, lifecycle controls, policy bounds, API behavior, full regression checks,
  production dashboard build, Compose validation, and live container acceptance pass.

## Non-goals

- Live web research, hosted-model worker reasoning, external communications, integration discovery,
  and cross-process distributed worker queues.
- Automatically granting capabilities, filesystem scope, spawn authority, or external-effect access.
