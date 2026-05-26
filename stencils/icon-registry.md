# Icon Registry

The helper uses real diagrams.net built-in vendor stencils by default for recognized cloud and platform service names: Azure (`mxgraph.azure.*`), AWS (`mxgraph.aws4.*`), GCP (`mxgraph.gcp2.*`), and Kubernetes (`mxgraph.kubernetes.*`). These stencil libraries ship with diagrams.net itself — no proprietary icon pack or manifest is required. Unrecognized labels fall back to vendor-colored generic shapes. A licensed third-party icon pack (see "Local Licensed Vendor Icon Packs" below) still takes precedence when configured.

## Built-In Categories

- General: actor, user, process, repository, artifact.
- Application: frontend, API, backend, worker.
- Data: database, cache, queue.
- Cloud and network: cloud, CDN, gateway, WAF, firewall, network.
- Security: identity, secret store, security controls.
- Platform: Kubernetes, container, server.
- DevOps: Terraform, Ansible, build/deploy processes.
- Operations: monitoring, logging, dashboard.

## Built-In Vendor Stencils (default)

The helper resolves recognized service names to the bundled diagrams.net vendor stencil libraries:

- **Azure** (`mxgraph.azure.*`): AKS, App Service, Functions, Container Apps, VM, Front Door, Application Gateway, Load Balancer, Traffic Manager, CDN, DNS, VNet, Firewall, Bastion, ExpressRoute, Private Link, Key Vault, Entra ID/AAD, Managed Identity, Sentinel, Defender, Monitor, Log Analytics, Application Insights, Cosmos DB, Azure SQL, Synapse, Service Bus, Event Hubs, Event Grid, API Management, Logic Apps, Storage Accounts, Backup, Data Factory, Databricks, Cognitive Services, ML, and more.
- **AWS** (`mxgraph.aws4.*` via `resourceIcon`): Lambda, EC2, ECS, EKS, Fargate, ECR, S3, EBS, EFS, FSx, RDS, Aurora, DynamoDB, ElastiCache, Redshift, DocumentDB, Neptune, CloudFront, Route 53, API Gateway, ELB/ALB/NLB, VPC, Transit Gateway, Direct Connect, IAM, KMS, Secrets Manager, ACM, WAF, Shield, GuardDuty, Security Hub, Cognito, Inspector, Macie, SQS, SNS, EventBridge, Step Functions, MQ, Kinesis, MSK, Athena, EMR, Glue, QuickSight, CloudWatch, CloudTrail, Config, Systems Manager, X-Ray, CloudFormation, Organizations, SageMaker, Bedrock, Rekognition, Comprehend, and more. Category-specific fill colors are applied automatically (compute=orange, storage=green, database=purple, network=violet, security=red, integration/management=pink, AI=teal).
- **GCP** (`mxgraph.gcp2.*`): GKE, Compute Engine, Cloud Functions, Cloud Run, App Engine, Cloud Storage, Filestore, Cloud SQL, Cloud Spanner, Bigtable, Firestore, BigQuery, Memorystore, Cloud Load Balancing, Cloud CDN, Cloud DNS, Cloud Armor, Cloud VPN, Interconnect, VPC, IAM, KMS, Secret Manager, Pub/Sub, Cloud Tasks, Cloud Scheduler, Cloud Monitoring/Logging/Trace, Vertex AI, and more.
- **Kubernetes** (`mxgraph.kubernetes.*` via `prIcon`): Pod, Deployment, ReplicaSet, StatefulSet, DaemonSet, Job, CronJob, Service, Ingress, Endpoint, NetworkPolicy, ConfigMap, Secret, PV, PVC, StorageClass, Namespace, ServiceAccount, Role, ClusterRole, Node, API server, etcd, kubelet, scheduler, controller manager.

## Fallback Rule

If a label doesn't match a recognized vendor service name, the helper falls back to a vendor-tagged generic shape (rounded rectangle in vendor color). The `validate_vendor_shape_accuracy` validator emits a warning when a node label clearly names a vendor but resolves to a generic shape — that's the signal to add a new alias rather than accept the gap.

## Adding Mappings

- **Add a new vendor service**: edit `src/drawio_generator/builtin_vendor_shapes.py` and add an entry to `_AZURE_SHAPES`, `_AWS_SHAPES`, `_GCP_SHAPES`, or `_K8S_SHAPES`. Use the exact mxgraph stencil suffix (e.g. `cosmos_db` for `mxgraph.azure.cosmos_db`).
- **Add a generic shape**: edit `src/drawio_generator/icon_registry.py` and add to `STYLE_REGISTRY`. Keep styles simple, readable, and compatible with diagrams.net XML. Prefer muted enterprise colors for non-vendor shapes; vendor brand colors are applied by the built-in vendor stencil resolver.

## Local Licensed Vendor Icon Packs

To opt into officially licensed vendor icons, drop a `manifest.json` next to the icons under `stencils/<vendor>/`. The manifest must explicitly attest to the license terms:

```json
{
  "vendor": "azure",
  "license_acknowledged": true,
  "license_notice": "Azure icons licensed under enterprise agreement EA-123",
  "shapes": {
    "azure kubernetes service": "shape=mscae/Kubernetes_Services;html=1;...",
    "key vault": "shape=mscae/Key_Vaults;html=1;..."
  }
}
```

Behavior:

- The resolver only marks an icon `official: true` when a manifest is present, `license_acknowledged` is `true`, and the service name matches a manifest entry.
- Without a manifest, every vendor service falls back to safe diagrams.net built-in shapes and the `license_notice` records that no official icon was embedded.
- Manifests that fail to parse or lack license acknowledgement are silently ignored for that vendor only.

Supported vendor keys today: `azure`, `aws`, `gcp`. Add additional vendors by including a matching `stencils/<vendor>/manifest.json` and corresponding `VENDOR_TERMS` entry in `icon_registry.py`.

For executive architecture pages, prefer icon-like built-in shapes that improve scanning without introducing proprietary icon dependencies:

- Source control: folder/repository.
- Tower, AWX, CI, and orchestration: process/controller.
- Customer targets: server-style infrastructure shapes.
- Databases and queues: cylinder and queue shapes.
- Reports and workbooks: document/note shapes.
- Vaults and secret stores: security-colored lock/vault fallback.
- SFS or external object storage: cloud/object-storage fallback.
- Consumers: actor/user shapes.
