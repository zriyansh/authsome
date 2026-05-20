# Authsome UI Design

## Summary

This design keeps the current dashboard simple while separating three user jobs more clearly:

- `Overview` remains the landing page.
- `Applications` becomes the deployment-scoped provider setup surface.
- `Connections` becomes the vault-scoped inventory of actual named connections.
- `Identity` becomes an informational page about the identities working for the current principal.

The goal is to improve clarity without introducing a new visual model such as explicit scope sections in the sidebar. The UI should continue to feel like the current Authsome dashboard, with targeted refactors to page responsibilities and connection presentation.

## Goals

- Keep the existing server-rendered dashboard and overall visual style.
- Make deployment-level provider configuration visible in the UI.
- Keep connection management separate from provider setup.
- Support multiple named connections per provider cleanly.
- Preserve a simple hosted-mode experience with strict visibility limits.
- Leave room for future principal, vault ownership, and permissions features without exposing them now.

## Non-Goals

- Introducing full principal or vault management UI.
- Adding separate tabs for tokens, API keys, or access tokens.
- Exposing multi-vault workflows in the first version.
- Adding identity management actions beyond basic informational display.
- Reworking the overall design language of the dashboard.

## Navigation

The primary navigation becomes:

- `Overview`
- `Applications`
- `Connections`
- `Identity`

`Overview` remains the default route and continues to act as a lightweight summary page.

The new tabs have these responsibilities:

- `Applications`: provider catalog and deployment-scoped provider setup.
- `Connections`: connection inventory and connection-level operations.
- `Identity`: informational principal-related context.

This intentionally avoids teaching deployment, principal, and vault as explicit labeled scopes in the navigation. Instead, those concepts are expressed by page behavior and copy.

## Page Responsibilities

### Overview

The overview page stays close to the current implementation. It remains the landing page and provides a high-level summary of system state, such as connected apps and recent activity.

It should link users into the new `Applications` and `Connections` pages rather than trying to absorb their functionality.

### Applications

The applications page remains visually close to the current provider catalog. It lists all available providers and acts as the starting point for provider setup.

Each provider card links to a provider setup page. This is true even if the provider has zero or one connection. The provider page is the deployment-scoped view for that app.

For ease of use, the applications page retains a provider-level `Login` action in the provider list view. This allows the user to begin a new connection flow directly from the catalog without first opening the provider setup page.

The applications page answers:

- What providers are available?
- Which providers are configured at the deployment level?
- Where do I go to configure a provider?

It should not become the primary page for managing individual connections.

### Connections

The connections page changes meaning. It is no longer primarily a provider browser. It becomes a connection inventory.

Instead of large provider cards, the page displays thin row cards. Each row represents one connection and includes:

- connection name
- provider name
- compact status
- optional compact context, such as identity name or vault label when useful

This page answers:

- What concrete connections exist right now?
- Which provider does each connection belong to?
- Which connection should I open to inspect tokens or manage access?

The page should include an `Add connection` action. That action starts a new connection flow by choosing a provider, but the page itself should still read as a list of connections rather than a provider gallery.

The page should also include an `Add new connection` button that routes the user to `Applications`. From there, the user chooses a provider and clicks that provider's `Login` action.

### Identity

The identity page is informational only in this version. It lists the identities working for the current principal and explains their role in the system.

It does not include create, rename, archive, or other management-heavy actions in this iteration.

## Provider Setup Page

The provider setup page becomes the deployment-scoped home for a provider.

It keeps the current detail-page shell and should be implemented as a light refactor of the existing provider detail pages rather than a rewrite.

### Self-Hosted Mode

In self-hosted mode, the page shows deployment-level provider configuration such as:

- client ID
- client secret presence or masked value
- redirect URI
- relevant OAuth endpoints
- provider documentation link

The main deployment action is `Configure` or `Replace`, not unrestricted inline editing.

For ease of use, the provider setup page also retains a `Login` action so a user can create a new connection directly from that provider page.

This page also shows existing connections for that provider as a secondary section. Those existing connections are read-oriented on this page and are grouped with scope context. The grouping should show vault and identity as subheaders so the user can understand where the provider is already in use.

The provider setup page answers:

- How is this provider configured for this deployment?
- Can I replace the provider credentials?
- Where is this provider already being used?

### Hosted Mode

In hosted mode, the provider setup page must not reveal deployment credentials or provider-scoped connection inventory.

The page should show only a managed-state presentation such as:

- `Managed by Authsome`
- short explanatory copy that the OAuth application and related setup are managed by the hosted deployment

Hosted mode must not show:

- client ID
- client secret status or value
- redirect URI details intended for deployment operators
- existing connections for that provider

This makes the page informational only in hosted mode.

## Provider Setup Actions

