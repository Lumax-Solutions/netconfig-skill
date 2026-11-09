# Host & cloud firewalls — UFW, nftables, iptables, Windows, AWS, Azure, GCP, Kubernetes

Part of the `network-config` skill. Read `../SKILL.md` first for the workflow and safety rules.

## Host-based & cloud firewalls (servers, cloud, Kubernetes)

Same principles (default deny inbound, least privilege, allow established) applied on the host or cloud layer — often in addition to the perimeter firewall.

The admin network `10.0.99.0/24` in these examples is a placeholder: replace it with the address you
connect from (`echo $SSH_CLIENT` shows it on Linux) or you will lock yourself out.

**UFW (Ubuntu/Debian):**
```
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow from 10.0.99.0/24 to any port 22 proto tcp   # SSH only from admin net
sudo ufw limit 22/tcp                                        # or rate-limit SSH if it must be public
sudo ufw allow 443/tcp
sudo ufw enable
sudo ufw status numbered      # delete with: sudo ufw delete <n>
```
Note: Docker-published ports bypass UFW (Docker writes its own iptables rules) — bind containers to `127.0.0.1:` or filter in the `DOCKER-USER` chain.

**nftables (modern Linux, `/etc/nftables.conf`):**
```
table inet filter {
  chain input {
    type filter hook input priority 0; policy drop;
    ct state established,related accept
    ct state invalid drop
    iif "lo" accept
    ip protocol icmp accept
    meta l4proto ipv6-icmp accept
    ip saddr 10.0.99.0/24 tcp dport 22 accept
    tcp dport { 80, 443 } accept
    log prefix "nft-drop: " limit rate 5/minute counter drop
  }
  chain forward { type filter hook forward priority 0; policy drop; }
  chain output  { type filter hook output priority 0; policy accept; }
}
```
Apply `sudo nft -c -f /etc/nftables.conf` (check) → `sudo nft -f /etc/nftables.conf`; persist with `systemctl enable nftables`. Inspect `sudo nft list ruleset`.
Migrating from iptables: `iptables-save > rules.v4` → `iptables-restore-translate -f rules.v4 > rules.nft`, review, then load.

**iptables (legacy):**
```
iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
iptables -A INPUT -i lo -j ACCEPT
iptables -A INPUT -p tcp -s 10.0.99.0/24 --dport 22 -j ACCEPT
iptables -A INPUT -p tcp -m multiport --dports 80,443 -j ACCEPT
iptables -P INPUT DROP
netfilter-persistent save
```
To keep the rules after a reboot, `netfilter-persistent save` (Debian/Ubuntu, package
`iptables-persistent`) writes `/etc/iptables/rules.v4` and `rules.v6`; on RHEL-family systems with
`iptables-services`, use `service iptables save`.
Adding the allow rules before the DROP policy reduces the risk of cutting off your own SSH session, but existing rules (an earlier DROP/REJECT, or a different source address than you expect) can still block it — check `iptables -S` first.
Over SSH, arm a rollback before pasting: `iptables-save > /root/fw.bak` and
`(sleep 300 && iptables-restore < /root/fw.bak) &`, then kill that job once a new session works.
`iptables-save` persists the rules only with `iptables-persistent` / `netfilter-persistent`.

**Windows Defender Firewall (PowerShell):**
`New-NetFirewallRule -DisplayName "Allow RDP from admin" -Direction Inbound -Protocol TCP -LocalPort 3389 -RemoteAddress 10.0.99.0/24 -Action Allow`; inspect `Get-NetFirewallRule | Where Enabled -eq True`.

**Cloud:**
- **AWS:** Security Groups are stateful, allow-only, attached to ENIs; reference other SGs instead of IPs for tiers (web-SG → app-SG → db-SG). NACLs are stateless, ordered, per subnet — need return-traffic rules for ephemeral ports 1024-65535. CLI: `aws ec2 authorize-security-group-ingress --group-id sg-xxx --protocol tcp --port 443 --cidr 0.0.0.0/0`. Terraform: `aws_security_group` + `aws_vpc_security_group_ingress_rule`.
- **Azure:** NSGs (stateful, priority 100–4096, lowest number wins) on subnet and/or NIC — both apply; use Application Security Groups for tiers; Azure Firewall for central egress filtering. `az network nsg rule create -g RG --nsg-name NSG -n Allow-HTTPS --priority 100 --direction Inbound --access Allow --protocol Tcp --destination-port-ranges 443`.
- **GCP:** VPC firewall rules are stateful, priority-based, target by network tag or service account; implied deny ingress / allow egress. `gcloud compute firewall-rules create allow-https --network=VPC --allow=tcp:443 --target-tags=web --source-ranges=0.0.0.0/0`.
- Never expose SSH/RDP/databases to `0.0.0.0/0`; prefer a bastion, AWS SSM Session Manager, Azure Bastion or GCP IAP.

**Kubernetes NetworkPolicy** (needs a CNI that enforces it — Calico, Cilium, etc.):
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: { name: default-deny, namespace: prod }
spec: { podSelector: {}, policyTypes: [Ingress, Egress] }
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: { name: api-from-web, namespace: prod }
spec:
  podSelector: { matchLabels: { app: api } }
  policyTypes: [Ingress]
  ingress:
  - from: [ { podSelector: { matchLabels: { app: web } } } ]
    ports: [ { protocol: TCP, port: 8080 } ]
```
With default-deny egress, remember to allow DNS (UDP/TCP 53 to kube-dns).
