# Answer-quality smoke tests

These are the original parent-assistant checklist grades, not newly generated scores. No independent blind grader or live appliance was used. Cases and rubric are unchanged. Each condition answered all three cases in one fresh session.

| Version | Case | Without skill | With skill |
|---|---|---:|---:|
| v1.2.0 | A: existing FortiGate conflicts | 7/8 | 8/8 |
| v1.2.0 | B: Cisco remote VTY restriction | 8/8 | 8/8 |
| v1.2.0 | C: unknown MikroTik version/path | 4/4 | 4/4 |
| v1.2.0 | **Total** | **19/20** | **20/20** |
| v1.2.1 | A: existing FortiGate conflicts | 6/8 | 8/8 |
| v1.2.1 | B: Cisco remote VTY restriction | 8/8 | 8/8 |
| v1.2.1 | C: unknown MikroTik version/path | 4/4 | 4/4 |
| v1.2.1 | **Total** | **18/20** | **20/20** |

v1.2.0 baseline: missed explicit blocked-traffic and existing-service acceptance checks. v1.2.1 baseline: additionally omitted a backup step. Both skill-assisted answers included these. Cisco and MikroTik baselines already met the original checklist. Baseline variation illustrates why these differences are not a reliable effect-size estimate.

## Correctness finding outside the checklist

The v1.2.0 reference incorrectly said `match-vip` defaults to disabled throughout FortiOS 7.x. Its answer repeated that default. The baseline also asserted that the earlier broad deny necessarily blocked the VIP, although the actual setting was unspecified. Thus 20/20 means checklist compliance, not complete factual correctness.

Fortinet documents the default as disabled through 7.2.3 and enabled in subsequent versions. v1.2.1 distinguishes new policies from upgraded policies and instructs the agent to inspect actual state. The v1.2.1 answer requested:

```text
show full-configuration firewall policy 12 | grep match-vip
```

It described both possibilities conditionally and did not repeat the false default: **regression PASS**. It preserved the existing publication until an authorized, nonconflicting endpoint was selected. The new baseline still made an unconditional policy-order claim.

Source checked during the original test: [Fortinet staff technical note](https://community.fortinet.com/fortigate-3/troubleshooting-tip-vip-traffic-not-matching-the-firewall-policy-with-an-all-destination-140780).

## Observed overhead

| Version | Metric | Baseline | With skill |
|---|---|---:|---:|
| v1.2.0 | Seconds | 53.2 | 54.3 |
| v1.2.0 | Whitespace words | 776 | 1150 |
| v1.2.0 | Reported input tokens | 16242 | 35389 |
| v1.2.0 | Reported output tokens | 1316 | 1770 |
| v1.2.1 | Seconds | 42.4 | 46.1 |
| v1.2.1 | Whitespace words | 653 | 1114 |
| v1.2.1 | Reported input tokens | 21522 | 35511 |
| v1.2.1 | Reported output tokens | 1199 | 1680 |

Full relevant references were injected up front. Token counts include CLI context; neither timing nor overhead predicts on-demand skill use.

## Method and limits

- Fresh ephemeral sessions, same default CLI settings within each pair; exact model identifier was not pinned or captured. User configuration ignored. Host discovery and skill search disabled; no skill reads, browsing, or device commands were permitted. Relevant skill text was explicitly appended only in the treatment.
- One generation per condition, three cases bundled per answer. Parent-assistant grading, no blind independent review. No per-check grading records were captured; these are preserved aggregate grades.
- Answer quality of supplied content is tested, not automatic activation. No network equipment was accessed. No correctness guarantee, statistical significance, or broad vendor coverage is established.
- Static manifests record SHA-256 hashes of the five supplied files. Skill contents, event logs, session IDs and local paths are intentionally absent.
- Samples are in `../sample-outputs/v1.2.0/` and `../sample-outputs/v1.2.1/`.
