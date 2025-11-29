import os
import subprocess
from langchain_core.tools import tool


@tool
def generate_iac(spec: str, provider: str = "terraform") -> str:
    """
    Generates IaC configuration based on a specification.

    Args:
        spec: A natural language description or JSON spec of the infrastructure.
        provider: The IaC provider to use (default: 'terraform').
    """
    # In a real scenario, this would use an LLM to generate the code.
    # For now, we'll scaffold a basic file.
    try:
        if provider == "terraform":
            filename = "main.tf"
            content = f"""
# Generated Terraform for: {spec}

provider "aws" {{
  region = "us-west-2"
}}

resource "null_resource" "example" {{
  provisioner "local-exec" {{
    command = "echo 'Provisioning {spec}'"
  }}
}}
"""
            with open(filename, "w") as f:
                f.write(content)
            return f"Generated {filename} with basic scaffold for '{spec}'."
        else:
            return f"Provider {provider} not supported yet."
    except Exception as e:
        return f"Error generating IaC: {str(e)}"


@tool
def apply_infra(directory: str = ".") -> str:
    """
    Applies the infrastructure configuration in the given directory.
    Executes 'terraform init' and 'terraform apply'.
    """
    try:
        # Check if terraform is installed
        subprocess.check_call(["terraform", "--version"])

        # Init
        subprocess.check_call(["terraform", "init"], cwd=directory)

        # Apply
        # -auto-approve is dangerous in prod, but okay for this agent context
        subprocess.check_call(["terraform", "apply", "-auto-approve"], cwd=directory)

        return "Infrastructure applied successfully."
    except FileNotFoundError:
        return "Error: Terraform not found. Please install it first."
    except subprocess.CalledProcessError as e:
        return f"Error applying infra: {str(e)}"
    except Exception as e:
        return f"Error: {str(e)}"


def get_infra_tools():
    """Returns infrastructure tools."""
    return [generate_iac, apply_infra]
