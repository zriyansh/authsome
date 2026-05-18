# Principal-owned vault namespace and on-behalf-of agent model

The original design scoped the vault namespace to an Identity (agent) — one credential namespace per agent. This conflated "the thing that holds a cryptographic key" with "the thing that owns credentials." In practice, a human wants multiple agents to share the same GitHub connection without copying tokens.

We introduce **Principal** as a first-class, non-cryptographic concept: a logical partition (human or team) that owns the vault namespace and performs OAuth authorization. Vault keys move from `identity:<handle>:...` to `principal:<PrincipalHandle>:...`. Every Identity registers under exactly one Principal; all accepted agents under a Principal share its credentials. Every audit event records both `identity` (which agent) and `principal` (on whose behalf).

In local mode the Principal is always `default` — no explicit creation required. In hosted mode, `authsome init --principal <handle> --email <email>` registers a **Claim** (an `IdentityRegistration` with `claim_status = pending`). The Principal reviews pending claims in the UI and accepts or rejects them. A pending agent can authenticate to the daemon but all vault access is gated until the claim is accepted.

`AuthService` is constructed with `(vault, principal, identity)`: `principal` drives the vault collection, `identity` is carried only for audit logging.

## Considered alternatives

**Identity-scoped vault with a parent pointer**: keep `identity:<handle>:...` keys but add a `principal` back-reference. Rejected because it requires either copying tokens across agents or adding an indirection layer — both create drift. Principal-scoped keys are the simpler model.

**Email as vault key**: use the Principal's email directly as the namespace key. Rejected because email addresses can change and are awkward in storage keys; a human-readable handle (e.g., `manoj`) is stable and debuggable.

## Consequences

Breaking change shipped in v0.4. Existing vault data under `identity:<handle>:...` is not migrated — users re-run `authsome login` after upgrading. Per-agent credential visibility filtering is deferred to the policy layer.
