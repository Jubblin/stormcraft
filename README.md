# Stormcraft

Framework to deploy and configure a Minecraft cluster for the kids.

**Build path (Proxmox):** local [Omni](omni/README.md) provisions Talos VMs via
the Proxmox infra provider and opinionated machine profiles; Cilium replaces
kube-proxy. Manual `talosctl` fallback lives in [talos/README.md](talos/README.md).
Local Docker Desktop / `talosctl cluster create` notes are in
[testbed.md](testbed.md) only (not the real target).

## Todo list

- Identify hosting requirements
- Setup testbed
  - [Document methodology](testbed.md)
  - [Omni + Proxmox machine profiles](omni/README.md)
  - [Talos cluster build (manual fallback)](talos/README.md)
- Java or Bedrock?
- [Shulker operator to deploy Minecraft?](https://github.com/jeremylvln/Shulker)
- [Agones](https://agones.dev/site/)?
- [Geyser Bedrock clients to Java server](https://geysermc.org/)
