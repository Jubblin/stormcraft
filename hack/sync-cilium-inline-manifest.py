#!/usr/bin/env python3
"""Regenerate the inlineManifests block in talos/patches/cni-kubeproxy.yaml
from the canonical `kubectl kustomize <dir>` output of each bootstrap Job
below, so none of them can drift apart from their source.

Both Jobs land in the same inlineManifests list: Talos applies it once at
bootstrap, and each Job's own pod spec (hostNetwork or not, tolerations
or not) decides when it can actually schedule — cilium-install runs
first because it tolerates NotReady nodes; flux-operator-install just
sits Pending until Cilium brings nodes up, no ordering logic needed.

Run locally to update the file, or let
.github/workflows/sync-cilium-inline-manifest.yml run it and open a PR
whenever it produces a diff.
"""
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PATCH_FILE = REPO_ROOT / "talos" / "patches" / "cni-kubeproxy.yaml"
CONTENT_INDENT = 8

# (inlineManifests entry name, kustomize dir)
MANIFESTS = [
    ("cilium-bootstrap", "cilium"),
    ("flux-operator-bootstrap", "flux-operator"),
]


def render_kustomize(dir_name: str) -> str:
    result = subprocess.run(
        ["kubectl", "kustomize", str(REPO_ROOT / dir_name)],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def indent(text: str, spaces: int) -> str:
    prefix = " " * spaces
    return "\n".join(prefix + line if line.strip() else line for line in text.splitlines())


def render_entry(name: str, dir_name: str) -> str:
    contents = indent(render_kustomize(dir_name).rstrip() + "\n", CONTENT_INDENT)
    return f"    - name: {name}\n      contents: |\n{contents}"


def render_patch() -> str:
    entries = "\n".join(render_entry(name, dir_name) for name, dir_name in MANIFESTS)
    return f"""\
# Shared patch applied to BOTH controlplane.yaml and worker.yaml.
# Cilium replaces both the default CNI and kube-proxy, so both must be
# turned off here before the cluster ever comes up.
#
# inlineManifests below is GENERATED — do not hand-edit it. Each entry is
# `kubectl kustomize <dir>/` for one of the bootstrap Jobs (cilium/,
# flux-operator/), rendered by hack/sync-cilium-inline-manifest.py and
# kept in sync by .github/workflows/sync-cilium-inline-manifest.yml.
# Talos applies all of it automatically at bootstrap, so a fresh cluster
# gets every listed Job with no manual `kubectl apply -k` step required.
cluster:
  network:
    cni:
      name: none
  proxy:
    disabled: true
  inlineManifests:
{entries}
"""


def main() -> int:
    patch = render_patch()
    current = PATCH_FILE.read_text() if PATCH_FILE.exists() else ""

    if patch == current:
        print("talos/patches/cni-kubeproxy.yaml is already up to date")
        return 0

    PATCH_FILE.write_text(patch)
    print(f"Updated {PATCH_FILE.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
