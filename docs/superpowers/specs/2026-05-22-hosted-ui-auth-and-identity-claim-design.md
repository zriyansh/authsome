# Hosted UI Auth And Identity Claim Design

Date: 2026-05-22
Status: Approved in chat, written for review

## Summary

This spec replaces the hosted-mode identity claim form with a minimal account authentication flow based on email and password, then an explicit claim confirmation step.

Hosted mode will move to a single browser authentication model:

- the hosted browser session is authenticated as a user account
- `User` and `Principal` are the same concept permanently
- the hosted dashboard is account-scoped, not identity-scoped
- unclaimed identities are claimed only after sign-in or registration and explicit confirmation

Local mode remains seamless:

- no browser login
- no account registration
- no claim flow prompt
- all identities continue to resolve under the implicit local default principal

The implementation should keep hosted/local branching at the lowest practical level. Route and service interfaces should stay generic and avoid spreading deployment-mode conditionals throughout the codebase.

## Goals

- Add a minimal hosted registration and login flow using email plus password
- Protect hosted UI sessions with a proper auth mechanism and JWT-backed session model
- Require explicit confirmation before claiming an identity
- Keep the hosted UI visually minimal and consistent with the existing black/green theme
- Preserve the current seamless local-mode experience
- Remove older hosted claim/session code that no longer fits the new model

## Non-Goals

- Backward compatibility with the current hosted claim-by-email form
- Multi-principal or workspace support
- Social login, password reset, email verification, or MFA
- New directories for auth code
- Broad refactors outside the hosted auth and claim flow

## User Decisions Captured

- Hosted mode uses one consolidated browser auth flow
- `User == Principal` permanently
- Login identifier is email
- Authentication method is email plus password
- Sign-in and registration share one minimal combined page
- After auth, claiming requires a separate confirmation screen
- Local mode must stay seamless with no login prompt
- New hosted auth code should ideally fit in two new files maximum and no new directories
- Older code that no longer serves the new flow should be removed rather than preserved

## Current State

Today, hosted identity registration returns a `claim_url` when an identity is unclaimed. That URL opens `/ui/claim/{token}`, which renders a simple email form. Submitting the form immediately claims the identity, creates a hosted UI browser session, and redirects to the dashboard.

The current implementation uses:

- `HostedIdentityBootstrapService` to decide whether `claim_url` is needed
- `UiClaimBootstrapToken` in `src/authsome/server/ui_sessions.py` to represent pending claim state
- `UiBrowserSession` in `src/authsome/server/ui_sessions.py` to represent hosted browser sessions bound to identity and principal
- `/ui/claim/{token}` routes in `src/authsome/server/routes/ui.py` for the email-only claim form

That model is too identity-centric for the new requirements. The browser session needs to become account-authenticated first, with claim completion layered on top.

## Target Architecture

### High-level model

Hosted mode will use a single account-authenticated browser session model. The browser signs in as a hosted user account, and that account is the principal. Identities are resources owned by that authenticated principal, not the subject of browser authentication themselves.

The claim link remains the onboarding entry point for newly registered unclaimed identities, but it is no longer the authentication mechanism. Instead, it carries pending claim context:

- which identity is waiting to be claimed
- whether the link is still valid
- where the flow should continue after auth

Once the browser is authenticated, the flow proceeds to an explicit confirmation screen before the identity is claimed.

### Hosted-only components

The new hosted auth flow should stay small. Prefer reusing the existing `src/authsome/server/` area and avoid adding directories. Aim for no more than two new files for the new auth path.

Recommended components:

- `HostedAccountService`
  Handles account registration, login, password hashing, password verification, and JWT issuance/validation. Because `User == Principal`, it creates or loads the principal directly.

- `HostedBrowserSessionStore`
  Handles hosted browser session cookies and session lookup. Its session model is user/principal-scoped rather than identity-scoped.

- `PendingClaimStore`
  Handles short-lived pending claim tokens for identities opened through claim URLs. This is conceptually already present today as `UiClaimBootstrapToken`; it should be renamed and tightened rather than duplicated.

No `HostedPrincipalResolver` is needed. The authenticated hosted account should already contain the principal identity required by the rest of the system.

