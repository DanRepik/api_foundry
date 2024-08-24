import pulumi
import pulumi_aws as aws


class GatewayAPICloudprint(pulumi.ComponentResource):
    rest_api: aws.apigateway.RestApi

    def __init__(self, name, body: str, opts=None):
        super().__init__("cloudprints:apigw:OpenAPIGateway", name, None, opts)

        self.rest_api = aws.apigateway.RestApi(
            f"{name}-http-api", name=f"{name}-http-api", body=body
        )

    def id(self) -> pulumi.Output[str]:
        return self.rest_api.id
