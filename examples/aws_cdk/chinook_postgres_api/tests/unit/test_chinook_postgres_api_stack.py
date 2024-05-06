import aws_cdk as core
import aws_cdk.assertions as assertions

from chinook_postgres_api.chinook_postgres_api_stack import ChinookPostgresApiStack

# example tests. To run these tests, uncomment this file along with the example
# resource in chinook_postgres_api/chinook_postgres_api_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = ChinookPostgresApiStack(app, "chinook-postgres-api")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
