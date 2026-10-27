# SvxLink-Touch — Development Log

## Project Overview

SvxLink-Touch is a touchscreen monitoring and control interface for SvxLink installations.

The project will support two principal editions:

- **Operator Edition:** An Android client for connecting to compatible SvxReflectors, initially using Protocol 2.
- **Sysop Edition:** A touchscreen monitoring and control application connecting to SvxLink-Dash V4.1 installations locally or remotely, including through Tailscale.

The initial development platform is a Raspberry Pi 3B with an 800 × 480 DSI touchscreen.

## Development Baseline — 27 October 2026

### Hardware

| Component | Specification |
|---|---|
| Computer | Raspberry Pi 3B |
| Display | Pi Smart DSI touchscreen |
| Resolution | 800 × 480 |
| Touch controller | FocalTech FT5x06 |
| Input device | `/dev/input/event1` |
| Graphics device | `/dev/dri/card0` |
| Rendering device | `/dev/dri/renderD128` |

Touchscreen input and display operation verified.

### Operating System

Raspberry Pi OS Lite 64-bit, based on Debian 13 Trixie.

No full desktop environment installed.

### Graphical Environment

Installed using:

```bash
sudo apt update
sudo apt install -y cage chromium
```

Verified versions:

- Cage 0.3.1
- Chromium 155.0.8059.79

### Branding

The approved SvxLink-Touch logo will be used for:

- Application branding.
- Startup splash screen.
- Configurable screen saver.

Screen saver behaviour and inactivity timing remain to be implemented.

## Architectural Principles

1. SvxLink-Touch remains optional and independent of SvxLink operation.
2. Existing SvxLink-Dash V4.1 control mechanisms should be reused rather than duplicated.
3. Remote administrative operations require authenticated access.
4. The Operator Edition must not be restricted to Federation Family reflectors.
5. Protocol 2 is the initial target for the Operator Edition; Protocol 3 remains a possible future extension.
6. The touchscreen interface must support different display resolutions.
7. Installation should eventually be automated and reproducible.
8. Every tested implementation change should be recorded before inclusion in the installer.

## Current Development Status

- [x] Raspberry Pi OS Lite installed.
- [x] DSI display operational.
- [x] Touch input detected and tested.
- [x] DRM/KMS graphics devices confirmed.
- [x] Cage and Chromium installed.
- [x] Application logo selected.
- [x] Git repository created.
- [ ] First Cage graphical session tested.
- [ ] Touchscreen browser interaction verified.
- [ ] SvxLink-Touch interface implemented.
- [ ] Dashboard API integration implemented.
- [ ] Automatic startup configured.
- [ ] Screen saver implemented.
- [ ] Automated installer completed.

## Next Milestone

Launch a graphical application under Cage on the Raspberry Pi 3B and verify touchscreen operation without installing a conventional desktop environment.
