from sql_migration_assistant.infra import init, deploy
import json
import argparse
import sys

import argparse


def parse_args():
    parser = argparse.ArgumentParser(description="Set up AI Migration Assistant")
    parser.add_argument("--profile", help="Specify the Databricks profile to use", default="DEFAULT")
    parser.add_argument("--commands", help="Specify the commands to run", nargs='+', choices=['init', 'deploy', 'all'], default=['all'])
    # Add other arguments as needed

    args = parser.parse_args()
    # Convert Namespace object to dictionary
    args_dict = vars(args)
    return args_dict

if __name__ == "__main__":

    args = parse_args()
    if args['commands'] == ['all']:
        init(args['profile'])
        deploy(args['profile'])
    else:
        if "init" in args['commands']:
            init(args['profile'])
        if "deploy" in args['commands']:
            deploy(args['profile'])