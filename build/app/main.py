from enum import StrEnum

from google.cloud import run_v2
from google.protobuf import duration_pb2

from app.cloud_run import ContainerBuilder, Deployment, RevisionTemplateBuilder
from app.setting import Setting


class Stage(StrEnum):
    DEV = "dev"
    STAGING = "staging"
    PROD = "prod"


def create_api_container(setting: Setting) -> run_v2.Container:
    container_builder = ContainerBuilder(setting.SHORT_SHA)
    container_name = setting.API_CONTAINER_NAME
    repository_name = "cake-fair"
    container_image = container_builder.get_image(
        repository=repository_name,
        stem=f"{container_name}/{setting.STAGE}",
        location=setting.LOCATION,
        project=setting.PROJECT,
        tag=setting.SHORT_SHA,
    )
    startup_probe = container_builder.create_startup_probe(
        initial_delay_seconds=60,
        timeout_seconds=5,
        period_seconds=15,
        failure_threshold=4,
        action=run_v2.HTTPGetAction(
            path="/health",
            port=setting.API_PORT,
        ),
    )
    resources = container_builder.create_resources(
        cpu="0.8",
        memory="512Mi",
        cpu_idle=True,
    )
    envs = [
        container_builder.create_env_from_value(
            env_name="SERVICE_NAME",
            value=setting.SERVICE_NAME,
        ),
        container_builder.create_env_from_secret(
            env_name="DB_USER", secret_name="DB_USER"
        ),
        container_builder.create_env_from_secret(
            env_name="DB_PASSWORD", secret_name="DB_PASSWORD"
        ),
        container_builder.create_env_from_secret(
            env_name="DB_NAME", secret_name="DB_NAME"
        ),
        container_builder.create_env_from_secret(
            env_name="DB_HOST", secret_name="DB_HOST"
        ),
        container_builder.create_env_from_secret(
            env_name="GCP_BUCKET_NAME", secret_name="GCP_BUCKET_NAME"
        ),
        container_builder.create_env_from_value(
            env_name="AGENT_PORT",
            value=str(setting.AGENT_PORT),
        ),
        container_builder.create_env_from_value(
            env_name="ON_CLOUD",
            value=str(True),
        ),
    ]

    container = container_builder.build(
        name=container_name,
        image=container_image,
        resources=resources,
        envs=envs,
        startup_probe=startup_probe,
    )
    return container


def create_agent_container(setting: Setting) -> run_v2.Container:
    container_builder = ContainerBuilder(
        short_sha=setting.SHORT_SHA,
    )
    container_name = setting.AGENT_CONTAINER_NAME
    repository_name = "cake-fair"
    container_image = container_builder.get_image(
        repository=repository_name,
        stem=f"{container_name}/{setting.STAGE}",
        location=setting.LOCATION,
        project=setting.PROJECT,
        tag=setting.SHORT_SHA,
    )
    startup_probe = container_builder.create_startup_probe(
        initial_delay_seconds=60,
        timeout_seconds=5,
        period_seconds=15,
        failure_threshold=4,
        action=run_v2.HTTPGetAction(
            path="/list-apps",
            port=setting.AGENT_PORT,
        ),
    )
    resources = container_builder.create_resources(
        cpu="0.8",
        memory="512Mi",
        cpu_idle=True,
    )
    envs = [
        container_builder.create_env_from_value(
            env_name="SERVICE_NAME",
            value=setting.SERVICE_NAME,
        ),
        container_builder.create_env_from_secret(
            env_name="OPENROUTER_API_KEY", secret_name="OPENROUTER_API_KEY"
        ),
    ]

    container = container_builder.build(
        name=container_name,
        image=container_image,
        resources=resources,
        envs=envs,
        startup_probe=startup_probe,
    )
    return container


def create_client_container(setting: Setting) -> run_v2.Container:
    container_builder = ContainerBuilder(
        short_sha=setting.SHORT_SHA,
    )
    container_name = setting.CLIENT_CONTAINER_NAME
    repository_name = "cake-fair"
    container_image = container_builder.get_image(
        repository=repository_name,
        stem=f"{container_name}/{setting.STAGE}",
        location=setting.LOCATION,
        project=setting.PROJECT,
        tag=setting.SHORT_SHA,
    )
    startup_probe = container_builder.create_startup_probe(
        initial_delay_seconds=60,
        timeout_seconds=5,
        period_seconds=15,
        failure_threshold=4,
        action=run_v2.HTTPGetAction(
            path="/healthz",
            port=setting.CLIENT_PORT,
        ),
    )
    resources = container_builder.create_resources(
        cpu="0.8",
        memory="512Mi",
        cpu_idle=True,
    )
    envs = [
        container_builder.create_env_from_value(
            env_name="SERVICE_NAME",
            value=setting.SERVICE_NAME,
        ),
        container_builder.create_env_from_value(
            env_name="ON_CLOUD",
            value=str(True),
        ),
        container_builder.create_env_from_value(
            env_name="API_PORT",
            value=str(setting.API_PORT),
        ),
        container_builder.create_env_from_value(
            env_name="CLIENT_PORT",
            value=str(setting.CLIENT_PORT),
        ),
        container_builder.create_env_from_value(
            env_name="ON_CLOUD",
            value=str(True),
        ),
    ]

    container = container_builder.build(
        name=container_name,
        image=container_image,
        resources=resources,
        envs=envs,
        ports=[run_v2.ContainerPort(container_port=setting.CLIENT_PORT)],
        startup_probe=startup_probe,
    )
    return container


def create_revision_template(setting: Setting) -> run_v2.RevisionTemplate:
    api_container = create_api_container(setting)
    agent_container = create_agent_container(setting)
    client_container = create_client_container(setting)

    revision_template_builder = RevisionTemplateBuilder(
        service_name=setting.SERVICE_NAME,
    )
    revision_name = revision_template_builder.create_name()
    revision_template = revision_template_builder.build(
        name=revision_name,
        scaling=revision_template_builder.create_scaling(max_instance=4),
        containers=[
            api_container,
            agent_container,
            client_container,
        ],
        max_instance_request_concurrency=40,
        timeout=duration_pb2.Duration(seconds=1200, nanos=0),
    )
    return revision_template


def run():
    setting = Setting()
    revision_template = create_revision_template(setting)
    deployment = Deployment(
        service_name=setting.SERVICE_NAME,
        project=setting.PROJECT,
        location=setting.LOCATION,
        deploy_timeout=setting.DEPLOY_TIMEOUT,
        stage=setting.STAGE,
        stage_production=Stage.PROD,
        branch_name=setting.BRANCH_NAME,
    )
    deployment.deploy(revision_template=revision_template)


if __name__ == "__main__":
    run()
