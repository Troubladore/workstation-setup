import os

EXEC_MODE = os.getenv("EXEC_MODE", "docker")  # "docker" locally, "k8s" in CI/prod


def run_datakit(
    task_id: str,
    image: str,
    arguments: list[str],
    env: dict[str, str] | None = None,
    queue: str | None = None,
    pod_template_file: str | None = None,
    **kwargs,
):
    """Return a task operator that runs a datakit.
    - In local dev (EXEC_MODE=docker), returns a DockerOperator.
    - In CI/prod (EXEC_MODE=k8s), returns a KubernetesPodOperator.
    The image/args/env stay identical for fidelity.
    """
    if EXEC_MODE == "k8s":
        from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import KubernetesPodOperator

        return KubernetesPodOperator(
            task_id=task_id,
            name=task_id.replace("_", "-"),
            image=image,
            arguments=arguments,
            env_vars=env or {},
            queue=queue,
            pod_template_file=pod_template_file,
            is_delete_operator_pod=True,
            get_logs=True,
            **kwargs,
        )
    else:
        from airflow.providers.docker.operators.docker import DockerOperator
        from docker.types import Mount

        mounts = []
        if os.getenv("KRB_CCACHE_PATH"):
            mounts.append(
                Mount(
                    target="/ccache",
                    source=os.getenv("KRB_CCACHE_PATH"),
                    type="bind",
                    read_only=True,
                )
            )
        return DockerOperator(
            task_id=task_id,
            image=image,
            command=arguments,
            environment=env or {},
            mounts=mounts,
            auto_remove=True,
            tty=False,
            mount_tmp_dir=True,
            **kwargs,
        )
