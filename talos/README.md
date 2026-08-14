# Talos cluster on Proxmox

Target: 3 control-plane VMs + N worker VMs on a Proxmox host, DHCP networking
on the existing bridge, Cilium as CNI with kube-proxy replaced. This is the
base platform the Agones-hosted Java + Bedrock Minecraft servers will run on
([../README.md](../README.md)).

**Preferred path:** provision and configure nodes via the local Omni instance
and opinionated machine profiles — see [../omni/README.md](../omni/README.md).
The `talosctl` steps below are the manual fallback (or for understanding what
Omni is applying).

## 1. VM hardware (per node, in Proxmox)

| Setting | Value |
|---|---|
| BIOS | OVMF (UEFI) + 4MB EFI disk |
| Machine type | q35 |
| CPU type | host |
| Disk controller | VirtIO SCSI (not "VirtIO SCSI Single") |
| Disk size | Control plane ≥40GB; workers ≥200GB (Minecraft world data) |
| Network model | virtio, on the existing bridge (DHCP) |
| Control plane sizing | 2 vCPU / 4GB+ (`proxmox-small` via Omni) |
| Worker sizing | 4 vCPU / 8GB+ / 200GB disk (`proxmox-medium-storage-large` via Omni) |

Attach an empty install disk to each VM, then boot once from the Talos
`metal-amd64.iso` ([Image Factory](https://factory.talos.dev/)). Talos runs
from RAM in maintenance mode until it receives a config, then installs onto
that disk. Without a disk attached, `apply-config` / Omni provision cannot
complete the install.

## Checklist before config generation

Fill these in before `talosctl gen config` or `omnictl cluster template sync`:

1. Reserve `<VIP_IP>` in DHCP (or otherwise keep it out of the lease pool).
2. Edit [patches/controlplane-vip.yaml](patches/controlplane-vip.yaml): set
   `<VIP_IP>` and `<IFACE>` (usually `eth0` on Proxmox virtio — confirm with
   `talosctl get links --insecure -n <node-ip>` after first boot).
3. Confirm the Omni machine-class placeholders (`storage_selector`,
   `network_bridge`) if using the Omni path — see [../omni/README.md](../omni/README.md).

## 2. Generate machine configs (manual path)

```bash
talosctl gen config stormcraft https://<VIP_IP>:6443 \
  --output-dir _out \
  --config-patch @talos/patches/cni-kubeproxy.yaml \
  --config-patch-control-plane @talos/patches/controlplane-vip.yaml
```

`<VIP_IP>` is the floating control-plane address from
[patches/controlplane-vip.yaml](patches/controlplane-vip.yaml) — it is the
cluster endpoint from here on.

## 3. Apply config to each node

Find each VM's DHCP-assigned address (Proxmox console, or your DHCP
server's lease table), then, per node:

```bash
talosctl apply-config --insecure -n <node-ip> --file _out/controlplane.yaml   # x3
talosctl apply-config --insecure -n <node-ip> --file _out/worker.yaml         # xN
```

## 4. Bootstrap

```bash
export TALOSCONFIG=_out/talosconfig
talosctl config endpoint <VIP_IP>
talosctl config node <first-controlplane-ip>   # bootstrap targets one CP directly
talosctl bootstrap
talosctl kubeconfig .
```

## 5. Install Cilium (≈10-minute window)

Both this Job and flux-operator's (step 6) are already in
[patches/cni-kubeproxy.yaml](patches/cni-kubeproxy.yaml)'s
`inlineManifests` — Talos applies them automatically right after
`talosctl bootstrap`, so you shouldn't need to run either step's
`kubectl apply -k` by hand. It's here for visibility into what's
happening, and as the manual re-trigger if you miss the reboot window
below or need to debug.

After bootstrap with `cni: none`, nodes stay NotReady until a CNI is running.
Talos will appear stuck around phase 18/19 (`node not ready`) and **reboots
to retry after roughly 10 minutes** if Cilium is not installed in time.
Apply Cilium immediately after you have a working kubeconfig:

```bash
kubectl apply -k ../cilium/
kubectl -n kube-system wait --for=condition=complete job/cilium-install --timeout=10m
```

This runs `helm install` from an in-cluster Job instead of from your own
machine — see [../cilium/bootstrap-job/job.yaml](../cilium/bootstrap-job/job.yaml)
for why that's possible with no CNI up yet (`hostNetwork: true`) and what
it needs (a cluster-admin ServiceAccount, since it's creating Cilium's
CRDs/ClusterRoles/DaemonSets).

Before it touches Helm, a `preflight` initContainer checks the cluster is
actually in the state this whole setup assumes — API reachable, all 3
control-plane nodes joined, kube-proxy genuinely absent (i.e. the CNI
patch took), and no previous cilium release stuck mid-install. It fails
the Job with a clear message rather than let a bad assumption surface as
a confusing Helm error. If the Job fails at this step:

```bash
kubectl -n kube-system logs job/cilium-install -c preflight
```

Once it completes, remove the bootstrap RBAC — it's cluster-admin and only
needed for this one install:

```bash
kubectl delete -f ../cilium/bootstrap-job/serviceaccount.yaml
```

(The Job itself is cleaned up by `ttlSecondsAfterFinished`; the values
ConfigMap from kustomize can stay or be deleted with the Job leftovers.)

If you'd rather run Helm from your own machine instead (e.g. to debug a
failed install), the equivalent manual command is:

```bash
helm repo add cilium https://helm.cilium.io/
helm repo update
helm install cilium cilium/cilium --version 1.18.0 \
  --namespace kube-system -f ../cilium/values.yaml
```

Either way, wait for nodes to go `Ready` (`kubectl get nodes`) and `cilium
status --wait` (via the Cilium CLI, or `kubectl -n kube-system get pods -l
k8s-app=cilium`) before moving on to Agones.

If you miss the window and nodes reboot before Cilium is up, re-apply the
bootstrap Job (or Helm install) as soon as the API is reachable again.

## 6. Install Flux Operator

Also auto-applied via inlineManifests (see step 5) — its Job just sits
Pending until Cilium brings nodes `Ready`, no ordering step needed. Manual
re-trigger/debug command:

```bash
kubectl apply -k ../flux-operator/
kubectl -n flux-system wait --for=condition=complete job/flux-operator-install --timeout=10m
kubectl delete clusterrolebinding flux-operator-installer
kubectl delete serviceaccount flux-operator-installer -n flux-system
```

Same in-cluster-Job idea as Cilium, without the CNI-bootstrap machinery —
no hostNetwork, no kubeconfig-in-cluster mount, no preflight checks, none
of that is needed once Cilium's already running normal pod networking.

## Notes

- Control-plane nodes are tainted `NoSchedule` by default in Talos, so
  game server pods land on workers without any extra config.
- [patches/cni-kubeproxy.yaml](patches/cni-kubeproxy.yaml) sets
  `forwardKubeDNSToHost: false` so CoreDNS works with Cilium's BPF path
  (Talos known issue with the default `true` + Cilium masquerade/host routing).
- Agones needs `hostPort` to work for game clients to reach a pod directly.
  Cilium supports `hostPort` natively (no extra chained CNI plugin, no
  extra Helm flag) — verify with a quick test pod before relying on it for
  the Minecraft servers.
- Agones install + the Java/Bedrock GameServer manifests are the next step,
  not covered here yet.
