# Principal-owned vaults, VaultHandle namespace, and three-registry model

The original design scoped the vault namespace to an Identity (agent) — one credential namespace per agent. This conflated "the thing that holds a cryptographic key" with "the thing that owns credentials." In practice, a human wants multiple agents to share the same GitHub connection without copying tokens. It also left no room for a Principal to hold multiple separate credential stores (e.g., `prod` vs `dev`).

We introduce two new first-class concepts:

**Principal** — a non-cryptographic logical partition (human or team) that owns Vaults and performs OAuth authorization. Identified by a stable, human-readable **PrincipalHandle** (e.g., `manoj`). Has no cryptographic key of its own. Every Identity registers under exactly one Principal via a **Claim**.

**Vault** — a named credential store owned by exactly one Principal. Identified by a **VaultHandle** (e.g., `default`, `prod`, `dev`), scoped to a Principal — uniqueness is `(PrincipalHandle, VaultHandle)`. Vault keys move from `identity:<handle>:...` to `vault:<principal_handle>:<vault_handle>:...`. All accepted agents under a Principal share its credentials.

Every audit event records both `identity` (which agent acted) and `principal` (on whose behalf).

`AuthService` is constructed with `(vault, principal, vault_handle, identity)`: `principal` and `vault_handle` together drive the vault collection (`vault:<principal>:<vault_handle>`); `identity` is carried only for audit logging. The caller (daemon dependency injection) resolves the correct VaultHandle before constructing AuthService — AuthService is a pure credential-access layer.

The full domain model is tracked across three separate registry files, each authoritative for one entity type: `principals.json` (Principals), `identities.json` (Identities + Claims), `vaults.json` (Vaults). Relationships are expressed as forward keys: `IdentityRegistration.principal_handle` and `VaultRegistration.principal_handle`. No denormalized reverse-index lists are maintained on the Principal entry.

In local mode the Principal is always `default` and the Vault is always `default` — both created automatically during `authsome init`, no explicit creation required. Multiple vaults per principal are not exposed in any CLI or API in this release; the storage key structure and registry schema support the feature when needed. In hosted mode, `authsome init --principal <handle> --email <email>` registers a **Claim** (`IdentityRegistration` with `claim_status = pending`). The Principal reviews pending claims in the UI and accepts or rejects them. A pending agent can authenticate to the daemon but all vault access is gated until the claim is accepted.

## Considered alternatives

**Identity-scoped vault with a parent pointer**: keep `identity:<handle>:...` keys but add a `principal` back-reference. Rejected because it requires either copying tokens across agents or adding an indirection layer — both create drift.

**Email as vault key**: use the Principal's email directly as the namespace key. Rejected because email addresses can change and are awkward in storage keys.

**Single namespace per principal, no VaultHandle**: keep `vault:<principal_handle>:...` with no vault segment. Rejected because it provides no path to multiple vaults per principal without a breaking key restructure later. The `<vault_handle>` segment costs nothing now and makes the future extension non-breaking.

**Per-vault encryption key**: give each Vault its own AES-256-GCM master key for cryptographic isolation between `prod` and `dev`. Rejected as premature — one master key with namespace isolation is sufficient; the registry schema is vault-key-ready when the need arises.

**Embed vault list on PrincipalRegistry**: store `vault_handles: list[str]` as a denormalized field on each Principal entry rather than a separate `vaults.json`. Rejected to keep each registry single-responsibility.

## Consequences

Breaking change — existing vault data under `identity:<handle>:...` is not migrated. Users re-run `authsome login` after upgrading. Per-agent credential visibility filtering is deferred to the policy layer.
