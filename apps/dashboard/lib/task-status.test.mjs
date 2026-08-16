import assert from "node:assert/strict";
import test from "node:test";

import { formatTaskStatus } from "./task-status.mjs";

test("formats task status for display", () => {
  assert.equal(formatTaskStatus("needs_approval"), "needs approval");
});

