# Adversarial Review Prompt

Review the diagram as a hostile enterprise architecture reviewer, security architect, SRE, developer lead, and executive stakeholder.

## Completeness

- Are critical components missing?
- Are external dependencies, users, systems, data stores, and integrations represented?
- Are security, observability, and operations included?
- Are deployment and runtime boundaries clear?

## Accuracy

- Are any relationships invented without evidence?
- Are arrows directionally wrong?
- Are protocols, ports, APIs, or data flows mislabeled?
- Are cloud or platform services represented accurately?
- Are assumptions clearly separated from facts?

## Enterprise Quality

- Would an enterprise architect accept this diagram?
- Would a security architect understand trust boundaries?
- Would an SRE understand ownership and observability?
- Would a developer understand service or code flow?
- Would an executive understand the high-level structure?

## Security and Operations

- Does the diagram expose secrets, credentials, internal hostnames, private IPs, or customer data?
- Are privileged paths, authn/authz flows, and audit paths clear?
- Are single points of failure, HA/DR paths, monitoring, alerting, logs, rollback, and recovery visible where relevant?

Write findings, improve the model, then generate final XML.
