# runbook-generator

> **Service name + architecture notes → complete operational runbook.** Step-by-step incident response, escalation paths, decision trees, rollback procedures, post-mortem templates. Exports to Markdown.

[![PyPI](https://img.shields.io/pypi/v/runbook-generator?style=flat)](https://pypi.org/project/runbook-generator/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Quickstart

```bash
pip install runbook-generator

# Quick runbook from service name + stack
python -m runbook_generator "payment-service" --stack postgres redis kubernetes --markdown runbook.md

# From architecture doc
python -m runbook_generator architecture.md --type incident_response --markdown runbook.md

# Deployment runbook
python -m runbook_generator "auth-service" --type deployment --markdown deploy.md
```

## Runbook types

`incident_response` · `deployment` · `maintenance` · `scaling` · `recovery` · `monitoring`

## What's generated

Each runbook includes:
- **Steps** with exact commands, expected output, what to do if it fails
- **Decision tree** for triage (observable symptom → action)
- **Escalation path** — L1/L2/L3 with triggers and SLAs
- **Rollback procedure** with trigger condition and verification steps
- **Common issues** — symptom → likely cause → fix
- **Post-incident checklist** and post-mortem template
- **Monitoring** — which alerts trigger this, logs to check, metric thresholds

## License
MIT © [Alper Nabil Gabra Zakher](https://github.com/AlperNab)
