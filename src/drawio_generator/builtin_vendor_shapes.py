"""Built-in diagrams.net vendor stencil shape strings.

diagrams.net ships with vendor stencil libraries (Azure, AWS, GCP, Kubernetes)
that are free to use in any ``.drawio`` file and require no external licensing.
This module maps service names to those bundled shape strings so vendor-aware
diagram generation produces real vendor icons by default, without requiring an
external icon-pack manifest.

A licensed third-party icon pack (see :mod:`icon_packs`) still takes precedence
when one is present and the service matches a manifest entry. This module is
the no-manifest baseline that replaces the previous "generic rounded rectangle
with a vendor-colored stroke" fallback for recognizable cloud and platform
service names.

The shape strings use the same ``shape=mxgraph.<family>.<name>`` references
diagrams.net itself emits when those vendor shape libraries are loaded, so
diagrams open correctly in both the desktop app and ``app.diagrams.net``.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BuiltinShape:
    """A vendor stencil entry resolved from the built-in shape libraries."""

    vendor: str
    drawio_style: str
    label: str
    category: str


# ---------------------------------------------------------------------------
# Azure: mxgraph.azure.* family
# ---------------------------------------------------------------------------

_AZURE_STYLE_TEMPLATE = (
    "sketch=0;outlineConnect=0;fontColor=#23A2D9;gradientColor=none;"
    "fillColor=#0072C6;strokeColor=#0072C6;dashed=0;"
    "verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;"
    "fontSize=12;shape=mxgraph.azure.{shape};"
)

# service-name -> mxgraph.azure shape suffix
_AZURE_SHAPES: dict[str, str] = {
    # Compute
    "azure kubernetes service": "kubernetes_services",
    "aks": "kubernetes_services",
    "azure app service": "app_services",
    "app service": "app_services",
    "azure functions": "function_apps",
    "function app": "function_apps",
    "azure container apps": "container_instances",
    "container apps": "container_instances",
    "azure container instances": "container_instances",
    "aci": "container_instances",
    "azure container registry": "container_registries",
    "acr": "container_registries",
    "azure batch": "batch_accounts",
    "azure virtual machine": "virtual_machine",
    "azure virtual machines": "virtual_machine",
    "azure vm": "virtual_machine",
    "vm scale set": "vm_scale_sets",
    "azure vmss": "vm_scale_sets",
    "azure service fabric": "service_fabric_clusters",
    # Networking / edge
    "azure front door": "front_doors",
    "front door": "front_doors",
    "azure application gateway": "application_gateways",
    "application gateway": "application_gateways",
    "azure load balancer": "load_balancers",
    "azure traffic manager": "traffic_manager_profiles",
    "traffic manager": "traffic_manager_profiles",
    "azure cdn": "cdn_profiles",
    "azure dns": "dns_zones",
    "azure virtual network": "virtual_networks",
    "vnet": "virtual_networks",
    "azure firewall": "firewalls",
    "azure bastion": "bastions",
    "azure vpn gateway": "vpn_gateways",
    "azure expressroute": "expressroute_circuits",
    "expressroute": "expressroute_circuits",
    "azure nat gateway": "nat",
    "azure private link": "private_link",
    "azure private endpoint": "private_endpoint",
    "azure ddos protection": "ddos_protection_plans",
    "azure web application firewall": "web_application_firewall_policies(waf)",
    # Data / databases
    "azure database for postgresql": "azure_database_postgresql_server",
    "azure database for mysql": "azure_database_mysql_server",
    "azure database for mariadb": "azure_database_mariadb_server",
    "azure sql database": "sql_database",
    "azure sql": "sql_database",
    "azure sql managed instance": "sql_managed_instance",
    "azure synapse analytics": "azure_synapse_analytics",
    "azure cosmos db": "cosmos_db",
    "cosmos db": "cosmos_db",
    "azure cache for redis": "cache_redis",
    "azure data lake storage": "data_lake_storage_gen1",
    "azure data lake": "data_lake_storage_gen1",
    "azure data factory": "data_factory",
    "azure databricks": "azure_databricks",
    # Storage
    "azure storage account": "storage_accounts",
    "storage account": "storage_accounts",
    "azure blob storage": "storage_accounts",
    "azure files": "storage_accounts",
    "azure queue storage": "storage_accounts",
    "azure table storage": "storage_accounts",
    "azure backup": "backup_vault",
    "azure site recovery": "site_recovery_vault",
    # Integration / messaging
    "azure service bus": "service_bus",
    "azure event hubs": "event_hubs",
    "event hubs": "event_hubs",
    "azure event grid": "event_grid_topics",
    "event grid": "event_grid_topics",
    "azure api management": "api_management_services",
    "api management": "api_management_services",
    "azure logic apps": "logic_apps",
    "logic apps": "logic_apps",
    # Identity / security
    "azure active directory": "azure_active_directory",
    "entra id": "azure_active_directory",
    "azure ad": "azure_active_directory",
    "aad": "azure_active_directory",
    "azure key vault": "key_vaults",
    "key vault": "key_vaults",
    "azure managed identity": "managed_identities",
    "managed identity": "managed_identities",
    "azure sentinel": "azure_sentinel",
    "microsoft sentinel": "azure_sentinel",
    "azure defender": "defender",
    "microsoft defender for cloud": "defender",
    "azure security center": "security_center",
    "azure information protection": "information_protections",
    "azure policy": "policy",
    "azure rbac": "role",
    # Observability / management
    "azure monitor": "monitor",
    "log analytics": "log_analytics_workspaces",
    "log analytics workspace": "log_analytics_workspaces",
    "application insights": "application_insights",
    "azure automation": "automation_accounts",
    "azure advisor": "advisor",
    "azure resource manager": "resource_groups",
    "resource group": "resource_groups",
    "azure subscription": "subscriptions",
    "azure tenant": "subscriptions",
    # AI / cognitive
    "azure openai": "cognitive_services",
    "azure cognitive services": "cognitive_services",
    "azure machine learning": "machine_learning",
}

_AZURE_CATEGORY_HINTS: dict[str, str] = {
    "key_vaults": "security",
    "azure_active_directory": "identity",
    "managed_identities": "identity",
    "defender": "security",
    "azure_sentinel": "security",
    "firewalls": "security",
    "security_center": "security",
    "policy": "security",
    "role": "security",
    "monitor": "observability",
    "log_analytics_workspaces": "observability",
    "application_insights": "observability",
    "advisor": "observability",
}


# ---------------------------------------------------------------------------
# AWS: mxgraph.aws4.* family using the resourceIcon wrapper
# ---------------------------------------------------------------------------

_AWS_STYLE_TEMPLATE = (
    "sketch=0;points=[[0,0,0],[0.25,0,0],[0.5,0,0],[0.75,0,0],[1,0,0],"
    "[0,1,0],[0.25,1,0],[0.5,1,0],[0.75,1,0],[1,1,0],"
    "[0,0.25,0],[0,0.5,0],[0,0.75,0],[1,0.25,0],[1,0.5,0],[1,0.75,0]];"
    "outlineConnect=0;fontColor=#232F3E;gradientColor=none;"
    "fillColor={fill};strokeColor=#ffffff;dashed=0;"
    "verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;"
    "fontSize=12;shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.{shape};"
)

# AWS uses category fill colors (compute=orange, storage=green, database=purple, etc.)
_AWS_FILL_COMPUTE = "#ED7100"
_AWS_FILL_CONTAINERS = "#ED7100"
_AWS_FILL_STORAGE = "#7AA116"
_AWS_FILL_DATABASE = "#C925D1"
_AWS_FILL_NETWORKING = "#8C4FFF"
_AWS_FILL_SECURITY = "#DD344C"
_AWS_FILL_INTEGRATION = "#E7157B"
_AWS_FILL_ANALYTICS = "#8C4FFF"
_AWS_FILL_MANAGEMENT = "#E7157B"
_AWS_FILL_AI = "#01A88D"

# service-name -> (mxgraph.aws4 resIcon suffix, category fill color)
_AWS_SHAPES: dict[str, tuple[str, str]] = {
    # Compute
    "aws lambda": ("lambda", _AWS_FILL_COMPUTE),
    "amazon lambda": ("lambda", _AWS_FILL_COMPUTE),
    "aws ec2": ("ec2", _AWS_FILL_COMPUTE),
    "amazon ec2": ("ec2", _AWS_FILL_COMPUTE),
    "ec2": ("ec2", _AWS_FILL_COMPUTE),
    "aws fargate": ("fargate", _AWS_FILL_CONTAINERS),
    "amazon ecs": ("elastic_container_service", _AWS_FILL_CONTAINERS),
    "aws ecs": ("elastic_container_service", _AWS_FILL_CONTAINERS),
    "amazon eks": ("elastic_kubernetes_service", _AWS_FILL_CONTAINERS),
    "aws eks": ("elastic_kubernetes_service", _AWS_FILL_CONTAINERS),
    "amazon ecr": ("elastic_container_registry", _AWS_FILL_CONTAINERS),
    "aws ecr": ("elastic_container_registry", _AWS_FILL_CONTAINERS),
    "aws batch": ("batch", _AWS_FILL_COMPUTE),
    "aws app runner": ("app_runner", _AWS_FILL_COMPUTE),
    "aws elastic beanstalk": ("elastic_beanstalk", _AWS_FILL_COMPUTE),
    # Storage
    "amazon s3": ("simple_storage_service_s3", _AWS_FILL_STORAGE),
    "aws s3": ("simple_storage_service_s3", _AWS_FILL_STORAGE),
    "s3": ("simple_storage_service_s3", _AWS_FILL_STORAGE),
    "amazon ebs": ("elastic_block_store", _AWS_FILL_STORAGE),
    "aws ebs": ("elastic_block_store", _AWS_FILL_STORAGE),
    "amazon efs": ("elastic_file_system", _AWS_FILL_STORAGE),
    "aws efs": ("elastic_file_system", _AWS_FILL_STORAGE),
    "aws backup": ("backup", _AWS_FILL_STORAGE),
    "aws storage gateway": ("storage_gateway", _AWS_FILL_STORAGE),
    "amazon fsx": ("fsx", _AWS_FILL_STORAGE),
    # Databases
    "amazon rds": ("rds", _AWS_FILL_DATABASE),
    "aws rds": ("rds", _AWS_FILL_DATABASE),
    "amazon aurora": ("aurora", _AWS_FILL_DATABASE),
    "aws aurora": ("aurora", _AWS_FILL_DATABASE),
    "amazon dynamodb": ("dynamodb", _AWS_FILL_DATABASE),
    "aws dynamodb": ("dynamodb", _AWS_FILL_DATABASE),
    "amazon elasticache": ("elasticache", _AWS_FILL_DATABASE),
    "aws elasticache": ("elasticache", _AWS_FILL_DATABASE),
    "amazon redshift": ("redshift", _AWS_FILL_DATABASE),
    "aws redshift": ("redshift", _AWS_FILL_DATABASE),
    "amazon documentdb": ("documentdb_with_mongodb_compatibility", _AWS_FILL_DATABASE),
    "amazon neptune": ("neptune", _AWS_FILL_DATABASE),
    "amazon timestream": ("timestream", _AWS_FILL_DATABASE),
    # Networking
    "amazon cloudfront": ("cloudfront", _AWS_FILL_NETWORKING),
    "aws cloudfront": ("cloudfront", _AWS_FILL_NETWORKING),
    "amazon route 53": ("route_53", _AWS_FILL_NETWORKING),
    "route 53": ("route_53", _AWS_FILL_NETWORKING),
    "aws route 53": ("route_53", _AWS_FILL_NETWORKING),
    "amazon api gateway": ("api_gateway", _AWS_FILL_NETWORKING),
    "aws api gateway": ("api_gateway", _AWS_FILL_NETWORKING),
    "aws elb": ("elastic_load_balancing", _AWS_FILL_NETWORKING),
    "aws elastic load balancer": ("elastic_load_balancing", _AWS_FILL_NETWORKING),
    "aws alb": ("elastic_load_balancing", _AWS_FILL_NETWORKING),
    "aws nlb": ("elastic_load_balancing", _AWS_FILL_NETWORKING),
    "aws vpc": ("vpc", _AWS_FILL_NETWORKING),
    "amazon vpc": ("vpc", _AWS_FILL_NETWORKING),
    "aws transit gateway": ("transit_gateway", _AWS_FILL_NETWORKING),
    "aws direct connect": ("direct_connect", _AWS_FILL_NETWORKING),
    "aws privatelink": ("privatelink", _AWS_FILL_NETWORKING),
    "aws global accelerator": ("global_accelerator", _AWS_FILL_NETWORKING),
    # Security / identity
    "aws iam": ("identity_and_access_management_iam", _AWS_FILL_SECURITY),
    "amazon iam": ("identity_and_access_management_iam", _AWS_FILL_SECURITY),
    "aws kms": ("key_management_service", _AWS_FILL_SECURITY),
    "aws secrets manager": ("secrets_manager", _AWS_FILL_SECURITY),
    "aws certificate manager": ("certificate_manager", _AWS_FILL_SECURITY),
    "aws waf": ("waf", _AWS_FILL_SECURITY),
    "aws shield": ("shield", _AWS_FILL_SECURITY),
    "aws guardduty": ("guardduty", _AWS_FILL_SECURITY),
    "amazon guardduty": ("guardduty", _AWS_FILL_SECURITY),
    "aws security hub": ("security_hub", _AWS_FILL_SECURITY),
    "aws cognito": ("cognito", _AWS_FILL_SECURITY),
    "amazon cognito": ("cognito", _AWS_FILL_SECURITY),
    "aws inspector": ("inspector", _AWS_FILL_SECURITY),
    "amazon macie": ("macie", _AWS_FILL_SECURITY),
    # Integration / messaging
    "amazon sqs": ("simple_queue_service_sqs", _AWS_FILL_INTEGRATION),
    "aws sqs": ("simple_queue_service_sqs", _AWS_FILL_INTEGRATION),
    "amazon sns": ("simple_notification_service_sns", _AWS_FILL_INTEGRATION),
    "aws sns": ("simple_notification_service_sns", _AWS_FILL_INTEGRATION),
    "amazon eventbridge": ("eventbridge", _AWS_FILL_INTEGRATION),
    "aws eventbridge": ("eventbridge", _AWS_FILL_INTEGRATION),
    "aws step functions": ("step_functions", _AWS_FILL_INTEGRATION),
    "amazon mq": ("mq", _AWS_FILL_INTEGRATION),
    "amazon kinesis": ("kinesis", _AWS_FILL_ANALYTICS),
    "aws kinesis": ("kinesis", _AWS_FILL_ANALYTICS),
    "amazon msk": ("managed_streaming_for_apache_kafka", _AWS_FILL_ANALYTICS),
    # Analytics
    "amazon athena": ("athena", _AWS_FILL_ANALYTICS),
    "amazon emr": ("emr", _AWS_FILL_ANALYTICS),
    "aws glue": ("glue", _AWS_FILL_ANALYTICS),
    "amazon quicksight": ("quicksight", _AWS_FILL_ANALYTICS),
    # Management / observability
    "amazon cloudwatch": ("cloudwatch_2", _AWS_FILL_MANAGEMENT),
    "aws cloudwatch": ("cloudwatch_2", _AWS_FILL_MANAGEMENT),
    "aws cloudtrail": ("cloudtrail", _AWS_FILL_MANAGEMENT),
    "aws config": ("config", _AWS_FILL_MANAGEMENT),
    "aws systems manager": ("systems_manager", _AWS_FILL_MANAGEMENT),
    "aws x-ray": ("x-ray", _AWS_FILL_MANAGEMENT),
    "aws cloudformation": ("cloudformation", _AWS_FILL_MANAGEMENT),
    "aws organizations": ("organizations", _AWS_FILL_MANAGEMENT),
    # AI / ML
    "amazon sagemaker": ("sagemaker", _AWS_FILL_AI),
    "amazon bedrock": ("bedrock", _AWS_FILL_AI),
    "amazon rekognition": ("rekognition", _AWS_FILL_AI),
    "amazon comprehend": ("comprehend", _AWS_FILL_AI),
}

_AWS_CATEGORY_FOR_FILL: dict[str, str] = {
    _AWS_FILL_COMPUTE: "compute",
    _AWS_FILL_STORAGE: "storage",
    _AWS_FILL_DATABASE: "database",
    _AWS_FILL_NETWORKING: "network",
    _AWS_FILL_SECURITY: "security",
    _AWS_FILL_INTEGRATION: "integration",
    _AWS_FILL_ANALYTICS: "analytics",
    _AWS_FILL_MANAGEMENT: "observability",
    _AWS_FILL_AI: "ai",
}


# ---------------------------------------------------------------------------
# GCP: mxgraph.gcp2.* family
# ---------------------------------------------------------------------------

_GCP_STYLE_TEMPLATE = (
    "sketch=0;points=[[0,0,0],[0.5,0,0],[1,0,0],[0,0.5,0],[1,0.5,0],"
    "[0,1,0],[0.5,1,0],[1,1,0]];"
    "outlineConnect=0;fontColor=#FFFFFF;gradientColor=none;"
    "fillColor={fill};strokeColor=none;dashed=0;"
    "verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;"
    "fontSize=12;shape=mxgraph.gcp2.{shape};"
)

_GCP_FILL_COMPUTE = "#4284F3"
_GCP_FILL_STORAGE = "#34A853"
_GCP_FILL_DATABASE = "#4284F3"
_GCP_FILL_NETWORKING = "#34A853"
_GCP_FILL_SECURITY = "#EA4335"
_GCP_FILL_INTEGRATION = "#FBBC04"
_GCP_FILL_AI = "#FBBC04"
_GCP_FILL_MANAGEMENT = "#5F6368"

_GCP_SHAPES: dict[str, tuple[str, str]] = {
    # Compute
    "google kubernetes engine": ("kubernetes_engine", _GCP_FILL_COMPUTE),
    "gke": ("kubernetes_engine", _GCP_FILL_COMPUTE),
    "google compute engine": ("compute_engine", _GCP_FILL_COMPUTE),
    "gce": ("compute_engine", _GCP_FILL_COMPUTE),
    "google cloud functions": ("cloud_functions", _GCP_FILL_COMPUTE),
    "cloud functions": ("cloud_functions", _GCP_FILL_COMPUTE),
    "google cloud run": ("cloud_run", _GCP_FILL_COMPUTE),
    "cloud run": ("cloud_run", _GCP_FILL_COMPUTE),
    "google app engine": ("app_engine", _GCP_FILL_COMPUTE),
    "app engine": ("app_engine", _GCP_FILL_COMPUTE),
    # Storage
    "google cloud storage": ("cloud_storage", _GCP_FILL_STORAGE),
    "cloud storage": ("cloud_storage", _GCP_FILL_STORAGE),
    "gcs": ("cloud_storage", _GCP_FILL_STORAGE),
    "google filestore": ("filestore", _GCP_FILL_STORAGE),
    "google persistent disk": ("persistent_disk", _GCP_FILL_STORAGE),
    # Databases
    "google cloud sql": ("cloud_sql", _GCP_FILL_DATABASE),
    "cloud sql": ("cloud_sql", _GCP_FILL_DATABASE),
    "google cloud spanner": ("cloud_spanner", _GCP_FILL_DATABASE),
    "cloud spanner": ("cloud_spanner", _GCP_FILL_DATABASE),
    "google cloud bigtable": ("cloud_bigtable", _GCP_FILL_DATABASE),
    "google firestore": ("firestore", _GCP_FILL_DATABASE),
    "google bigquery": ("bigquery", _GCP_FILL_DATABASE),
    "bigquery": ("bigquery", _GCP_FILL_DATABASE),
    "google cloud memorystore": ("cloud_memorystore", _GCP_FILL_DATABASE),
    # Networking
    "google cloud load balancing": ("cloud_load_balancing", _GCP_FILL_NETWORKING),
    "cloud load balancing": ("cloud_load_balancing", _GCP_FILL_NETWORKING),
    "google cloud cdn": ("cloud_cdn", _GCP_FILL_NETWORKING),
    "cloud cdn": ("cloud_cdn", _GCP_FILL_NETWORKING),
    "google cloud dns": ("cloud_dns", _GCP_FILL_NETWORKING),
    "cloud dns": ("cloud_dns", _GCP_FILL_NETWORKING),
    "google cloud armor": ("cloud_armor", _GCP_FILL_SECURITY),
    "cloud armor": ("cloud_armor", _GCP_FILL_SECURITY),
    "google cloud vpn": ("cloud_vpn", _GCP_FILL_NETWORKING),
    "google cloud interconnect": ("cloud_interconnect", _GCP_FILL_NETWORKING),
    "google vpc": ("virtual_private_cloud", _GCP_FILL_NETWORKING),
    # Security / identity
    "google cloud iam": ("identity_and_access_management", _GCP_FILL_SECURITY),
    "cloud iam": ("identity_and_access_management", _GCP_FILL_SECURITY),
    "google cloud kms": ("key_management_service", _GCP_FILL_SECURITY),
    "cloud kms": ("key_management_service", _GCP_FILL_SECURITY),
    "google secret manager": ("secret_manager", _GCP_FILL_SECURITY),
    "secret manager": ("secret_manager", _GCP_FILL_SECURITY),
    # Integration / messaging
    "google cloud pub sub": ("cloud_pubsub", _GCP_FILL_INTEGRATION),
    "cloud pub/sub": ("cloud_pubsub", _GCP_FILL_INTEGRATION),
    "google pub sub": ("cloud_pubsub", _GCP_FILL_INTEGRATION),
    "pub/sub": ("cloud_pubsub", _GCP_FILL_INTEGRATION),
    "google cloud tasks": ("cloud_tasks", _GCP_FILL_INTEGRATION),
    "google cloud scheduler": ("cloud_scheduler", _GCP_FILL_INTEGRATION),
    # Observability
    "google cloud monitoring": ("cloud_monitoring", _GCP_FILL_MANAGEMENT),
    "cloud monitoring": ("cloud_monitoring", _GCP_FILL_MANAGEMENT),
    "google cloud logging": ("cloud_logging", _GCP_FILL_MANAGEMENT),
    "cloud logging": ("cloud_logging", _GCP_FILL_MANAGEMENT),
    "google cloud trace": ("cloud_trace", _GCP_FILL_MANAGEMENT),
    # AI / ML
    "google vertex ai": ("ai_platform", _GCP_FILL_AI),
    "vertex ai": ("ai_platform", _GCP_FILL_AI),
}

_GCP_CATEGORY_FOR_FILL: dict[str, str] = {
    _GCP_FILL_COMPUTE: "compute",
    _GCP_FILL_STORAGE: "storage",
    _GCP_FILL_SECURITY: "security",
    _GCP_FILL_INTEGRATION: "integration",
    _GCP_FILL_AI: "ai",
    _GCP_FILL_MANAGEMENT: "observability",
}


# ---------------------------------------------------------------------------
# Kubernetes: mxgraph.kubernetes.icon family
# ---------------------------------------------------------------------------

_K8S_STYLE_TEMPLATE = (
    "sketch=0;points=[[0.5,0,0],[1,0.5,0],[0.5,1,0],[0,0.5,0]];"
    "outlineConnect=0;fontColor=#326CE5;gradientColor=none;"
    "fillColor={fill};strokeColor=#ffffff;dashed=0;"
    "verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;"
    "fontSize=12;shape=mxgraph.kubernetes.icon;prIcon={shape};"
)

_K8S_FILL_RESOURCE = "#326CE5"
_K8S_FILL_INFRA = "#326CE5"
_K8S_FILL_CONFIG = "#326CE5"

_K8S_SHAPES: dict[str, tuple[str, str]] = {
    # Workloads
    "kubernetes pod": ("pod", _K8S_FILL_RESOURCE),
    "k8s pod": ("pod", _K8S_FILL_RESOURCE),
    "pod": ("pod", _K8S_FILL_RESOURCE),
    "kubernetes deployment": ("deploy", _K8S_FILL_RESOURCE),
    "deployment": ("deploy", _K8S_FILL_RESOURCE),
    "kubernetes replicaset": ("rs", _K8S_FILL_RESOURCE),
    "replicaset": ("rs", _K8S_FILL_RESOURCE),
    "kubernetes statefulset": ("sts", _K8S_FILL_RESOURCE),
    "statefulset": ("sts", _K8S_FILL_RESOURCE),
    "kubernetes daemonset": ("ds", _K8S_FILL_RESOURCE),
    "daemonset": ("ds", _K8S_FILL_RESOURCE),
    "kubernetes job": ("job", _K8S_FILL_RESOURCE),
    "kubernetes cronjob": ("cronjob", _K8S_FILL_RESOURCE),
    "cronjob": ("cronjob", _K8S_FILL_RESOURCE),
    # Service / networking
    "kubernetes service": ("svc", _K8S_FILL_RESOURCE),
    "k8s service": ("svc", _K8S_FILL_RESOURCE),
    "kubernetes ingress": ("ing", _K8S_FILL_RESOURCE),
    "ingress": ("ing", _K8S_FILL_RESOURCE),
    "kubernetes endpoint": ("ep", _K8S_FILL_RESOURCE),
    "kubernetes networkpolicy": ("netpol", _K8S_FILL_RESOURCE),
    # Config / storage
    "kubernetes configmap": ("cm", _K8S_FILL_CONFIG),
    "configmap": ("cm", _K8S_FILL_CONFIG),
    "kubernetes secret": ("secret", _K8S_FILL_CONFIG),
    "kubernetes pv": ("pv", _K8S_FILL_CONFIG),
    "persistent volume": ("pv", _K8S_FILL_CONFIG),
    "kubernetes pvc": ("pvc", _K8S_FILL_CONFIG),
    "persistent volume claim": ("pvc", _K8S_FILL_CONFIG),
    "kubernetes storageclass": ("sc", _K8S_FILL_CONFIG),
    "kubernetes namespace": ("ns", _K8S_FILL_INFRA),
    "namespace": ("ns", _K8S_FILL_INFRA),
    # Identity / RBAC
    "kubernetes serviceaccount": ("sa", _K8S_FILL_RESOURCE),
    "serviceaccount": ("sa", _K8S_FILL_RESOURCE),
    "kubernetes role": ("role", _K8S_FILL_RESOURCE),
    "kubernetes clusterrole": ("c-role", _K8S_FILL_RESOURCE),
    # Cluster-level
    "kubernetes node": ("node", _K8S_FILL_INFRA),
    "k8s node": ("node", _K8S_FILL_INFRA),
    "kubernetes control plane": ("c-c-m", _K8S_FILL_INFRA),
    "kubernetes api server": ("api", _K8S_FILL_INFRA),
    "kubernetes etcd": ("etcd", _K8S_FILL_INFRA),
    "kubernetes kubelet": ("kubelet", _K8S_FILL_INFRA),
    "kubernetes scheduler": ("sched", _K8S_FILL_INFRA),
    "kubernetes controller manager": ("c-m", _K8S_FILL_INFRA),
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def lookup(vendor: str, key: str) -> BuiltinShape | None:
    """Resolve a vendor service name to a built-in diagrams.net shape entry.

    Returns ``None`` when the vendor is unknown or the key does not match a
    known service name. The caller is responsible for further fallback.
    """

    normalized = key.strip().lower()
    if not normalized:
        return None
    vendor_key = vendor.strip().lower()
    if vendor_key == "azure":
        shape = _AZURE_SHAPES.get(normalized)
        if shape is None:
            return None
        category = _AZURE_CATEGORY_HINTS.get(shape, "azure")
        return BuiltinShape(
            vendor="azure",
            drawio_style=_AZURE_STYLE_TEMPLATE.format(shape=shape),
            label=_humanize(normalized),
            category=f"azure-{category}",
        )
    if vendor_key == "aws":
        entry = _AWS_SHAPES.get(normalized)
        if entry is None:
            return None
        shape, fill = entry
        category = _AWS_CATEGORY_FOR_FILL.get(fill, "service")
        return BuiltinShape(
            vendor="aws",
            drawio_style=_AWS_STYLE_TEMPLATE.format(shape=shape, fill=fill),
            label=_humanize(normalized),
            category=f"aws-{category}",
        )
    if vendor_key == "gcp":
        entry = _GCP_SHAPES.get(normalized)
        if entry is None:
            return None
        shape, fill = entry
        category = _GCP_CATEGORY_FOR_FILL.get(fill, "service")
        return BuiltinShape(
            vendor="gcp",
            drawio_style=_GCP_STYLE_TEMPLATE.format(shape=shape, fill=fill),
            label=_humanize(normalized),
            category=f"gcp-{category}",
        )
    if vendor_key in {"kubernetes", "k8s"}:
        entry = _K8S_SHAPES.get(normalized)
        if entry is None:
            return None
        shape, fill = entry
        return BuiltinShape(
            vendor="kubernetes",
            drawio_style=_K8S_STYLE_TEMPLATE.format(shape=shape, fill=fill),
            label=_humanize(normalized),
            category="kubernetes-resource",
        )
    return None


def known_service_names(vendor: str) -> tuple[str, ...]:
    """Return the recognized service names for a vendor (for tests/docs)."""

    vendor_key = vendor.strip().lower()
    if vendor_key == "azure":
        return tuple(_AZURE_SHAPES.keys())
    if vendor_key == "aws":
        return tuple(_AWS_SHAPES.keys())
    if vendor_key == "gcp":
        return tuple(_GCP_SHAPES.keys())
    if vendor_key in {"kubernetes", "k8s"}:
        return tuple(_K8S_SHAPES.keys())
    return ()


@dataclass(frozen=True, slots=True)
class ExtractorEntry:
    """A vendor service exposed to the file_ingestion extractor.

    The extractor reads ``needle`` from input prose and creates a Node whose
    ``label`` and ``node_type`` come from this entry. The icon resolver then
    resolves the label back to the original BuiltinShape, so extraction and
    rendering stay in sync from a single source of truth.
    """

    label: str
    needle: str
    node_type: str
    vendor: str


# Map BuiltinShape.category -> generic node_type for layout. The icon resolver
# uses the label to pick the real vendor stencil; node_type only feeds layout.
_CATEGORY_TO_NODE_TYPE: dict[str, str] = {
    # Azure
    "azure": "backend",
    "azure-security": "secret",
    "azure-identity": "identity",
    "azure-observability": "monitoring",
    # AWS (color-derived categories)
    "aws-compute": "process",
    "aws-storage": "object_storage",
    "aws-database": "database",
    "aws-network": "network",
    "aws-security": "secret",
    "aws-integration": "queue",
    "aws-analytics": "process",
    "aws-observability": "monitoring",
    "aws-ai": "process",
    "aws-service": "backend",
    # GCP
    "gcp-compute": "process",
    "gcp-storage": "object_storage",
    "gcp-security": "secret",
    "gcp-integration": "queue",
    "gcp-ai": "process",
    "gcp-observability": "monitoring",
    "gcp-service": "backend",
    # Kubernetes
    "kubernetes-resource": "container",
}

# Per-needle overrides for cases where category->node_type doesn't fit. These
# steer layout (network resources to network swim lanes, databases to data,
# etc.) without changing the vendor stencil that gets rendered.
_NODE_TYPE_OVERRIDES: dict[str, str] = {
    # Azure
    "azure kubernetes service": "kubernetes",
    "aks": "kubernetes",
    "azure app service": "backend",
    "app service": "backend",
    "azure functions": "process",
    "function app": "process",
    "azure container apps": "container",
    "container apps": "container",
    "azure container instances": "container",
    "aci": "container",
    "azure container registry": "repository",
    "acr": "repository",
    "azure virtual machine": "server",
    "azure virtual machines": "server",
    "azure vm": "server",
    "vm scale set": "server",
    "azure vmss": "server",
    "azure front door": "cdn",
    "front door": "cdn",
    "azure application gateway": "gateway",
    "application gateway": "gateway",
    "azure load balancer": "network",
    "azure traffic manager": "cdn",
    "traffic manager": "cdn",
    "azure cdn": "cdn",
    "azure dns": "network",
    "azure virtual network": "network",
    "vnet": "network",
    "azure firewall": "firewall",
    "azure bastion": "security",
    "azure vpn gateway": "network",
    "azure expressroute": "network",
    "expressroute": "network",
    "azure nat gateway": "network",
    "azure private link": "network",
    "azure private endpoint": "network",
    "azure database for postgresql": "database",
    "azure database for mysql": "database",
    "azure database for mariadb": "database",
    "azure sql database": "database",
    "azure sql": "database",
    "azure sql managed instance": "database",
    "azure synapse analytics": "database",
    "azure cosmos db": "database",
    "cosmos db": "database",
    "azure cache for redis": "cache",
    "azure data lake storage": "object_storage",
    "azure data lake": "object_storage",
    "azure data factory": "process",
    "azure databricks": "process",
    "azure storage account": "object_storage",
    "storage account": "object_storage",
    "azure blob storage": "object_storage",
    "azure files": "object_storage",
    "azure queue storage": "queue",
    "azure table storage": "database",
    "azure backup": "object_storage",
    "azure site recovery": "object_storage",
    "azure service bus": "queue",
    "azure event hubs": "queue",
    "event hubs": "queue",
    "azure event grid": "queue",
    "event grid": "queue",
    "azure api management": "gateway",
    "api management": "gateway",
    "azure logic apps": "process",
    "logic apps": "process",
    "azure key vault": "secret",
    "key vault": "secret",
    "azure resource manager": "process",
    "resource group": "process",
    "azure subscription": "process",
    "azure tenant": "process",
    # AWS
    "amazon ec2": "server",
    "aws ec2": "server",
    "ec2": "server",
    "amazon eks": "kubernetes",
    "aws eks": "kubernetes",
    "amazon ecs": "container",
    "aws ecs": "container",
    "aws fargate": "container",
    "amazon ecr": "repository",
    "aws ecr": "repository",
    "amazon s3": "object_storage",
    "aws s3": "object_storage",
    "s3": "object_storage",
    "amazon ebs": "object_storage",
    "aws ebs": "object_storage",
    "amazon efs": "object_storage",
    "aws efs": "object_storage",
    "amazon fsx": "object_storage",
    "aws backup": "object_storage",
    "amazon elasticache": "cache",
    "aws elasticache": "cache",
    "amazon cloudfront": "cdn",
    "aws cloudfront": "cdn",
    "amazon route 53": "network",
    "route 53": "network",
    "aws route 53": "network",
    "amazon api gateway": "gateway",
    "aws api gateway": "gateway",
    "aws elb": "network",
    "aws elastic load balancer": "network",
    "aws alb": "network",
    "aws nlb": "network",
    "aws vpc": "network",
    "amazon vpc": "network",
    "aws transit gateway": "network",
    "aws direct connect": "network",
    "aws privatelink": "network",
    "aws global accelerator": "network",
    "aws waf": "waf",
    "aws shield": "security",
    "aws guardduty": "security",
    "amazon guardduty": "security",
    "aws security hub": "security",
    "aws inspector": "security",
    "amazon macie": "security",
    "aws iam": "identity",
    "amazon iam": "identity",
    "aws cognito": "identity",
    "amazon cognito": "identity",
    # GCP
    "google kubernetes engine": "kubernetes",
    "gke": "kubernetes",
    "google compute engine": "server",
    "gce": "server",
    "google cloud storage": "object_storage",
    "cloud storage": "object_storage",
    "gcs": "object_storage",
    "google filestore": "object_storage",
    "google persistent disk": "object_storage",
    "google cloud sql": "database",
    "cloud sql": "database",
    "google cloud spanner": "database",
    "cloud spanner": "database",
    "google cloud bigtable": "database",
    "google firestore": "database",
    "google bigquery": "database",
    "bigquery": "database",
    "google cloud memorystore": "cache",
    "google cloud load balancing": "network",
    "cloud load balancing": "network",
    "google cloud cdn": "cdn",
    "cloud cdn": "cdn",
    "google cloud dns": "network",
    "cloud dns": "network",
    "google cloud armor": "waf",
    "cloud armor": "waf",
    "google cloud vpn": "network",
    "google cloud interconnect": "network",
    "google vpc": "network",
    "google cloud iam": "identity",
    "cloud iam": "identity",
    # Kubernetes
    "kubernetes pod": "container",
    "k8s pod": "container",
    "pod": "container",
    "kubernetes deployment": "deployment",
    "deployment": "deployment",
    "kubernetes replicaset": "deployment",
    "kubernetes statefulset": "deployment",
    "kubernetes daemonset": "deployment",
    "kubernetes job": "process",
    "kubernetes cronjob": "process",
    "kubernetes service": "network",
    "k8s service": "network",
    "kubernetes ingress": "gateway",
    "kubernetes endpoint": "network",
    "kubernetes networkpolicy": "security",
    "kubernetes configmap": "process",
    "kubernetes secret": "secret",
    "kubernetes pv": "database",
    "persistent volume": "database",
    "kubernetes pvc": "database",
    "persistent volume claim": "database",
    "kubernetes storageclass": "database",
    "kubernetes namespace": "process",
    "namespace": "process",
    "kubernetes serviceaccount": "identity",
    "serviceaccount": "identity",
    "kubernetes role": "identity",
    "kubernetes clusterrole": "identity",
    "kubernetes node": "server",
    "k8s node": "server",
}


# Display-label overrides so canonical extracted labels read naturally.
_DISPLAY_LABEL_OVERRIDES: dict[str, str] = {
    "aks": "Azure Kubernetes Service",
    "acr": "Azure Container Registry",
    "aci": "Azure Container Instances",
    "vnet": "Azure Virtual Network",
    "azure vm": "Azure Virtual Machine",
    "azure vmss": "Azure VM Scale Set",
    "aad": "Microsoft Entra ID",
    "azure ad": "Microsoft Entra ID",
    "entra id": "Microsoft Entra ID",
    "azure active directory": "Microsoft Entra ID",
    "s3": "Amazon S3",
    "ec2": "Amazon EC2",
    "gke": "Google Kubernetes Engine",
    "gce": "Google Compute Engine",
    "gcs": "Google Cloud Storage",
    "k8s pod": "Kubernetes Pod",
    "k8s service": "Kubernetes Service",
    "k8s node": "Kubernetes Node",
    "pod": "Kubernetes Pod",
    "deployment": "Kubernetes Deployment",
    "namespace": "Kubernetes Namespace",
    "serviceaccount": "Kubernetes ServiceAccount",
    "persistent volume": "Kubernetes Persistent Volume",
    "persistent volume claim": "Kubernetes Persistent Volume Claim",
    "pub/sub": "Google Cloud Pub/Sub",
    "cloud run": "Google Cloud Run",
    "cloud functions": "Google Cloud Functions",
    "bigquery": "Google BigQuery",
    "cloud storage": "Google Cloud Storage",
    "cloud sql": "Google Cloud SQL",
    "cloud spanner": "Google Cloud Spanner",
    "cloud cdn": "Google Cloud CDN",
    "cloud dns": "Google Cloud DNS",
    "cloud iam": "Google Cloud IAM",
    "cloud kms": "Google Cloud KMS",
    "cloud monitoring": "Google Cloud Monitoring",
    "cloud logging": "Google Cloud Logging",
    "cloud armor": "Google Cloud Armor",
    "cloud load balancing": "Google Cloud Load Balancing",
    "secret manager": "Google Secret Manager",
    "vertex ai": "Google Vertex AI",
    "key vault": "Azure Key Vault",
    "cosmos db": "Azure Cosmos DB",
    "front door": "Azure Front Door",
    "application gateway": "Azure Application Gateway",
    "traffic manager": "Azure Traffic Manager",
    "function app": "Azure Functions",
    "app service": "Azure App Service",
    "service bus": "Azure Service Bus",
    "event hubs": "Azure Event Hubs",
    "event grid": "Azure Event Grid",
    "api management": "Azure API Management",
    "logic apps": "Azure Logic Apps",
    "storage account": "Azure Storage Account",
    "log analytics": "Azure Log Analytics",
    "log analytics workspace": "Azure Log Analytics Workspace",
    "application insights": "Azure Application Insights",
    "managed identity": "Azure Managed Identity",
    "microsoft sentinel": "Microsoft Sentinel",
    "microsoft defender for cloud": "Microsoft Defender for Cloud",
    "route 53": "Amazon Route 53",
    "container apps": "Azure Container Apps",
    "expressroute": "Azure ExpressRoute",
}


def _node_type_for(vendor: str, needle: str, category: str) -> str:
    override = _NODE_TYPE_OVERRIDES.get(needle)
    if override is not None:
        return override
    return _CATEGORY_TO_NODE_TYPE.get(category, "component")


def _display_label_for(vendor: str, needle: str, default_label: str) -> str:
    override = _DISPLAY_LABEL_OVERRIDES.get(needle)
    if override is not None:
        return override
    return default_label


def iter_extractor_entries() -> list[ExtractorEntry]:
    """Yield extractor-friendly entries for every built-in vendor shape.

    This is the single source of truth for vendor service recognition: the
    file_ingestion extractor calls this to extend its KNOWN_COMPONENTS list,
    so every shape the icon resolver knows about is also extractable from
    input prose. Adding a new mxgraph stencil to any of the vendor maps
    immediately becomes recognizable in user requests with no second edit.
    """

    entries: list[ExtractorEntry] = []
    for vendor, shape_map in (
        ("azure", _AZURE_SHAPES),
        ("aws", _AWS_SHAPES),
        ("gcp", _GCP_SHAPES),
        ("kubernetes", _K8S_SHAPES),
    ):
        for needle in shape_map.keys():
            shape = lookup(vendor, needle)
            if shape is None:
                continue
            label = _display_label_for(vendor, needle, shape.label)
            node_type = _node_type_for(vendor, needle, shape.category)
            entries.append(
                ExtractorEntry(label=label, needle=needle, node_type=node_type, vendor=vendor)
            )
    return entries


_ACRONYM_UPPER: frozenset[str] = frozenset({
    "aws", "gcp", "ai", "ml", "api", "cdn", "dns", "vpn", "vm", "iis", "ci",
    "cd", "os", "nat", "waf", "lb", "alb", "nlb", "elb", "sdk", "ssh", "tls",
    "ssl", "kms", "iam", "sns", "sqs", "emr", "msk", "mq", "fsx", "rds", "ec2",
    "s3", "ebs", "efs", "eks", "ecs", "ecr", "vpc", "aks", "acr", "aci",
    "vmss", "aad", "gke", "gce", "gcs", "pv", "pvc", "cm", "ds", "sts", "rs",
    "ns", "sa", "svc", "ing", "ep", "etcd", "iga", "pam", "siem", "sla", "slo",
    "mfa", "sso", "rbac", "abac", "ddos", "saml", "oidc", "jwt",
    "k8s", "ha", "dr", "io", "id", "ip", "url", "uri", "ux", "ui",
    "db", "sql", "etl", "elt", "fs", "tcp", "udp", "http", "https",
})

_COMPOUND_PROPER: dict[str, str] = {
    "bigquery": "BigQuery",
    "cloudfront": "CloudFront",
    "cloudwatch": "CloudWatch",
    "cloudtrail": "CloudTrail",
    "cloudformation": "CloudFormation",
    "dynamodb": "DynamoDB",
    "documentdb": "DocumentDB",
    "elasticache": "ElastiCache",
    "eventbridge": "EventBridge",
    "guardduty": "GuardDuty",
    "openai": "OpenAI",
    "opensearch": "OpenSearch",
    "expressroute": "ExpressRoute",
    "privatelink": "PrivateLink",
    "macie": "Macie",
    "sagemaker": "SageMaker",
    "quicksight": "QuickSight",
    "memorystore": "Memorystore",
    "kinesis": "Kinesis",
    "neptune": "Neptune",
    "athena": "Athena",
    "redshift": "Redshift",
    "aurora": "Aurora",
    "fargate": "Fargate",
    "lambda": "Lambda",
    "cognito": "Cognito",
    "inspector": "Inspector",
    "comprehend": "Comprehend",
    "rekognition": "Rekognition",
    "bedrock": "Bedrock",
    "glue": "Glue",
    "databricks": "Databricks",
    "synapse": "Synapse",
    "cosmos": "Cosmos",
    "sentinel": "Sentinel",
    "defender": "Defender",
    "entra": "Entra",
    "postgresql": "PostgreSQL",
    "mariadb": "MariaDB",
    "mysql": "MySQL",
    "kubernetes": "Kubernetes",
    "kubelet": "Kubelet",
    "spanner": "Spanner",
    "firestore": "Firestore",
    "bigtable": "Bigtable",
    "filestore": "Filestore",
    "pubsub": "Pub/Sub",
    "pub": "Pub",
    "sub": "Sub",
    "vertex": "Vertex",
    "azure": "Azure",
    "amazon": "Amazon",
    "google": "Google",
    "microsoft": "Microsoft",
    "delinea": "Delinea",
    "cyberark": "CyberArk",
    "okta": "Okta",
    "ping": "Ping",
    "prometheus": "Prometheus",
    "grafana": "Grafana",
    "datadog": "Datadog",
    "splunk": "Splunk",
    "opentelemetry": "OpenTelemetry",
    # Kubernetes compound resource names
    "configmap": "ConfigMap",
    "daemonset": "DaemonSet",
    "statefulset": "StatefulSet",
    "replicaset": "ReplicaSet",
    "cronjob": "CronJob",
    "networkpolicy": "NetworkPolicy",
    "clusterrole": "ClusterRole",
    "serviceaccount": "ServiceAccount",
    "storageclass": "StorageClass",
}


def _humanize(name: str) -> str:
    """Produce a polished display label from a lowercase service needle.

    Treats known acronyms (AWS, S3, EKS, AKS, KMS, etc.) as uppercase and
    known compound proper nouns (BigQuery, CloudFront, DynamoDB, etc.) with
    their canonical mixed-case form, so auto-derived labels read correctly.
    """

    parts: list[str] = []
    for word in name.split():
        # Strip a trailing slash-suffix like "pub/sub" -> keep the form
        if "/" in word:
            sub_parts = [_humanize_word(sub) for sub in word.split("/")]
            parts.append("/".join(sub_parts))
        else:
            parts.append(_humanize_word(word))
    return " ".join(parts)


def _humanize_word(word: str) -> str:
    if word in _COMPOUND_PROPER:
        return _COMPOUND_PROPER[word]
    if word in _ACRONYM_UPPER:
        return word.upper()
    return word.capitalize()
