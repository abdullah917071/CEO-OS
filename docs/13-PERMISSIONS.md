# Permissions

Capabilities carry risk classes: R0 read, R1 harmless local write, R2 external communication, R3 financial/business change, and R4 destructive/admin. Risk is combined with owner autonomy settings, task scope, data sensitivity, agent identity, budgets, and current environment.

Policy outcomes are allow, deny, require approval, or shadow. Approval records bind an exact actor, action, arguments or bounded range, expiry, and task. Material argument changes invalidate approval.

Milestone 1 automatically permits built-in R0 and workspace-contained R1 capabilities. It exposes no R2–R4 capability. Later policy enforcement must occur immediately before effects and again after any pause or retry.

The owner can configure autonomy per domain, but a global stop prevents new external actions regardless of profile.