### File-shape guidance

Keep the implementation compact:

- substantially replace `src/authsome/server/ui_sessions.py` rather than preserving its current identity-scoped structure
- place the hosted account logic in at most two new files, or fold part of it into an existing server file if that keeps boundaries clear
- do not add new directories

The preferred outcome is:

- one file for hosted account auth behavior and models
- one file for hosted browser session and pending claim token storage

If `ui_sessions.py` is rewritten cleanly enough to absorb browser-session and pending-claim state, then only one additional hosted account auth file may be necessary.

## Route Design

### Hosted mode

The hosted route surface should be simplified around authenticated browser sessions:

- `GET /ui/claim/{token}`
  Loads the pending claim flow. If the browser is not authenticated, render the combined sign in / register page. If the browser is authenticated, render the claim confirmation page.

- `POST /ui/auth/register`
  Creates the hosted account and matching principal, establishes the hosted browser session, and redirects back to the claim page when pending claim context exists.

- `POST /ui/auth/login`
  Authenticates the hosted account, establishes the hosted browser session, and redirects back to the claim page when pending claim context exists.

- `POST /ui/claim/{token}/confirm`
  Claims the pending identity to the authenticated principal and redirects to the dashboard.

- `POST /ui/logout`
  Clears the hosted browser session.

- `GET /ui/`
  Requires an authenticated hosted browser session and shows the account-scoped dashboard with all identities owned by the current account.

The existing hosted bootstrap URL may remain as a transport-only handoff if it still helps CLI-driven browser opening, but it should not remain the source of truth for hosted browser authentication.

### Local mode

Local mode keeps the same seamless route behavior:

- `GET /ui/` continues to resolve the current local identity without browser login
- no login or registration page is introduced
- no claim confirmation page is introduced

This branching should stay inside the lowest-level UI session and ownership resolution code, not spread across unrelated route handlers.

## State Model

### Hosted browser auth state

Hosted browser auth state should represent the signed-in account:

- `principal_id`
- `email`
- creation and expiry timestamps
- cookie or token binding data

The implementation should use JWT tokens for UI auth. The browser may still store the session as a secure HTTP-only cookie, but the cookie value should represent or carry a JWT-backed authenticated session, not an identity-scoped opaque session from the old model.

### Pending claim state

Pending claim state should remain separate from hosted browser auth state. It needs to survive the transition from signed-out browser to signed-in browser while keeping the claim target explicit.

Minimum fields:

- `token`
- `identity`
- `created_at`
- `expires_at`

Optional fields:

- return or redirect target if needed

This state already exists today in primitive form through `UiClaimBootstrapToken`. The redesign should formalize it, not invent a second overlapping mechanism.

## Flow Design

### Hosted unclaimed identity flow

1. A new identity registers with the hosted server.
2. If the identity is already claimed, registration status reflects that and no claim onboarding is needed.
3. If the identity is unclaimed, the server returns a hosted claim URL backed by a pending claim token.
4. The browser opens `GET /ui/claim/{token}`.
5. If no hosted browser auth session exists, render one minimal combined sign in / create account page using the current black/green theme.
6. The user signs in or registers with email and password.
7. A hosted browser session is created.
8. The browser returns to `GET /ui/claim/{token}`.
9. Because the user is now authenticated, render a confirmation page that clearly states which identity will be claimed to which account email.
10. The user confirms the claim.
11. The server claims the identity to the authenticated principal, ensures the default vault binding exists, and redirects to `/ui/`.
12. The hosted dashboard now shows the claimed identity under the signed-in account.

### Hosted already-signed-in claim flow

1. A signed-in hosted user opens `GET /ui/claim/{token}`.
2. The route validates the pending claim token.
3. The route renders the confirmation page immediately.
4. The user confirms the claim.
5. The identity is claimed and the user is redirected to the dashboard.

### Hosted dashboard flow

1. The browser visits `/ui/`.
2. Hosted mode requires an authenticated browser session.
3. The dashboard loads as the authenticated account and lists identities claimed by that account.

### Local dashboard flow

1. The browser visits `/ui/`.
2. Local mode resolves the current local identity and implicit local principal.
3. The dashboard loads without any login prompt.

