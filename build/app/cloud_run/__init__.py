import logging

import nanoid
from google.api_core import exceptions
from google.cloud import run_v2
from google.protobuf import duration_pb2, field_mask_pb2


class ServiceBuilder:
    def __init__(
        self,
        name: str | None = None,
        template: run_v2.RevisionTemplate | None = None,
        traffic: list[run_v2.TrafficTarget] | None = None,
        labels: dict[str, str] = None,
    ):
        self.name = name
        self.template = template
        self.traffic = traffic
        self.labels = labels or {}

    def build(self) -> run_v2.Service:
        service_params = {
            "template": self.template,
            "labels": self.labels,
        }
        if self.name:
            service_params["name"] = self.name
        if self.traffic:
            service_params["traffic"] = self.traffic
        return run_v2.Service(**service_params)


class RevisionTemplateBuilder:
    def __init__(
        self, service_name: str, branch_name: str = None, short_sha: str = None
    ):
        self.service_name: str = service_name
        self.branch_name: str = branch_name or "main"
        self.short_sha: str = short_sha or "latest"

    def create_name(self, name: str = None):
        branch_name = self.branch_name
        short_sha = self.short_sha
        suffix = nanoid.generate(size=4, alphabet="0123456789")
        if name:
            return name
        return f"{self.service_name}-{branch_name}-{short_sha}-{suffix}"

    def create_scaling(self, min_instance: int = 0, max_instance: int = 1):
        return run_v2.RevisionScaling(
            min_instance_count=min_instance, max_instance_count=max_instance
        )

    def create_timeout(self, timeout: int = 600):
        return duration_pb2.Duration(seconds=timeout)

    def build(
        self,
        name: str,
        containers: list[run_v2.Container],
        scaling: run_v2.RevisionScaling = None,
        max_instance_request_concurrency: int = 40,
        timeout: duration_pb2.Duration = None,
        volumes: list[run_v2.Volume] = None,
        cloud_sql_instances: list[str] = None,
        service_account: str = None,
        cpu_throttling: bool = True,
    ) -> run_v2.RevisionTemplate:
        self.name = name
        self.scaling = scaling or self.create_scaling()
        self.max_instance_request_concurrency = max_instance_request_concurrency
        self.timeout = timeout or self.create_timeout()
        self.containers = containers
        self.service_account = service_account
        self.cpu_throttling = cpu_throttling
        self.volumes = volumes or []
        if cloud_sql_instances:
            self.volumes.append(
                run_v2.Volume(
                    name="cloudsql",
                    cloud_sql_instance=run_v2.CloudSqlInstance(
                        instances=[
                            str(cloud_sql_instance)
                            for cloud_sql_instance in cloud_sql_instances
                        ]
                    ),
                )
            )

        template_params = {
            "revision": self.name,
            "scaling": self.scaling,
            "max_instance_request_concurrency": self.max_instance_request_concurrency,
            "timeout": self.timeout,
            "containers": self.containers,
            "volumes": self.volumes,
        }
        if self.service_account:
            template_params["service_account"] = self.service_account
        return run_v2.RevisionTemplate(
            **template_params,
            annotations={
                "run.googleapis.com/cpu-throttling": str(self.cpu_throttling).lower()
            },
        )


