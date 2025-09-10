import requests


def test_stack_deployment(chinook_api_stack):
    outputs = chinook_api_stack
    assert "domain" in outputs

def test_chinook_api_stack_simple_request(chinook_api_stack):
    outputs = chinook_api_stack
    domain = outputs["domain"]
    url = to_localstack_url(f"https://{domain}/album/1")
    response = requests.get(url)
    assert response.status_code == 200

def to_localstack_url(real_url: str, host_style: bool = False, edge_port: int = 4566) -> str:
    """
    Convert a real API Gateway invoke URL to a LocalStack URL.
    Supports REST APIs (format: https://{api_id}.execute-api.{region}.amazonaws.com/{stage}/path)

    Example:
      https://wgtzdsypit.execute-api.us-east-1.amazonaws.com/farmMarket/albums/1
      -> http://localhost:4566/restapis/wgtzdsypit/farmMarket/_user_request_/albums/1
    """
    import re
    from urllib.parse import urlparse

    p = urlparse(real_url)
    m = re.match(r"^(?P<api_id>[a-z0-9]+)\.execute-api\.(?P<region>[-a-z0-9]+)\.amazonaws\.com$", p.netloc)
    if not m:
        raise ValueError(f"Unrecognized API Gateway hostname: {p.netloc}")
    api_id = m.group("api_id")

    # first path segment = stage
    parts = [seg for seg in p.path.split("/") if seg]
    if not parts:
        raise ValueError("Missing stage segment in path")
    stage = parts[0]
    resource_path = "/" + "/".join(parts[1:]) if len(parts) > 1 else ""

    if host_style:
        return f"http://{api_id}.execute-api.localhost.localstack.cloud:{edge_port}/{stage}{resource_path}"
    else:
        # path-style form
        return f"http://localhost:{edge_port}/_aws/execute-api/{api_id}/{stage}/{resource_path}"
