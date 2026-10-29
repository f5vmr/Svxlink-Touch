# SvxLink-Touch V0.4

**Local touchscreen status display and control for SvxLink, with remote-node monitoring.**

SvxLink-Touch provides a full-screen, touch-operated interface on a Raspberry Pi equipped with Pi-Touch available from various sources. It displays the selected node's receiver, transmitter, reflector and talkgroup state using information supplied by SvxLink-Dash. Its local control facility can select a talkgroup using DTMF; remote nodes are **monitoring-only**.

## 1. Essential prerequisite: SvxLink and SvxLink-Dash V4.1

**SvxLink-Touch is an optional addition to an already installed and operational SvxLink station. It is not an installer for SvxLink or SvxLink-Dash.**

**Before installing SvxLink-Touch, you must install SvxLink and SvxLink-Dash V4.1 using SvxLink-Bootstrap, complete the Dashboard configuration and build, and verify that SvxLink and its Dashboard are working.** Do not begin the Touch installation until these steps are complete.

Other requirements are:

- An operational local SvxLink installation with SvxLink-Dash V4.1.
- A compatible **800 × 480 touchscreen** known as a Pi-Touch connected to the Raspberry Pi. Other resolutions are not established as supported. 
- Network access for package installation, and connectivity to any remote Dashboards you wish to monitor.
- The existing `pi` account, or another established account selected through `SVXLINK_TOUCH_USER`.

SvxLink-Touch uses Cage and Chromium to present the display in kiosk mode; a desktop environment or Node.js is not required.

## 2. Install and configure SvxLink first — using SvxLink-Bootstrap

If the Raspberry Pi does **not** already have SvxLink and SvxLink-Dash V4.1 installed by Bootstrap, complete that installation **before going any further**.

It is quite possible that the SvxLink-Touch will run in an otherwise constructed SvxLink Node, but it will not be guaranteeed as it is untested.

The full, maintained setup instructions are available at:

