import subprocess
from pathlib import Path

import yaml
from databricks.labs.blueprint.tui import Prompts
from databricks.sdk.service.apps import AppDeployment

from sql_migration_assistant.utils import get_workspace_client
from sql_migration_assistant.utils.initialsetup import SetUpMigrationAssistant


def init(profile, **kwargs):
    w = get_workspace_client(profile)
    p = Prompts()
    setter_upper = SetUpMigrationAssistant(w, p)
    final_config = setter_upper.setup_migration_assistant(w, p)
    project_path = Path(__file__).parent.parent.parent.parent.resolve()
    local_config = str(project_path) + "/config.yml"
    with open(local_config, "w") as f:
        yaml.dump(final_config, f)


def deploy(profile, **kwargs):
    """
    Main function to handle the deployment.

    Parameters:
    - profile (str): The name of the profile.
    - project_dir (str): The directory of the project.
    - config_path (str): The path to the configuration file.
    """
    project_path = Path(__file__).parent.parent.parent.parent.resolve()

    project_dir_resolved = project_path
    config_path_resolved = project_path / "config.yml"
    print(f"Profile: {profile}")
    print(f"Project Directory: {project_dir_resolved}")
    print(f"Config Path: {config_path_resolved}")

    with open(config_path_resolved, "r") as config_file:
        config = yaml.safe_load(config_file)
        print(f"Loaded Config: {config}")

    create_app_yml(config)

    w = get_workspace_client(kwargs.get("profile"))

    deployment_path = config.get("DEPLOYMENT_PATH")

    subprocess.run(
        [
            "databricks",
            "sync",
            project_dir_resolved,
            deployment_path,
            "--profile",
            profile,
        ]
    )

    print("Deploying app")
    deployment = w.apps.deploy_and_wait(
        config.get("APP"),
        app_deployment=AppDeployment(source_code_path=deployment_path),
    )
    app = w.apps.get(config.get("APP"))
    print(f"App deployed. URL: {app.url} with result {deployment.status}")


def create_app_yml(config):
    content = {
        "command": ["python", "src/sql_migration_assistant/main.py"],
        "env": [{"name": key, "value": value} for key, value in config.items()],
    }
    with open("app.yml", "w") as file:
        yaml.dump(content, file)
