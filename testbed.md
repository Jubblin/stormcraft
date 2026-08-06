# Testbed

Target platform is Proxmox: a Talos cluster on Proxmox VMs, Cilium as CNI
with kube-proxy replaced, Agones hosting both Java and Bedrock Minecraft
servers. See [talos/README.md](talos/README.md) for the cluster build and
[cilium/values.yaml](cilium/values.yaml) for the CNI install.

The Docker Desktop steps below are for quick local iteration only (e.g.
testing an Agones/Helm change) and don't reflect the real deployment target.

## Software
- Docker Desktop
- talosctl to create clusters
  - [Talos quickstart](https://www.talos.dev/v1.10/introduction/quickstart/)

``` bash
talosctl cluster create --name stormcraft
talosctl kubeconfig
```

agones
``` bash
helm repo add agones https://agones.dev/chart/stable
helm repo update

kubectl create namespace java-mc
kubectl create namespace bedrock-mc

helm install my-release agones/agones \
  --namespace agones-system --create-namespace \
  --set "gameservers.namespaces={default,java-mc,bedrock-mc}"
```