**[SvxLink – Single/Multi Port Node Initial Setup](https://g4nab.co.uk/svxlink-single-node-initial-setup/)**

Follow that guide for the radio interface, credentials, SvxLink-Bootstrap installation, Dashboard configuration, and the final configuration build. The Bootstrap launcher documented there is:

```bash
curl -fsSL \
    https://raw.githubusercontent.com/f5vmr/Svxlink-Bootstrap/main/launch-bootstrap.sh | sudo sh
```

Bootstrap starts the guided installation process and supplies a browser URL containing an access token. Keep its terminal open while following the browser prompts. Complete the handover to **SvxLink-Dash V4.1**, configure the node, and use **Build** to apply the configuration. Prove normal SvxLink operation before proceeding.

This README does not duplicate the full Bootstrap/Dashboard installation and radio setup procedure. **Do not substitute a manually installed, unconfigured Dashboard for the completed Bootstrap and Dashboard workflow.**

### Verify SvxLink-Dash V4.1 before installing Touch

Once the Dashboard installation and configuration are complete, verify it responds from the Raspberry Pi that will run SvxLink-Touch:

```bash
sudo systemctl status svxlink --no-pager
sudo systemctl status svxlink-dash --no-pager
curl -fsS 'http://127.0.0.1:5000/api/status?port=1'
```

The URL above assumes the Dashboard is running locally on port **5000** and that port **1** is enabled. Use the Dashboard's actual listening port and enabled SvxLink port when they differ. A successful HTTP response containing status data establishes that the API is reachable; also verify normal radio/node operation in the Dashboard itself.

**If `/api/status` does not respond, resolve the Dashboard installation or configuration first.** SvxLink-Touch depends on this status API for its four status panels. Installing Touch will not repair a nonfunctional Dashboard.

## 3. Install SvxLink-Touch

Only after completing §2, on the **same Raspberry Pi** that hosts the local SvxLink and Dashboard installation:

```bash
cd /opt
sudo git clone https://github.com/f5vmr/Svxlink-Touch.git svxlink-touch
cd /opt/svxlink-touch
sudo bash install/install-touch.sh
```

The installer installs the touchscreen kiosk components, configures the loopback-only web service and DTMF control socket, installs the restricted configuration helper, and sets up automatic kiosk start on tty2. Existing node and talkgroup configuration files are preserved when present.

The touchscreen interface is served locally at `http://127.0.0.1:8080/` using Chromium in kiosk mode. It is intentionally bound to the Raspberry Pi loopback interface and is not a remotely published control website.

Check the installed service and control socket:

```bash
sudo systemctl status svxlink-touch-web.service --no-pager
sudo systemctl status svxlink-touch-control.socket --no-pager
```

After installation, a reboot may be used to check automatic kiosk startup:

```bash
sudo reboot
```

## 4. First use

The normal status screen displays four panels:

- **RECEIVER** — current receiver status.
- **TRANSMITTER** — current transmitter status.
- **REFLECTOR** — connected reflector information.
- **TALKGROUP** — current talkgroup information; touching the panel opens talkgroup selection.

The footer shows the node type, **Nodes** and **Talkgroups** management buttons, and the application version.

Use the node selection control in the heading to select a configured node. The node selection screen is separate from the **Nodes** management button.

## 5. Local and remote nodes

Touch **Nodes** in the footer to open **Manage Remote Nodes**.

- **Add Remote Node** — enter the node name, address and port using the touchscreen keyboard; test connectivity and save.
- **Edit** — choose a configured remote node to change its details.
- **Remove** — remove a configured remote node after confirmation.
- **Close** — return to the status display.

The remote SvxLink-Dash must be reachable from the Raspberry Pi over its network, whether a LAN, VPN/Tailscale or another authorised route. Enter the actual host/address and HTTP port; do not include `/api/status` as part of the host name. Remote nodes need an operating SvxLink-Dash `/api/status` endpoint. The default local Dashboard example is `http://127.0.0.1:5000`.

**Remote-node control is intentionally disabled.** Selecting a remote node changes only the information displayed. DTMF commands are permitted solely for the configured local node.

Node configuration is stored in:

```text
/etc/svxlink-touch/nodes.json
```

The installer preserves an existing node configuration during upgrades.

## 6. Talkgroup favourites

Touch **Talkgroups** in the footer to manage the locally stored favourite talkgroup numbers.

- **Add Talkgroup:** enter a number on the on-screen numeric keypad, then **Save**.
- **Edit:** select an existing favourite, enter the replacement number and **Save**.
- **Remove:** select a favourite, press **Remove**, and then **Confirm Remove**.
- **Close:** return to the status display.

A talkgroup's displayed name is the number itself. Talkgroup names and the main SvxLink/reflector configuration are administered through SvxLink-Dash, not through this touchscreen editor. Duplicate and invalid numbers are rejected.

Favourites are stored in:

```text
/var/lib/svxlink-touch/talkgroups.json
```

The file has the following format:

```json
{
    "favorites": [
        {"name": "235", "number": 235},
        {"name": "91", "number": 91}
    ]
}
```

The **TALKGROUP** status panel is the separate selection/control interface. For the local node, selecting and confirming TG 235 sends **`91235#`** through the local SvxLink DTMF control path (`91` + talkgroup number + `#`). Adding, editing or removing a favourite **never sends DTMF**.

Locally monitored talkgroups are derived from the existing SvxLink configuration and are not edited by the favourites manager. The same favourites can be displayed while monitoring remote nodes, but remote talkgroup transmission is disabled.

## 7. Updating an existing installation

On the Mac development computer, commit and push reviewed changes to `main`. Then, on the touchscreen Raspberry Pi:

```bash
cd /opt/svxlink-touch
sudo git pull origin main
sudo bash install/install-touch.sh
```

The installer restarts the touchscreen web service, DTMF control socket and kiosk login. Existing node configuration and talkgroup favourites are preserved if already present, but maintain independent backups before upgrades.

Backup examples:

```bash
sudo cp -a /etc/svxlink-touch/nodes.json /etc/svxlink-touch/nodes.json.backup
sudo cp -a /var/lib/svxlink-touch/talkgroups.json /var/lib/svxlink-touch/talkgroups.json.backup
```

## 8. Service checks and troubleshooting

Check the local web service:

```bash
sudo systemctl status svxlink-touch-web.service --no-pager
sudo journalctl -u svxlink-touch-web.service -n 50 --no-pager
curl -I http://127.0.0.1:8080/
```

Check the local DTMF service:

```bash
sudo systemctl status svxlink-touch-control.socket --no-pager
sudo journalctl -u svxlink-touch-control.service -n 50 --no-pager
```

Check automatic kiosk start:

```bash
sudo systemctl status getty@tty2.service --no-pager
sudo systemctl status svxlink-touch-console.service --no-pager
```

If a node appears offline, first verify its Dashboard status endpoint from the touchscreen Raspberry Pi, using that node's actual host, port and API route. Check the network/VPN path and configuration saved in **Nodes**. An unreachable dashboard will not prevent other configured nodes from being monitored.

If talkgroup control fails, verify that **the local node is selected**, SvxLink is running and its configured control interface is accessible. Do not attempt to enable remote DTMF control by changing the user interface.

## 9. Important file locations

| Path | Purpose |
| --- | --- |
| `/opt/svxlink-touch/` | Application checkout |
| `/opt/svxlink-touch/install/install-touch.sh` | Installer and upgrade script |
| `/etc/svxlink-touch/nodes.json` | Persistent node configuration |
| `/var/lib/svxlink-touch/talkgroups.json` | Persistent talkgroup favourites |
| `/usr/local/lib/svxlink-touch/svxlink_touch_node_config.py` | Restricted configuration helper |
| `/run/svxlink-touch/control.sock` | Local DTMF control socket |
| `http://127.0.0.1:8080/` | Local-only touchscreen web interface |

## 10. Project and credits

Repository: <https://github.com/f5vmr/Svxlink-Touch>

SvxLink was created by Tobias Blomberg, SM0SVX. SvxLink-Touch is developed by Chris Jackson, G4NAB, for SvxLink installations using SvxLink-Dash. It is an optional touchscreen addition, not a replacement for SvxLink or SvxLink-Dash.

---

**Release:** V0.4. **Documentation:** Combined installation and operator reference. **Installation order:** SvxLink-Bootstrap → SvxLink-Dash V4.1 configured and working → SvxLink-Touch.
