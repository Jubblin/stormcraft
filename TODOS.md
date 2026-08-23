# TODOs

## PAT rotation runbook for the Flux git secret

**What:** Document (or automate) re-encrypting `flux-operator/git-secret.enc.yaml`
when the git PAT it holds expires or is rotated.

**Why:** GitHub PATs expire (fine-grained tokens max out at 1 year). Without
a documented process, a future rebuild or rotation hits a mysteriously-Pending
`sops-decrypt` Job with no obvious cause — the SOPS-encrypted secret silently
holds a dead credential.

**Pros:** Cheap insurance against a confusing failure months from now, when
the context of "why does this Job exist" has faded.

**Cons:** Adds a maintenance doc to keep in sync if the SOPS/age setup changes.

**Context:** Same `sops -e` workflow as the initial encryption in
[docs/designs/flux-auto-bootstrap.md](docs/designs/flux-auto-bootstrap.md) —
generate a new PAT, re-encrypt with the existing `age` public key, commit.
Surfaced during `/plan-eng-review` of that design (outside-voice finding #6).

**Depends on:** The Flux auto-bootstrap design (Approach B) shipping first —
this only matters once `git-secret.enc.yaml` exists.
