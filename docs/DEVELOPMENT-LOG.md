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
- [x] First Cage graphical session tested.
- [x] Touchscreen browser interaction verified.
- [x] SvxLink-Touch interface implemented.
- [x] Dashboard API integration implemented.
- [x] Automatic startup configured.
- [ ] Screen saver implemented.
- [x] Automated installer completed.

## Next Milestone

Launch a graphical application under Cage on the Raspberry Pi 3B and verify touchscreen operation without installing a conventional desktop environment.
## Development log:
Installer V0.2 startup passed; transient warnings observed. Temporary startup logging enabled for diagnosis. This diagnostic logging should not become a permanent installer feature unless needed.

## 27 October 2026 — Cage startup diagnostics resolved.

Cage/libseat reports that /run/seatd.sock is unavailable, skips that backend and uses systemd-logind. Touchscreen, Chromium and Dashboard operate successfully. These startup messages are informational, not installation failures. No corrective action required.
## 27 October 2026 — Installer V0.2: Unattended Boot Successful

### Test platform
- Raspberry Pi 3B
- Raspberry Pi OS Lite, Debian 13 Trixie, arm64
- 800 x 480 DSI touchscreen
- Cage Wayland compositor
- Chromium kiosk browser
- SvxLink 26.05.2
- SvxLink-Dash V4.1

### Verified
- Installer repeat execution successful
- tty2 automatic login operational
- systemd console activation service operational
- Automatic switching to tty2 successful
- Cage and Chromium started without intervention
- Full SvxLink Dashboard displayed after reboot
- Temporary startup diagnostics removed
- Repository startup script restored

### Outcome
Installer V0.2 successfully provides an unattended
touchscreen kiosk environment.

### Next development phase
Design and implement the native SvxLink-Touch interface,
optimised for the 800 x 480 touchscreen.

The existing SvxLink-Dash V4.1 API will provide node status
and, where authorised, control functionality.

## 27 October 2026 — V0.3 Welcome Screen and Screensaver

### Completed
- SvxLink-Touch web interface running on port 8080
- Existing SvxLink-Touch logo displayed at startup
- Touch anywhere on the logo to enter the application
- Automatic return to the logo after inactivity
- Default inactivity timeout: 5 minutes
- Inactivity timer reset by touchscreen interaction
- Timeout can be disabled by setting INACTIVITY_MINUTES to 0
- No interruption to SvxLink or Dashboard services
- Fully unattended Raspberry Pi startup retained

### Validation
- Welcome screen displayed: PASS
- Touch-to-enter navigation: PASS
- Automatic return to logo: PASS
- Touch-to-reopen after timeout: PASS

### Next Development Phase
V0.4 — Node Status Interface

Use the existing SvxLink-Dash V4.1 API to provide:
- Local node selection by default
- Last selected node when no local node is available
- Saved remote nodes using LAN, hostname or Tailscale addresses
- Receiver and transmitter status
- Reflector and talkgroup information
- Support for SimplexLogic, RepeaterLogic and radio-less nodes

## 27 October 2026 — V0.4 Multi-Node Selection Validated

### Completed
- Touch-sensitive title bar opens node-selection overlay
- Configured nodes retrieved through /api/nodes
- Node status retrieved through /api/node-status
- Local and remote node switching tested successfully
- Existing four-panel status layout preserved
- Five-second status polling retained
- No changes required to SvxLink or SvxLink-Dash

### Live Test
- Local node: 192.168.1.90 — PASS
- Remote node: 192.168.1.214 (MB5HT) — PASS
- Switching in both directions — PASS

### Next Task
Separate installation-specific node configuration from the
public GitHub repository while preserving existing configured nodes.

## 27 October 2026 — V0.4 Node Configuration Migration

### Completed
- Separated installation-specific node configuration from GitHub
- Added generic config/nodes.example.json
- Installed node configuration stored in /etc/svxlink-touch/nodes.json
- Installer preserves existing node configuration
- Uninstaller preserves existing node configuration
- Python web server reads installed node configuration
- Local and remote node selection retained

### Validation
- Local node API: PASS
- Remote node API: PASS
- Title-bar node selection: PASS
- Switching between local and remote nodes: PASS
- Existing touchscreen layout: PASS

### Outcome
SvxLink-Touch now supports installation-specific node lists
without embedding individual node addresses in the public
repository or overwriting them during upgrades.