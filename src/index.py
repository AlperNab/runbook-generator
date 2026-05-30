#!/usr/bin/env python3
"""
runbook-generator — system architecture + incident history → operational runbooks
Generates: step-by-step runbooks, decision trees, on-call playbooks,
escalation paths, post-mortem templates, SLO dashboards
"""
import anthropic, json, re, sys
from datetime import datetime, timezone
from pathlib import Path

SYSTEM = """You are a senior Site Reliability Engineer (SRE) with 15 years of production experience.
Generate clear, actionable operational runbooks that on-call engineers can follow at 3am.

Runbook principles:
- Assume minimal context — write for someone who wasn't in the original design meeting
- Use numbered steps, not paragraphs
- Include verification steps after each action
- List exact commands, not descriptions
- Decision trees for ambiguous situations
- Escalation paths should be explicit

Return ONLY valid JSON — no markdown, no explanation.

{
  "service_name": "string",
  "runbook_type": "incident_response|deployment|maintenance|scaling|recovery|monitoring",
  "title": "descriptive runbook title",
  "description": "1-2 sentences: what this runbook is for and when to use it",
  "severity_levels": ["P1","P2","P3"],
  "prerequisites": [
    {"tool":"string","purpose":"why it's needed","install_hint":"how to get it"}
  ],
  "quick_reference": {
    "summary": "3-4 bullet decision tree for quick triage",
    "key_metrics_to_check": ["metric name and where to find it"],
    "key_dashboards": ["dashboard name and URL pattern"]
  },
  "steps": [
    {
      "step": number,
      "title": "short action title",
      "description": "what to do and why",
      "commands": ["exact shell commands or API calls"],
      "expected_output": "what success looks like",
      "if_fails": "what to do if this step fails",
      "time_estimate_minutes": number,
      "requires_approval": true_or_false,
      "rollback_command": "string or null"
    }
  ],
  "decision_tree": [
    {
      "condition": "observable symptom or check",
      "if_true": "next step or action",
      "if_false": "next step or action"
    }
  ],
  "escalation_path": [
    {
      "level": "L1|L2|L3|executive",
      "trigger": "when to escalate to this level",
      "contact": "role or team name",
      "sla_minutes": number
    }
  ],
  "rollback_procedure": {
    "trigger": "when to initiate rollback",
    "steps": ["ordered rollback steps"],
    "verification": "how to verify rollback succeeded"
  },
  "post_incident": {
    "immediate_actions": ["within 1 hour of resolution"],
    "follow_up_actions": ["within 24 hours"],
    "post_mortem_template": {
      "incident_summary": "template",
      "timeline": "template",
      "root_cause": "template",
      "contributing_factors": "template",
      "impact": "template",
      "resolution": "template",
      "action_items": "template"
    }
  },
  "monitoring": {
    "alerts_that_trigger_this": ["alert names"],
    "key_logs_to_check": ["log location and grep pattern"],
    "metrics_to_watch": ["metric name, threshold, what breach means"]
  },
  "common_issues": [
    {
      "symptom": "what you observe",
      "likely_cause": "most common root cause",
      "fix": "specific remediation steps"
    }
  ],
  "last_tested": null,
  "owner": "team or person",
  "review_frequency": "quarterly|monthly|after_each_incident",
  "confidence": 0.0
}"""

def generate(
    service_name: str,
    runbook_type: str = "incident_response",
    architecture_notes: str = "",
    incident_history: str = "",
    tech_stack: list[str] | None = None
) -> dict:
    client = anthropic.Anthropic()
    context_parts = [
        f"Service: {service_name}",
        f"Runbook type: {runbook_type}",
        f"Tech stack: {', '.join(tech_stack)}" if tech_stack else "",
        f"Architecture:\n{architecture_notes}" if architecture_notes else "",
        f"Incident history / known issues:\n{incident_history}" if incident_history else "",
        f"Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
    ]
    context = "\n".join(p for p in context_parts if p)
    prompt = f"Generate an operational runbook for:\n\n{context}"

    resp = client.messages.create(
        model="claude-sonnet-4-20250514", max_tokens=4096, system=SYSTEM,
        messages=[{"role":"user","content":prompt}]
    )
    raw = re.sub(r'^```(?:json)?\s*','',resp.content[0].text.strip(),flags=re.MULTILINE)
    raw = re.sub(r'\s*```$','',raw,flags=re.MULTILINE)
    return json.loads(raw)

def generate_from_file(architecture_file: str, runbook_type: str = "incident_response", service: str = "") -> dict:
    path = Path(architecture_file)
    if not path.exists(): raise FileNotFoundError(f"Not found: {architecture_file}")
    text = path.read_text(encoding="utf-8", errors="replace")
    service_name = service or path.stem.replace("-"," ").replace("_"," ").title()
    return generate(service_name, runbook_type, architecture_notes=text[:20000])

