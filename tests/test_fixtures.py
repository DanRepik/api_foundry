import os
import yaml

from typing import Any


def read_spec(spec_locaton: str = "resources/chinook_api.yaml") -> dict[str, Any]:
    # Define the path to the YAML test spec file
    spec_file_path = os.path.join(os.getcwd(), spec_locaton)

    # Load YAML from file
    with open(spec_file_path, "r") as file:
        return yaml.safe_load(file)


def write_spec(spec_location: str, spec: dict[str, Any]):
    # Define the path to the YAML test spec file
    spec_file_path = os.path.join(os.getcwd(), spec_location)

    with open(spec_location, "w") as out_file:
        yaml.dump(spec, out_file, indent=4)
