# Azure Application Notes

Azure Front Door receives public HTTPS traffic and forwards approved traffic to Application Gateway WAF. Application Gateway routes traffic to workloads running in AKS. Workloads retrieve secrets from Key Vault and store application data in Azure Database for PostgreSQL. GitHub Actions runs Terraform to provision cloud resources and deploy changes. Prometheus collects metrics, Grafana displays dashboards, and Log Analytics stores diagnostic logs.

Unknowns: regions, private DNS, private endpoint names, exact namespaces, alert routing, HA/DR posture, and owner teams.