class ContainerBuilder:
    def __init__(
        self,
        short_sha: str = "latest",
    ):
        self.short_sha = short_sha

    def create_env_from_secret(self, env_name, secret_name) -> run_v2.EnvVar:
        return run_v2.EnvVar(
            name=env_name,
            value_source=run_v2.EnvVarSource(
                secret_key_ref=run_v2.SecretKeySelector(
                    secret=secret_name,
                    version="latest",
                )
            ),
        )

    def create_env_from_value(self, env_name, value) -> run_v2.EnvVar:
        return run_v2.EnvVar(
            name=env_name,
            value=value,
        )

    def create_resources(
        self,
        cpu: str = "0.2",
        memory: str = "128Mi",
        cpu_idle: bool = True,
    ) -> None:
        resources = run_v2.ResourceRequirements(
            limits={
                "cpu": cpu,
                "memory": memory,
            },
            cpu_idle=cpu_idle,
        )
        return resources

    def create_startup_probe(
        self,
        initial_delay_seconds: int = 5,
        timeout_seconds: int = 5,
        period_seconds: int = 5,
        failure_threshold: int = 3,
        action: run_v2.HTTPGetAction
        | run_v2.GRPCAction
        | run_v2.TCPSocketAction = None,
    ) -> None:
        kwargs = {
            "initial_delay_seconds": initial_delay_seconds,
            "period_seconds": period_seconds,
            "timeout_seconds": timeout_seconds,
            "failure_threshold": failure_threshold,
        }
        if action:
            if isinstance(action, run_v2.HTTPGetAction):
                kwargs["http_get"] = action
            elif isinstance(action, run_v2.GRPCAction):
                kwargs["grpc"] = action
            elif isinstance(action, run_v2.TCPSocketAction):
                kwargs["tcp_socket"] = action
        return run_v2.Probe(**kwargs)

    def get_image(
        self, repository: str, stem: str, location: str, project: str, tag: str = None
    ):
        tag = tag or self.short_sha
        return f"{location}-docker.pkg.dev/{project}/{repository}/{stem}:{tag}"

    def create_ports(self, ports: list[int]) -> run_v2.ContainerPort:
        container_ports = []
        for port in ports:
            container_ports.append(run_v2.ContainerPort(container_port=port))
        return container_ports

    def build(
        self,
        name: str,
        image: str,
        resources: run_v2.ResourceRequirements,
        envs: list[run_v2.EnvVar] = None,
        depends_on: list[str] = None,
        startup_probe: run_v2.Probe = None,
        command: list[str] = None,
        volume_mounts: list[run_v2.VolumeMount] = None,
        ports: list[run_v2.ContainerPort] = None,
        require_cloud_sql: bool = False,
    ) -> run_v2.Container:
        name: str = name
        image: str = image

        ports: list[run_v2.ContainerPort] = ports or []
        depends_on: list[str] = depends_on or []
        volume_mounts: list[run_v2.VolumeMount] = volume_mounts or []
        if require_cloud_sql:
            volume_mounts.append(
                run_v2.VolumeMount(
                    mount_path="/cloudsql",
                    name="cloudsql",
                )
            )

        env: list[run_v2.EnvVar] = envs or []
        resources: run_v2.ResourceRequirements = resources
        startup_probe: run_v2.Probe = startup_probe
        command: list[str] = command
        kwargs = {
            "name": name,
            "image": image,
            "resources": resources,
            "env": env,
        }
        if depends_on:
            kwargs["depends_on"] = depends_on
        if ports:
            kwargs["ports"] = ports
        if volume_mounts:
            kwargs["volume_mounts"] = volume_mounts
        if startup_probe:
            kwargs["startup_probe"] = startup_probe
        if command:
            kwargs["command"] = command

        container = run_v2.Container(**kwargs)
        return container


