#!/usr/bin/env python3
"""Regenerate the inlineManifests block in talos/patches/cni-kubeproxy.yaml
from the canonical `kubectl kustomize cilium/` output, so the two can't
drift apart.

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


def render_kustomize() -> str:
    result = subprocess.run(
        ["kubectl", "kustomize", str(REPO_ROOT / "cilium")],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def indent(text: str, spaces: int) -> str:
    prefix = " " * spaces
    return "\n".join(prefix + line if line.strip() else line for line in text.splitlines())


def render_patch(rendered_manifests: str) -> str:
    contents = indent(rendered_manifests.rstrip() + "\n", CONTENT_INDENT)
    return f"""\
# Shared patch applied to BOTH controlplane.yaml and worker.yaml.
# Cilium replaces both the default CNI and kube-proxy, so both must be
# turned off here before the cluster ever comes up.
#
# inlineManifests below is GENERATED — do not hand-edit it. It's
# `kubectl kustomize cilium/` (cilium/bootstrap-job/*.yaml +
# cilium/values.yaml), rendered by hack/sync-cilium-inline-manifest.py and
# kept in sync by .github/workflows/sync-cilium-inline-manifest.yml.
# Talos applies it automatically at bootstrap, so a fresh cluster gets the
# cilium-install Job (see cilium/bootstrap-job/job.yaml) with no manual
# `kubectl apply -k cilium/` step required.
cluster:
  network:
    cni:
      name: none
  proxy:
    disabled: true
  inlineManifests:
    - name: cilium-bootstrap
      contents: |
{contents}
"""


def main() -> int:
    patch = render_patch(render_kustomize())
    current = PATCH_FILE.read_text() if PATCH_FILE.exists() else ""

    if patch == current:
        print("talos/patches/cni-kubeproxy.yaml is already up to date")
        return 0

    PATCH_FILE.write_text(patch)
    print(f"Updated {PATCH_FILE.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
