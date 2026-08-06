# Omni → Proxmox cluster build

Preferred path for Stormcraft: the **local Omni** instance drives Talos node
lifecycle on Proxmox via the
[omni-infra-provider-proxmox](https://github.com/siderolabs/omni-infra-provider-proxmox)
provider and the opinionated machine classes in this directory.

Manual `talosctl` / hand-built VMs remain documented in
[../talos/README.md](../talos/README.md) as a fallback.

## What lives here

| Path | Role |
|---|---|
| [machine-classes/](machine-classes/) | Auto-provision profiles (CP vs worker sizing for Agones/Minecraft) |
| [cluster-template.yaml](cluster-template.yaml) | Omni cluster template (patches + machineClass sizes) |
| [proxmox-provider/config.yaml.example](proxmox-provider/config.yaml.example) | Provider → Proxmox API config template (no secrets committed) |

Shared Talos patches stay under [../talos/patches/](../talos/patches/) so the
Omni and manual paths share one source of truth.

## Prerequisites (fill in locally — do not commit secrets)

1. Local Omni reachable (API URL) and `omnictl` matching that Omni version.
2. An Omni **infra provider key** for the Proxmox provider (not a normal
   service-account key).
3. Proxmox API user with VM create/manage rights; URL, bridge name, and
   storage pool name known.
4. Placeholders edited before sync:
   - `machine-classes/*.yaml` → `storage_selector`, `network_bridge`
   - `../talos/patches/controlplane-vip.yaml` → `<VIP_IP>`, `<IFACE>`
   - `cluster-template.yaml` → Talos/Kubernetes versions if you pin differently

Open questions for this homelab are tracked on
[issue #2](https://github.com/Jubblin/stormcraft/issues/2).

## Opinionated profiles

Aligned with [../talos/README.md](../talos/README.md) hardware guidance:

| Class | Cores | Memory | Disk | Purpose |
|---|---|---|---|---|
| `proxmox-small` | 2 | 4 GiB | 40 GiB | Control plane (etcd / API, NoSchedule) |
| `proxmox-medium-storage-large` | 4 | 8 GiB | 200 GiB | Workers — Agones game servers + world data |

Both use OVMF + q35 + `cpu_type: host`, VirtIO-friendly defaults, and tags
`stormcraft` for Proxmox inventory. Adjust upward if you run more concurrent
Minecraft instances per worker.

## Apply flow

From a machine that can reach Omni and (indirectly) Proxmox:

```bash
# 1. Run the Proxmox infra provider against local Omni (example)
cp omni/proxmox-provider/config.yaml.example omni/proxmox-provider/config.yaml
# edit config.yaml with Proxmox URL/user/password — keep it out of git
docker run --rm -d --name omni-proxmox-provider \
  -v "$PWD/omni/proxmox-provider/config.yaml:/config.yaml:ro" \
  ghcr.io/siderolabs/omni-infra-provider-proxmox \
  --config-file /config.yaml \
  --omni-api-endpoint "https://<local-omni-host>/" \
  --omni-service-account-key "<infra-provider-key>"

# 2. Register machine classes
omnictl apply -f omni/machine-classes/proxmox-small.yaml
omnictl apply -f omni/machine-classes/proxmox-medium-storage-large.yaml

# 3. Sync the cluster (run from repo root so patch file paths resolve)
omnictl cluster template sync -v -f omni/cluster-template.yaml
```

Omni will ask the Proxmox provider to create VMs matching each machine class
and join them into the `stormcraft` cluster. Watch Machines / Cluster in the
Omni UI until control planes are up.

## Cilium (still required, ≈10-minute window)

The cluster template disables the default CNI and kube-proxy (same patches as
the manual path). After Omni exposes a kubeconfig / API:

```bash
kubectl apply -k cilium/
kubectl -n kube-system wait --for=condition=complete job/cilium-install --timeout=10m
kubectl delete -f cilium/bootstrap-job/serviceaccount.yaml
```

See [../talos/README.md](../talos/README.md) §5 for why the deadline matters and
how to recover if a node reboots before Cilium lands.

## Install disk note

Talos 1.13+ needs an explicit `machine.install.disk`. The cluster template
sets `/dev/sda` (typical for VirtIO SCSI on Proxmox). If your VMs present the
disk as `/dev/vda` instead, change the `install-disk` patch in
`cluster-template.yaml` before syncing.