class Deployment:
    def __init__(
        self,
        service_name: str,
        project: str,
        location: str,
        stage: str,
        stage_production: str,
        branch_name: str,
        deploy_timeout: int,
    ):
        self.service_name = service_name

        self.service_client = run_v2.ServicesClient()
        self.project = project
        self.location = location
        self.stage = stage
        self.stage_production = stage_production
        self.branch_name = branch_name
        self.service_parent = f"projects/{self.project}/locations/{self.location}"
        self.service_path = f"{self.service_parent}/services/{self.service_name}"
        self.timeout = deploy_timeout

        self.service: run_v2.Service = None

    def get_traffic_status_map(self):
        latest_ready_revision = self.service.latest_ready_revision.split("/")[-1]
        logging.info(f"Latest revision: {latest_ready_revision}")
        traffic_tag_map = {}
        for status in self.service.traffic_statuses:
            tag = status.tag
            percent = status.percent
            revision = status.revision or latest_ready_revision
            traffic_tag_map[tag] = {
                "percent": percent,
                "revision": revision,
            }
        logging.info(f"Current traffic status map: {traffic_tag_map}")
        return traffic_tag_map

    def create_service(
        self, revision_template: run_v2.RevisionTemplate
    ) -> run_v2.Service:
        try:
            service = ServiceBuilder(
                template=revision_template,
                traffic=[
                    run_v2.TrafficTarget(
                        type_=run_v2.TrafficTargetAllocationType.TRAFFIC_TARGET_ALLOCATION_TYPE_REVISION,
                        revision=revision_template.revision,
                        percent=100,
                    )
                ],
            )
            logging.info(f"Creating service: {self.service_path}")
            operation = self.service_client.create_service(
                parent=self.service_parent,
                service_id=self.service_name,
                service=service.build(),
                timeout=self.timeout,
            )
            logging.info("Waiting for operation to complete...")
            operation.result()
            logging.info(f"Service created: {self.service_path}")
            self.service = self.service_client.get_service(name=self.service_path)
        except Exception as e:
            logging.info(f"Error creating service: {e}")
            raise
        return service

    def add_revision(self, revision_template: run_v2.RevisionTemplate):
        try:
            service = ServiceBuilder(
                name=self.service_path,
                template=revision_template,
            ).build()
            logging.info(f"Updating service: {self.service_path}")
            operation = self.service_client.update_service(
                service=service,
                update_mask=field_mask_pb2.FieldMask(paths=["template"]),
                timeout=self.timeout,
            )
            logging.info("Waiting for operation to complete...")
            operation.result()
            logging.info(f"Service updated: {self.service_path}")
        except Exception as e:
            logging.info(f"Error updating service: {e}")
            logging.info(f"Service: {service.template}")
            raise

    def update_trafic_tag(self, revision_name):
        logging.info(
            f"Updating traffic tag for service: {self.service_path} with revision: {revision_name}"
        )
        current_traffic_status_map = self.get_traffic_status_map()

        update_traffic_status_map = {}
        for tag, status in current_traffic_status_map.items():
            if self.stage == self.stage_production and not (
                tag == self.stage_production
            ):
                status["percent"] = 0
            update_traffic_status_map[tag] = status
        update_traffic_status_map[self.branch_name] = {
            "percent": 0,
            "revision": revision_name,
        }
        update_traffic_status_map[self.stage] = {
            "percent": 100 if self.stage == self.stage_production else 0,
            "revision": revision_name,
        }
        logging.info(f"Update traffic status map: {update_traffic_status_map}")
        update_traffic = []
        for tag, status in update_traffic_status_map.items():
            update_traffic.append(
                run_v2.TrafficTarget(
                    type_=run_v2.TrafficTargetAllocationType.TRAFFIC_TARGET_ALLOCATION_TYPE_REVISION,
                    revision=status["revision"],
                    percent=status["percent"],
                    tag=tag,
                )
            )
        try:
            service = ServiceBuilder(
                name=self.service_path,
                traffic=update_traffic,
            )
            operation = self.service_client.update_service(
                service=service.build(),
                update_mask=field_mask_pb2.FieldMask(paths=["traffic"]),
            )
            logging.info("Waiting for operation to complete...")
            operation.result()
        except Exception as e:
            logging.info(f"Error updating traffic: {e}")
            raise
        return service

    def get_service(self) -> run_v2.Service:
        try:
            logging.info(f"Getting service: {self.service_path}")
            service = self.service_client.get_service(name=self.service_path)
            logging.info(f"Service retrieved: {service.name}")
        except exceptions.NotFound:
            logging.info(f"Service not found: {self.service_path}")
            service = None
        return service

    def setup_logging(self):
        logging.basicConfig(
            format="%(asctime)s - %(levelname)s - %(message)s",
            level=logging.INFO,
        )
        logging.info(f"Setting up deployment for service: {self.service_name}")

    def remove_failed_revisions_tag(self):
        traffics = self.service.traffic_statuses
        update_traffics = [
            run_v2.TrafficTarget(
                type_=traffic.type_,
                revision=traffic.revision,
                percent=traffic.percent,
                tag=traffic.tag,
            )
            for traffic in traffics
        ]
        logging.info(f"Current service traffic: {update_traffics}")
        service = ServiceBuilder(
            name=self.service.name, traffic=update_traffics
        ).build()
        self.service_client.update_service(
            service=service,
            update_mask=field_mask_pb2.FieldMask(paths=["traffic"]),
        )

    def deploy(self, revision_template: run_v2.RevisionTemplate):
        self.setup_logging()
        self.service = self.get_service()
        if not self.service:
            self.create_service(revision_template)
            self.update_trafic_tag(revision_template.revision)
        else:
            self.remove_failed_revisions_tag()
            self.add_revision(revision_template)
            self.update_trafic_tag(revision_template.revision)
        service = self.get_service()

        logging.info(f"Service deployed: {service.name}")
        logging.info(f"Service URL: {service.uri}")
        logging.info(
            f"Service lateset created revision: {service.latest_created_revision}"
        )
        logging.info(f"Service latest ready revision: {service.latest_ready_revision}")
        return service