In self-hosted mode, provider credential changes follow the existing backend behavior.

When the user chooses `Configure` or `Replace`, the UI should:

1. present the current provider setup state
2. send the user through the existing credential entry flow
3. show a clear warning before replacement is confirmed

The warning must explicitly state that replacing provider credentials revokes existing connections for that provider.

The UI must not hide or soften this consequence. The warning is a required confirmation step because the action has cross-connection impact.

The provider-level `Login` action on both the applications page and the provider setup page should behave as follows:

1. if no `default` connection exists for that provider in the current vault context, start the login flow using `default`
2. if `default` already exists, open a modal prompting the user for a connection name
3. after the user provides a valid connection name, start the login flow for that named connection

This keeps the common path fast while still supporting multiple named connections without forcing the user through a heavier workflow.

## Connections Page Behavior

The connections page becomes a list of actual connections rather than a list of providers.

Each connection is rendered as a thin clickable row card. A row should feel denser and more operational than the current provider cards.

Recommended row contents:

- connection name as the primary label
- provider name as secondary metadata
- status pill
- optional compact context like identity name
- subtle chevron or affordance indicating navigation

The page should support search and filtering, but the first implementation can stay close to existing filter behavior where practical.

## Connection Detail Page

Tokens, API keys, refresh tokens, and similar secrets remain on the connection detail page.

This page continues to be the operational surface for a specific connection. It should host actions such as:

- reconnect
- disconnect
- inspect access token
- inspect refresh token
- inspect API key

No separate navigation tab is added for tokens or keys. Connection detail remains the single place where connection-scoped secrets are shown.

## Interaction Rules

### Applications to Provider Setup

Clicking a provider on `Applications` always opens the provider setup page.

This is true regardless of how many connections exist for that provider because the purpose of the page is deployment setup, not connection selection.

The separate `Login` action on each provider card starts connection creation and does not replace the main card click target.

### Connections to Connection Detail

The connections page is connection-first.

Each row links directly to the connection detail page for that named connection. Because the page already lists individual connections, there is no need for provider-level expansion behavior on this page.

The `Add new connection` action on this page redirects to `Applications`, where the user can choose a provider and use that provider's `Login` action.

### Existing Connections on Provider Setup

The provider setup page may show existing connections grouped by vault and identity as contextual information. Those items can link to connection detail pages, but they are secondary to deployment setup.

## Data Presentation Rules

### Applications

- primary unit: provider
- scope: deployment
- default action: open provider setup

### Connections

- primary unit: connection
- scope: vault
- default action: open connection detail

### Identity

- primary unit: identity
- scope: principal
- default action: informational only

This is the main organizational rule that keeps the tabs distinct and avoids duplicated meaning.

## Error Handling

The UI should preserve current server-rendered error behavior and add targeted copy where needed.

Important cases:

- if provider credentials are missing in self-hosted mode, the provider setup page should clearly show that the provider is not configured
- if a replace action would revoke connections, the confirmation copy must say so before the action completes
- if hosted mode is active, pages must gracefully replace hidden data with managed-state messaging rather than showing empty sections
- if a connection no longer exists, detail routes should continue to surface a clear not-found or expired-state message

## Implementation Shape

This should be implemented as a focused refactor rather than a redesign.

Likely areas:

- update sidebar/navigation template to add `Applications` and `Identity`
- convert the current provider catalog page into `Applications`
- refactor the current `Connections` page into a connection inventory layout
- adapt provider detail templates to behave as provider setup pages
- retain and adapt provider-level `Login` actions on both provider catalog and provider setup views
- add a connection-name modal for provider login when `default` already exists
- add hosted-mode conditional rendering that hides provider credentials and provider connection listings
- add or adapt identity page templates for informational display

The current detail-page shell should be reused where possible.

## Testing

Add or update coverage for:

- navigation rendering for `Overview`, `Applications`, `Connections`, and `Identity`
- provider setup page in self-hosted mode
- provider setup page in hosted mode
- hosted-mode hiding of provider credentials
- hosted-mode hiding of provider connection inventory
- connection inventory rendering on the `Connections` page
- connection detail navigation from a connection row
- provider-level `Login` behavior when `default` does not exist
- provider-level `Login` modal behavior when `default` already exists
- `Add new connection` redirect from `Connections` to `Applications`
- destructive warning flow for provider credential replacement

UI tests should focus on the new page responsibilities and visibility rules rather than purely visual assertions.

## Rollout Notes

This design intentionally keeps the mental model simple:

- `Applications` is for setting up apps
- `Connections` is for managing actual connected accounts
- `Identity` is for understanding who is acting

That split should be reinforced in page titles, subtitles, and empty-state copy so users understand the difference without learning internal architecture terms first.
