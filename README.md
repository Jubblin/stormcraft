# Stormcraft

Framework to deploy and configure a Minecraft cluster for the kids.

**Build path (Proxmox):** all Proxmox VMs are created via local
[Omni](omni/README.md) and the `omni-infra-provider-proxmox` provider, using
opinionated machine profiles; Cilium replaces kube-proxy. `talosctl` steps in
[talos/README.md](talos/README.md) are reference/fallback only, not how VMs
are actually provisioned. Local Docker Desktop / `talosctl cluster create`
notes are in [testbed.md](testbed.md) only (not the real target).

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