## Data And Storage Design

### Principal and account identity

Because `User == Principal` permanently, hosted account registration should create or resolve the principal directly. The principal registry remains the authoritative store for the logical account owner.

The email is the login identifier. It should continue to be treated as mutable account data, while `principal_id` remains the stable identifier used internally.

### Password storage

Password handling should use a trusted library and store only hashed passwords. The code should not implement custom password crypto. Keep the password logic encapsulated inside the hosted account auth service.

The storage record should be server-owned and simple. It needs:

- `principal_id`
- `email`
- `password_hash`
- timestamps

The exact persistence shape can follow the existing server registry style or nearby store patterns, but it should remain a small server-owned record with one clear responsibility.

### Claim persistence

Identity claims continue to use the existing claim registry. The main change is when the claim happens:

- before: immediate after email form submit
- after: only after authenticated confirmation

No extra persistence layer is needed for confirmed claims beyond the existing claim registry and principal-vault binding behavior.

## UI Design

The UI should remain minimal and match the current visual language:

- same black/green theme
- server-rendered HTML
- no design-system expansion
- no new visual framework

Hosted auth screens should include:

- a combined sign in / create account page with minimal toggle or tabs
- inline error messaging for auth failures
- a simple confirmation screen showing:
  - the identity handle
  - the signed-in account email
  - confirm and cancel actions

Do not introduce a large standalone auth UI. The goal is a lightweight extension of the current hosted pages.

## Error Handling

Keep failure handling small, explicit, and deterministic.

Hosted errors to cover:

- expired or unknown pending claim token:
  render a short page telling the user the claim link expired and they should restart the flow

- duplicate registration email:
  render an inline error on the combined auth page

- wrong password:
  render an inline error on the combined auth page

- claim token reused after success:
  show a stable “already completed or expired” message

- identity already claimed by the signed-in user:
  either render an “already claimed” success page or redirect to the dashboard with a success message

- identity already claimed by another principal:
  render a clear failure page and do not mutate state

- hosted dashboard without browser auth:
  render the existing session-expired style message or redirect to the hosted sign-in entry point consistently

Local-mode error handling should remain as close to current behavior as possible.

## Cleanup Plan

Backward compatibility is not required. Remove or rewrite older code when it no longer fits.

Expected cleanup targets:

- remove the old email-only claim form behavior from `src/authsome/server/routes/ui.py`
- replace or substantially rewrite `src/authsome/server/ui_sessions.py`
- remove hosted identity-scoped browser session assumptions
- remove or simplify any route code that exists only to preserve the old hosted model

Avoid unrelated refactoring. Cleanup should stay tightly scoped to hosted auth, hosted claim onboarding, and the session boundary changes they require.

## Testing Plan

Add or update tests to cover the new hosted state machine and protect local behavior.

Hosted tests:

- account registration success
- account login success
- duplicate email registration failure
- wrong password login failure
- password hashing and verification behavior
- hosted browser session creation and validation
- hosted logout clears the browser session
- signed-out claim flow: claim link -> auth page -> register or login -> confirmation -> claim -> dashboard
- signed-in claim flow: claim link -> confirmation -> claim -> dashboard
- expired claim token
- attempt to claim an identity already claimed by the same account
- attempt to claim an identity already claimed by another account
- hosted dashboard requires authenticated browser session

Local regression tests:

- local `/ui/` still loads without login
- local identity registration still does not produce hosted login requirements
- local ownership remains implicit and seamless

## Implementation Constraints

- no new directories
- keep new hosted auth code to two files maximum if possible
- keep hosted/local branching at the bottom-most level
- keep interfaces generic and implementation-agnostic
- prefer deletion of legacy code over compatibility shims
- use trusted password-hashing libraries rather than custom crypto

## Open Implementation Decisions

These are intentionally constrained, not product-open questions:

- whether hosted account records are best implemented as a dedicated registry file or via the existing server KV substrate
- whether the hosted browser cookie stores the JWT directly or stores a signed session wrapper that contains JWT-derived identity data
- whether the existing hosted bootstrap route remains as a thin transport handoff for CLI-opened browser flows

The implementation plan should decide these based on the existing code patterns and the goal of keeping the change compact.