def to_markdown(r: dict) -> str:
    lines = [
        f"# Runbook: {r.get('title','')}",
        f"> **Service:** {r.get('service_name','')} | **Type:** {r.get('runbook_type','')}",
        f"> **Owner:** {r.get('owner','?')} | **Review:** {r.get('review_frequency','?')}",
        "",
        r.get("description",""),
        "",
        "---",
        "",
        "## Quick Reference",
    ]
    qr = r.get("quick_reference",{})
    for item in qr.get("summary",[]): lines.append(f"- {item}")
    if qr.get("key_metrics_to_check"):
        lines += ["","**Key metrics:**"]
        for m in qr["key_metrics_to_check"]: lines.append(f"- {m}")

    lines += ["","---","","## Steps",""]
    for step in r.get("steps",[]):
        lines += [
            f"### Step {step.get('step','?')}: {step.get('title','')}",
            f"*~{step.get('time_estimate_minutes','?')} min{' | ⚠ Requires approval' if step.get('requires_approval') else ''}*",
            "",
            step.get("description",""),
            ""
        ]
        cmds = step.get("commands",[])
        if cmds:
            lines += ["```bash"] + cmds + ["```",""]
        if step.get("expected_output"):
            lines.append(f"✅ **Expected:** {step['expected_output']}")
        if step.get("if_fails"):
            lines.append(f"❌ **If fails:** {step['if_fails']}")
        if step.get("rollback_command"):
            lines.append(f"↩ **Rollback:** `{step['rollback_command']}`")
        lines.append("")

    lines += ["---","","## Escalation Path",""]
    for esc in r.get("escalation_path",[]):
        lines.append(f"**{esc.get('level','')}** — {esc.get('contact','')} | Trigger: {esc.get('trigger','')} | SLA: {esc.get('sla_minutes','?')}min")

    common = r.get("common_issues",[])
    if common:
        lines += ["","---","","## Common Issues",""]
        for ci in common:
            lines += [f"### {ci.get('symptom','')}", f"**Likely cause:** {ci.get('likely_cause','')}", f"**Fix:** {ci.get('fix','')}", ""]

    return "\n".join(lines)

def print_runbook(r: dict):
    print(f"\n{'═'*60}")
    print(f"  RUNBOOK: {r.get('title','')}")
    print(f"  Service: {r.get('service_name','?')} | Type: {r.get('runbook_type','?')}")
    print(f"{'═'*60}")
    print(f"\n  {r.get('description','')}")

    qr = r.get("quick_reference",{})
    if qr.get("summary"):
        print(f"\n  QUICK TRIAGE")
        for item in qr["summary"]: print(f"  • {item}")

    steps = r.get("steps",[])
    if steps:
        total_time = sum(s.get("time_estimate_minutes",0) for s in steps)
        print(f"\n  STEPS ({len(steps)} steps, ~{total_time} min total)")
        for s in steps:
            approval = " ⚠ APPROVAL" if s.get("requires_approval") else ""
            print(f"\n  [{s.get('step','?')}] {s.get('title','')}{approval} (~{s.get('time_estimate_minutes','?')}min)")
            print(f"       {s.get('description','')[:100]}")
            for cmd in s.get("commands",[])[:2]: print(f"       $ {cmd}")
            if s.get("if_fails"): print(f"       ❌ {s['if_fails']}")

    esc = r.get("escalation_path",[])
    if esc:
        print(f"\n  ESCALATION PATH")
        for e in esc:
            print(f"  {e.get('level','')} → {e.get('contact','')} | after {e.get('sla_minutes','?')}min | {e.get('trigger','')}")

    common = r.get("common_issues",[])
    if common:
        print(f"\n  COMMON ISSUES ({len(common)})")
        for c in common[:3]:
            print(f"  • {c.get('symptom','')}")
            print(f"    → {c.get('fix','')[:80]}")

    print(f"\n  Confidence: {int(r.get('confidence',0)*100)}%")
    print(f"{'═'*60}\n")

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Generate operational runbooks from system architecture")
    p.add_argument("service", help="Service name or architecture file path")
    p.add_argument("--type","-t",default="incident_response",
                   choices=["incident_response","deployment","maintenance","scaling","recovery","monitoring"])
    p.add_argument("--stack",nargs="+",help="Tech stack (e.g. postgres redis kubernetes)")
    p.add_argument("--incidents",default="",help="Known incidents or failure patterns file")
    p.add_argument("--json",action="store_true")
    p.add_argument("--markdown","-m",help="Save as markdown file")
    a = p.parse_args()

    if Path(a.service).exists():
        r = generate_from_file(a.service, a.type)
    else:
        incidents = Path(a.incidents).read_text() if a.incidents and Path(a.incidents).exists() else a.incidents
        r = generate(a.service, a.type, tech_stack=a.stack, incident_history=incidents)

    if a.markdown:
        Path(a.markdown).write_text(to_markdown(r), encoding="utf-8")
        print(f"Runbook saved to {a.markdown}")
    if a.json: print(json.dumps(r,indent=2,ensure_ascii=False))
    else: print_runbook(r)
