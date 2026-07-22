from tools.export_openapi import build_openapi_document


def test_exported_openapi_contains_management_contract() -> None:
    document = build_openapi_document()

    assert "/api/v1/auth/token" in document["paths"]
    assert "/api/v1/admin/users" in document["paths"]
    assert "/api/v1/resources/nodes" in document["paths"]
    assert "post" in document["paths"]["/api/v1/incidents"]
    assert document["components"]["securitySchemes"]["HumanOAuth2"]["flows"]["password"][
        "tokenUrl"
    ] == "/api/v1/auth/token"


def test_public_list_responses_have_concrete_item_schemas() -> None:
    document = build_openapi_document()
    response = document["paths"]["/api/v1/incidents"]["get"]["responses"]["200"]
    schema = response["content"]["application/json"]["schema"]

    assert schema["$ref"].endswith("/IncidentPage")
    assert "IncidentResponse" in document["components"]["schemas"]


def test_openapi_does_not_expose_heartbeat_only_event_stream() -> None:
    document = build_openapi_document()

    assert "/api/v1/events/stream" not in document["paths"]
