# v1.2.1 activation smoke test

**Eight of eight intended matches loaded the installed skill. Zero of four controls loaded it.**

| Case | Request | Expected | Loaded |
|---|---|---|---|
| 01_cisco_vlan | Catalyst VLAN and trunk change | Yes | Yes |
| 02_fortigate_publish | Publish an internal web server | Yes | Yes |
| 03_juniper_bgp | Juniper BGP setup in Arabic | Yes | Yes |
| 04_mikrotik_guest | Guest VLAN isolation | Yes | Yes |
| 05_vpn_troubleshoot | FortiGate-Cisco VPN troubleshooting | Yes | Yes |
| 06_config_review | Pasted Cisco configuration review | Yes | Yes |
| 07_vendor_migration | ASA to Palo Alto migration | Yes | Yes |
| 08_linux_firewall | nftables IPv4/IPv6 SSH and HTTPS | Yes | Yes |
| 09_general_networking | Explain TCP versus UDP | No | No |
| 10_python_network_script | Python hostname resolution | No | No |
| 11_conceptual_routing | Explain routing fundamentals | No | No |
| 12_python_http | Python HTTPS/JSON example | No | No |

## Evidence and method

Twelve separate fresh ephemeral CLI sessions in empty working directories. Host skill discovery enabled; shell reads and skill search available. Installed v1.2.1 remained in its ordinary personal skill location. No skill names, paths, contents, prior conversation or expected results were inserted into prompts. The original advice-only suffix is retained by the harness. User configuration ignored, web search disabled, read-only sandbox.

Activation required an observed completed read of `network-config/SKILL.md`, exit code zero, and more than 100 output characters. An announcement alone did not count. Every positive case met that criterion. Vendor references were also read for all positives except VPN troubleshooting, which read the core only. Controls contained no such read. Sanitized relative read evidence is in `activation-results.json`; raw commands, local paths and event IDs were removed. The old field called `bytes` actually counted characters; the sanitized field is accurately named `output_characters`.

## Limits

One generation per prompt with an unpinned CLI default model. CLI activation only, not desktop routing, answer correctness, or device validation. Normal skill discovery was enabled, but custom user config/hooks were excluded. Successful small samples do not guarantee recall/precision for all future wording. Expected results are test-author judgments, preserved unchanged. A failed or incomplete future run is unknown, not a valid negative.

The parser recognizes this CLI version's completed `command_execution` events. Future tool schemas or non-shell readers may need parser updates; lack of a recognized read should be investigated before editing the description. All original positive reads were shell commands.

Final answers are in `../sample-outputs/activation/`. No description tuning or installed skill changes were made during the activation test.
