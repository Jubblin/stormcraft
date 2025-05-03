# Testbed

## Software
- Docker Desktop
- talosctl to create clusters
  - [Talos quickstart](https://www.talos.dev/v1.10/introduction/quickstart/)

``` bash
talosctl cluster create --name stormcraft
```

agones
``` bash
helm repo add agones https://agones.dev/chart/stable
helm repo update
helm install my-release --namespace agones-system --create-namespace agones/agones
```

``` bash
kubectl create namespace java-mc
kubectl create namespace bedrock-mc
helm install my-release agones/agones --set "gameservers.namespaces={default,java-mc, bedrock-mc}" --namespace agones-system
```
