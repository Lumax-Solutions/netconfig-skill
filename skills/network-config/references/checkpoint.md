# Check Point — Gaia R81.x

Part of the `network-config` skill. Read `../SKILL.md` first for the workflow and safety rules.

## Check Point (Gaia R81.x)

Two layers: **Gaia OS** (clish) for interfaces/routing; **security policy** via SmartConsole or the Management API, then *Publish* and *Install Policy*.
Gaia clish, on the gateway:
```
set interface eth1 ipv4-address 10.0.0.1 mask-length 24
set interface eth1 state on
set static-route default nexthop gateway address 203.0.113.1 on
set static-route 10.1.0.0/16 nexthop gateway address 10.0.0.254 on
save config
```
Management API, on the management server (expert mode):
```
mgmt_cli login user admin > id.txt
mgmt_cli add host name WEB-SRV ip-address 10.0.0.10 -s id.txt
mgmt_cli add access-rule layer "Network" position top name "Allow-Web" source Any destination WEB-SRV service https action Accept track.type Log -s id.txt
mgmt_cli publish -s id.txt
mgmt_cli install-policy policy-package "Standard" targets.1 "GW1" -s id.txt
```
NAT: automatic NAT on objects (hide/static) or manual NAT rules. Troubleshoot: `fw stat`, `cpstat fw`,
`fw ctl zdebug + drop` (drops in real time; on busy/Maestro gateways prefer `fw ctl debug -m fw + drop` + `fw ctl kdebug`), `fw monitor -F "10.0.0.5,0,0,0,0"` (order src,sport,dst,dport,proto; 0 = any; up to 5 `-F` OR'd; don't run together with zdebug), `fw tab -t connections -s`,
`vpn tu` (tunnel utility), `cphaprob state` / `cphaprob -a if` (ClusterXL), `cpview`. Backup: `add backup local` / snapshots.
