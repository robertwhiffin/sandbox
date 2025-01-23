import os
import sys

from importlib.metadata import version

# Get the directory of the current file
module_dir = os.path.dirname(os.path.abspath(__file__)) + "/.."

# Change the working directory to the directory of the current file
os.chdir(module_dir)
sys.path.append(module_dir)
print(module_dir)


def main():
    from sql_migration_assistant.utils import logger

    logger.info("Starting sql-migration assistant")
    from sql_migration_assistant.frontend.GradioFrontend import GradioFrontend

    try:
        logger.info(f"Version: {version('sql_migration_assistant')}")
    except Exception as e:
        logger.error(e)

    frontend = GradioFrontend()
    frontend.app.launch(
        server_name=os.getenv("GRADIO_SERVER_NAME", "localhost"),
        server_port=int(os.getenv("GRADIO_SERVER_PORT", 3001)),
        debug=True,
    )


if __name__ == "__main__":
    main()
