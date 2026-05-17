# Eval Setup Guide

Run this before every eval session. It brings the machine to a known clean state so tests start from predictable authsome installation with no leftover credential state.

## 1. Fresh install

If authsome is already installed, reinstall to get the latest version:

```bash
uv tool install --reinstall authsome
```

If not yet installed:

```bash
uv tool install authsome
```

Verify:

```bash
authsome --version
```

## 2. Wipe state

Remove all existing authsome state (identities, credentials, config):

```bash
rm -rf ~/.authsome
```

## 3. Initialise

```bash
authsome init
```

Expected: prints your new identity handle and DID.

## 4. Verify

```bash
authsome doctor
```

Expected: exit code `0`, all checks `ok`.

## 5. Confirm no providers are connected

```bash
authsome list
```

Expected: all providers show `not_connected`. If any show `connected`, run `authsome logout <provider>` for each.

---

## Between-test state notes

The eval sequence is ordered so that credential state built by one test is reused by the next. See the Test Sequence table in the design spec. The one manual step between tests is:

- **After test 2 (Agentic Installation and Login):** run `authsome logout github` so that test 3 (Scenario 2) starts with github disconnected.
