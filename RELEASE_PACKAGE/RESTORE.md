# Restore — lottery-ia-ux-v2.4.5.4-certified (2026.1)

Exact restore of the CERTIFIED conversational baseline.

## Identity lock

| Field | Value |
|-------|-------|
| Tag | `lottery-ia-ux-v2.4.5.4-certified` |
| Commit | `9b440c3b51b9684bf48e6f31bbc23226b2994b6e` |
| Image | `jaios-app-backend:lottery-ia-ux-v2.4.5.4-de` |
| Image ID | `sha256:a6204913747cc2472f2dfec4cd125b95f73fe1fd55439d6d1255c9342780af24` |
| Seed | `20260727` |
| Bank SHA-256 | `6d056978809140eee4af23299cbd0c78a8bae9537fbbbcd62ad50bd18c6d7931` |

## A) Source restore (exact commit)

```bash
cd /path/to/justech-forensic-audit
git fetch --tags
git checkout lottery-ia-ux-v2.4.5.4-certified
bash RELEASE_PACKAGE/verify_restore.sh
```

Expected: script exits 0 and prints `RESTORE_OK`.

## B) Runtime restore (production image)

```bash
# On jaios.justech.do — redeploy the certified backend image
# Prefer alias lottery-ia-ux-v2.4.5.4-de (same ID as lottery-analyst-certified-2026.1)
docker image inspect jaios-app-backend:lottery-ia-ux-v2.4.5.4-de \
  --format '{{.Id}}'
# must equal sha256:a6204913747cc2472f2dfec4cd125b95f73fe1fd55439d6d1255c9342780af24

# Then recreate backend from that tag (site deploy script / compose as used in freeze).
```

## C) Certification replay (optional, read-only)

```bash
# Inside backend container with bank + runner mounted at /tmp
# CERT_ONLY_GROUPS unset; bank SHA must match VERSION_MANIFEST
PYTHONPATH=/app python /tmp/run_certification_audit.py
```

Do not alter `QUESTION_BANK.json`, seed, or evaluator criteria when replaying for restore proof.

## D) Do not

- Move or retarget tag `lottery-ia-ux-v2.4.5.4-certified`
- Hot-patch Prompt Maestro / Hermes / mathematical motor onto this baseline without a new version
- Replace the question bank while claiming this certificate
