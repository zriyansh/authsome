# ProviderClientRecord is server-scoped, not profile-scoped

OAuth `client_id` and `client_secret` represent the OAuth application registration — they belong to the server, not to the user. In a hosted multi-user deployment, all profiles share the same OAuth app. Storing `ProviderClientRecord` per-profile would force every user to register their own OAuth app, which breaks the managed hosting model where authsome provides the app credentials.

**Decision:** `ProviderClientRecord` is stored under the key `server:<provider>:client`, shared across all profiles and users on a server instance. Connection tokens (`ConnectionRecord`) remain profile-scoped as before.

**Considered alternative:** Keep `ProviderClientRecord` per-profile. Rejected because it prevents shared OAuth app credentials on hosted deployments and forces each user to manage their own OAuth app registration.

**Consequence:** Any existing `ProviderClientRecord` data stored under `profile:<name>:<provider>:client` is not migrated automatically — users on upgraded local deployments must re-enter client credentials once.
