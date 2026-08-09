# Testbed

Target platform is Proxmox: a Talos cluster driven by the local Omni instance
(opinionated machine profiles + Proxmox infra provider), Cilium as CNI with
kube-proxy replaced, Agones hosting both Java and Bedrock Minecraft servers.
See [omni/README.md](omni/README.md) for the preferred build,
[talos/README.md](talos/README.md) for the manual `talosctl` fallback, and
[cilium/values.yaml](cilium/values.yaml) for the CNI install values.

The Docker Desktop steps below are for quick local iteration only (e.g.
testing an Agones/Helm change) and don't reflect the real deployment target.
`talosctl cluster create` uses Talos's **default CNI** (not the Cilium /
kube-proxy-replacement stack from `talos/patches/` and `cilium/`).

## Software

- Docker Desktop
- talosctl to create clusters
  - [Talos quickstart](https://www.talos.dev/v1.10/introduction/quickstart/)

```bash
talosctl cluster create --name stormcraft
talosctl kubeconfig
```

agones

```bash
helm repo add agones https://agones.dev/chart/stable
helm repo update

kubectl create namespace java-mc
kubectl create namespace bedrock-mc

helm install my-release agones/agones \
  --namespace agones-system --create-namespace \
  --set "gameservers.namespaces={default,java-mc,bedrock-mc}"
```
