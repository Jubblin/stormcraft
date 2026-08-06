# Talos cluster on Proxmox

Target: 3 control-plane VMs + N worker VMs on a Proxmox host, DHCP networking
on the existing bridge, Cilium as CNI with kube-proxy replaced. This is the
base platform the Agones-hosted Java + Bedrock Minecraft servers will run on
([../README.md](../README.md)).

## 1. VM hardware (per node, in Proxmox)

| Setting | Value |
|---|---|
| BIOS | OVMF (UEFI) + 4MB EFI disk |
| Machine type | q35 |
| CPU type | host |
| Disk controller | VirtIO SCSI (not "VirtIO SCSI Single") |
| Network model | virtio, on the existing bridge (DHCP) |
| Control plane sizing | 2 vCPU / 4GB+ |
| Worker sizing | 4 vCPU / 8GB+ (game servers are the workload) |

Boot each VM once from the Talos `metal-amd64.iso` (from Image Factory) with
no disk attached yet — Talos runs from RAM in maintenance mode until it
receives a config.

## 2. Generate machine configs

```bash
talosctl gen config stormcraft https://<VIP_IP>:6443 \
  --output-dir _out \
  --config-patch @talos/patches/cni-kubeproxy.yaml \
  --config-patch-control-plane @talos/patches/controlplane-vip.yaml
```

`<VIP_IP>` is the floating control-plane address from
[patches/controlplane-vip.yaml](patches/controlplane-vip.yaml) — reserve it
in DHCP before this step, it's the cluster endpoint from here on.

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

## 5. Install Cilium (cluster has no CNI / networking yet at this point)

```bash
kubectl apply -k ../cilium/
kubectl -n kube-system wait --for=condition=complete job/cilium-install --timeout=10m
```

This runs `helm install` from an in-cluster Job instead of from your own
machine — see [../cilium/bootstrap-job/job.yaml](../cilium/bootstrap-job/job.yaml)
for why that's possible with no CNI up yet (`hostNetwork: true`) and what
it needs (a cluster-admin ServiceAccount, since it's creating Cilium's
CRDs/ClusterRoles/DaemonSets).

Once it completes, remove the bootstrap RBAC — it's cluster-admin and only
needed for this one install:

```bash
kubectl delete -f ../cilium/bootstrap-job/serviceaccount.yaml
```

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

## Notes

- Control-plane nodes are tainted `NoSchedule` by default in Talos, so
  game server pods land on workers without any extra config.
- Agones needs `hostPort` to work for game clients to reach a pod directly.
  Cilium supports `hostPort` natively (no extra chained CNI plugin, no
  extra Helm flag) — verify with a quick test pod before relying on it for
  the Minecraft servers.
- Agones install + the Java/Bedrock GameServer manifests are the next step,
  not covered here yet.
