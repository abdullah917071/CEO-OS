import assert from "node:assert/strict";
import test from "node:test";

import { availableTaskActions, groupCapabilities } from "./dashboard-utils.mjs";

test("shows only valid lifecycle controls", () => {
  assert.deepEqual(availableTaskActions("running"), ["pause", "cancel"]);
  assert.deepEqual(availableTaskActions("waiting"), ["resume", "cancel"]);
  assert.deepEqual(availableTaskActions("success"), []);
});

test("groups capability registry entries by domain", () => {
  const groups = groupCapabilities([
    { name: "files.read", risk: "R0" },
    { name: "files.write", risk: "R1" },
    { name: "browser.navigate", risk: "R0" },
  ]);
  assert.equal(groups.files.length, 2);
  assert.equal(groups.browser.length, 1);
});
