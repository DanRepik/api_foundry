import json
from pulumi import automation as auto


def deploy_stack(project_name, stack_name, pulumi_program):
    stack = auto.create_or_select_stack(
        stack_name=stack_name,
        project_name=project_name,
        program=pulumi_program,
    )
    try:
        print("Deploying Pulumi stack...")
        up_result = stack.up()
        print(f"Deployment complete: {up_result.summary.resource_changes}")
        outputs = {k: v.value for k, v in up_result.outputs.items()}
        return stack, outputs
    finally:
        # Optional: let the caller/fixture control teardown instead of destroying here
        pass


def deploy_stack_no_teardown(project_name, stack_name, pulumi_program):
    stack = auto.create_or_select_stack(
        stack_name=stack_name,
        project_name=project_name,
        program=pulumi_program,
    )
    print("Deploying Pulumi stack...")
    up_result = stack.up()
    print(f"Deployment complete: {up_result.summary.resource_changes}")
    outputs = {k: v.value for k, v in up_result.outputs.items()}
    return stack, outputs


def deploy_localstack(
    project_name, stack_name, localstack, pulumi_program, teardown=True
):
    aws_config = {
        "aws:region": auto.ConfigValue(localstack["region"]),
        "aws:accessKey": auto.ConfigValue("test"),
        "aws:secretKey": auto.ConfigValue("test"),
        "aws:endpoints": auto.ConfigValue(
            json.dumps(
                [
                    {
                        "cloudwatch": localstack["endpoint_url"],
                        "apigateway": localstack["endpoint_url"],
                        "logs": localstack["endpoint_url"],
                        "iam": localstack["endpoint_url"],
                        "lambda": localstack["endpoint_url"],
                        "secretsmanager": localstack["endpoint_url"],
                        "sts": localstack["endpoint_url"],
                    }
                ]
            )
        ),
        "aws:skipCredentialsValidation": auto.ConfigValue("true"),
        "aws:skipRegionValidation": auto.ConfigValue("true"),
        "aws:skipRequestingAccountId": auto.ConfigValue("true"),
        "aws:skipMetadataApiCheck": auto.ConfigValue("true"),
        "aws:insecure": auto.ConfigValue("true"),
        "aws:s3UsePathStyle": auto.ConfigValue("true"),
    }

    stack = auto.create_or_select_stack(
        stack_name=stack_name, project_name=project_name, program=pulumi_program
    )

    # Clean prior resources (ignore errors)
    try:
        stack.destroy(on_output=lambda _: None)
    except Exception:
        pass

    stack.set_all_config(aws_config)
    try:
        stack.refresh(on_output=lambda _: None)
    except Exception:
        pass

    up_result = stack.up(on_output=print)

    # Normalize outputs to plain dict
    outputs = {k: v.value for k, v in up_result.outputs.items()}
    return stack, outputs, teardown
