# Security Notes

## Local Daemon V1

The first client-server implementation runs a local daemon bound to:

```text
127.0.0.1:7998
```

The daemon is intentionally local-only in v1. Hosted mode, user accounts, orgs,
and remote authorization are out of scope for this release.

Known v1 tradeoffs:

- The daemon relies on loopback binding for local access control.
- There is no local bearer token between CLI/proxy and daemon yet.
- Browser-rendered input forms do not include a per-session CSRF/form token yet.
- Active auth sessions are stored in daemon memory and are lost on daemon restart.
- Proxy-resolved credentials are cached only in memory for the lifetime of
  `authsome run`.

Secrets remain encrypted at rest through the Authsome vault. The server API does
not expose raw vault endpoints in v1.

## Hosted Internal Deployment

Authsome can also be deployed as a small shared internal service when all of the
following are true:

- the service lives on a trusted private network
- one shared vault/store is acceptable
- operators understand that the network is the primary access-control boundary

For hosted deployments, set `AUTHSOME_SERVER_BASE_URL` on the server to the exact
URL used by the browser and by OAuth provider callback registration. Example:

```text
https://authsome.internal.example.com
```

The hosted callback URL is then:

```text
https://authsome.internal.example.com/auth/callback/oauth
```

Client machines that talk to a hosted daemon should set `AUTHSOME_DAEMON_URL`
to that hosted daemon URL. They do not need `AUTHSOME_SERVER_BASE_URL`.

### Hosted deployment assumptions

The smallest hosted deployment deliberately keeps the current trust model simple:

- no per-user authentication layer inside authsome yet
- no tenant separation
- no persistent browser-session store
- one shared `AUTHSOME_HOME`, typically on a persistent disk

In this model, access to the persistent filesystem matters as much as network
access. A host that can read both the encrypted SQLite store and `master.key`
can effectively access the vault contents.

### Recommended boundary for hosted use

Treat hosted authsome as an internal infrastructure service:

- place it behind a private IP, VPN, or overlay network
- restrict ingress to trusted operator machines only
- snapshot or back up the persistent disk
- terminate TLS at your private reverse proxy if you need a stable HTTPS URL

### Current hosted tradeoffs

The hosted path inherits several local-daemon tradeoffs:

- active auth sessions are still stored only in daemon memory
- a process restart during login loses the in-flight session
- there is not yet a built-in shared admin secret or bearer token gate
- browser forms do not yet have full session-hardening for internet-facing use

Future hosted/server releases must add real authentication, authorization,
browser session protection, and stronger daemon hardening before authsome should
be treated as an internet-facing service.
