"""Parser for OpenAPI 3.x, Swagger 2.0, and API documentation specifications."""

from __future__ import annotations

import json
import re
from typing import Any

from core.contracts import RiskLevel
from integrations.autobuilder.contracts import ApiEndpointSpec, ApiSpecification


def _resolve_ref(ref: str, root_doc: dict[str, Any]) -> dict[str, Any]:
    """Resolve a local JSON schema $ref pointer like '#/components/schemas/Item'."""
    if not ref.startswith("#/"):
        return {"type": "object"}

    parts = ref.lstrip("#/").split("/")
    curr: Any = root_doc
    for p in parts:
        if isinstance(curr, dict) and p in curr:
            curr = curr[p]
        else:
            return {"type": "object"}

    if isinstance(curr, dict) and "$ref" in curr:
        return _resolve_ref(curr["$ref"], root_doc)
    return curr if isinstance(curr, dict) else {"type": "object"}


def _clean_schema(schema: Any, root_doc: dict[str, Any]) -> dict[str, Any]:
    """Recursively expand $refs and sanitize JSON schema."""
    if not isinstance(schema, dict):
        return {"type": "string"}

    if "$ref" in schema:
        resolved = _resolve_ref(schema["$ref"], root_doc)
        return _clean_schema(resolved, root_doc)

    out: dict[str, Any] = {}
    for k, v in schema.items():
        if k == "properties" and isinstance(v, dict):
            out[k] = {pk: _clean_schema(pv, root_doc) for pk, pv in v.items()}
        elif k == "items" and isinstance(v, dict):
            out[k] = _clean_schema(v, root_doc)
        else:
            out[k] = v
    return out


def _slugify(text: str) -> str:
    """Normalize string into a clean snake_case identifier."""
    cleaned = re.sub(r"[^a-zA-Z0-9_]+", "_", text.lower().strip())
    return re.sub(r"_+", "_", cleaned).strip("_")


def _infer_tool_name(
    service_name: str, path: str, method: str, operation_id: str | None = None
) -> str:
    """Derive semantic capability name e.g. 'stripe.customers.create' or 'linear.issues.get'."""
    del operation_id
    clean_path = path.rstrip("/")
    segments = [
        s for s in clean_path.split("/") if s and not s.startswith("{") and not s.startswith(":")
    ]
    resource = _slugify(segments[-1]) if segments else "root"

    last_segment = clean_path.split("/")[-1] if clean_path else ""
    is_item_param = last_segment.startswith("{") or last_segment.startswith(":")

    method_lower = method.lower()
    if method_lower == "get":
        action = "get" if is_item_param else "list"
    elif method_lower == "post":
        action = "create"
    elif method_lower in ("put", "patch"):
        action = "update"
    elif method_lower == "delete":
        action = "delete"
    else:
        action = method_lower

    return f"{service_name}.{resource}.{action}"


def _infer_risk_level(method: str, path: str) -> RiskLevel:
    """Assign principle of least privilege risk level according to operation semantics."""
    m = method.upper()
    if m in ("GET", "HEAD", "OPTIONS"):
        return RiskLevel.READ
    if m == "DELETE":
        return RiskLevel.BUSINESS_CHANGE
    if "send" in path.lower() or "publish" in path.lower() or "notify" in path.lower():
        return RiskLevel.EXTERNAL_COMMUNICATION
    return RiskLevel.HARMLESS_WRITE


class OpenApiParser:
    """Parses OpenAPI 3.x and Swagger 2.0 specs into normalized ApiSpecification."""

    def parse(
        self,
        raw_spec: dict[str, Any] | str,
        service_name_override: str | None = None,
        base_url_override: str | None = None,
    ) -> ApiSpecification:
        if isinstance(raw_spec, str):
            try:
                doc = json.loads(raw_spec)
            except Exception as exc:
                raise ValueError(f"Invalid JSON in API specification: {exc}") from exc
        elif isinstance(raw_spec, dict):
            doc = raw_spec
        else:
            raise ValueError("API specification must be a dict or valid JSON string")

        info = doc.get("info", {})
        title = str(info.get("title", "External API"))
        version = str(info.get("version", "1.0.0"))
        description = str(info.get("description", ""))

        # 1. Determine service name
        service_name = service_name_override or _slugify(title) or "api_service"
        service_name = _slugify(service_name)

        # 2. Determine base URL
        base_url = "https://api.example.com"
        if base_url_override:
            base_url = base_url_override
        elif "servers" in doc and doc["servers"]:
            base_url = str(doc["servers"][0].get("url", "https://api.example.com"))
        elif "host" in doc:
            scheme = doc.get("schemes", ["https"])[0]
            base_path = doc.get("basePath", "")
            base_url = f"{scheme}://{doc['host']}{base_path}".rstrip("/")

        # 3. Detect authentication
        auth_type = "bearer"
        auth_header = "Authorization"
        sec_schemes = doc.get("components", {}).get("securitySchemes", {}) or doc.get(
            "securityDefinitions", {}
        )
        for _, s_def in sec_schemes.items():
            if isinstance(s_def, dict):
                stype = s_def.get("type", "").lower()
                if stype == "http" and s_def.get("scheme", "").lower() == "bearer":
                    auth_type = "bearer"
                    break
                if stype == "apikey":
                    auth_type = "apikey_header" if s_def.get("in") == "header" else "apikey_query"
                    auth_header = s_def.get("name", "X-API-Key")
                    break
                if stype == "basic":
                    auth_type = "basic"
                    break

        # 4. Parse endpoints
        endpoints: list[ApiEndpointSpec] = []
        paths = doc.get("paths", {})

        for path, path_item in paths.items():
            if not isinstance(path_item, dict):
                continue

            for method_key, op in path_item.items():
                if method_key.lower() not in ("get", "post", "put", "patch", "delete", "head"):
                    continue
                if not isinstance(op, dict):
                    continue

                method = method_key.upper()
                op_id = op.get("operationId") or f"{method.lower()}_{_slugify(path)}"
                summary = str(op.get("summary") or op.get("description") or f"{method} {path}")
                op_desc = str(op.get("description") or summary)
                tool_name = _infer_tool_name(service_name, path, method, op.get("operationId"))
                risk = _infer_risk_level(method, path)

                # Extract parameters
                param_props: dict[str, Any] = {}
                required_params: list[str] = []

                # Path & Query params
                all_params = list(path_item.get("parameters", [])) + list(op.get("parameters", []))
                for param in all_params:
                    if isinstance(param, dict):
                        pname = param.get("name")
                        if not pname:
                            continue
                        pschema = param.get("schema", {"type": param.get("type", "string")})
                        param_props[pname] = _clean_schema(pschema, doc)
                        if param.get("description"):
                            param_props[pname]["description"] = param["description"]
                        if param.get("required") or param.get("in") == "path":
                            required_params.append(pname)

                # Request body (OpenAPI 3.x)
                req_body = op.get("requestBody", {})
                req_body_schema = None
                if isinstance(req_body, dict):
                    content = req_body.get("content", {})
                    app_json = content.get("application/json", {}).get("schema")
                    if app_json:
                        cleaned_body = _clean_schema(app_json, doc)
                        req_body_schema = cleaned_body
                        if cleaned_body.get("type") == "object" and "properties" in cleaned_body:
                            for prop_name, prop_val in cleaned_body["properties"].items():
                                param_props[prop_name] = prop_val
                            for req_field in cleaned_body.get("required", []):
                                if req_field not in required_params:
                                    required_params.append(req_field)

                # Unified parameters schema
                unified_schema: dict[str, Any] = {
                    "type": "object",
                    "properties": param_props,
                }
                if required_params:
                    unified_schema["required"] = list(dict.fromkeys(required_params))

                # Responses
                resp_schema: dict[str, Any] = {"type": "object"}
                responses = op.get("responses", {})
                ok_resp = responses.get("200") or responses.get("201") or responses.get("default")
                if isinstance(ok_resp, dict):
                    resp_content = (
                        ok_resp.get("content", {}).get("application/json", {}).get("schema")
                    )
                    if resp_content:
                        resp_schema = _clean_schema(resp_content, doc)

                endpoints.append(
                    ApiEndpointSpec(
                        operation_id=op_id,
                        tool_name=tool_name,
                        path=path,
                        method=method,
                        summary=summary,
                        description=op_desc,
                        parameters_schema=unified_schema,
                        request_body_schema=req_body_schema,
                        response_schema=resp_schema,
                        risk_level=risk,
                        requires_auth=True,
                    )
                )

        return ApiSpecification(
            service_name=service_name,
            title=title,
            version=version,
            base_url=base_url,
            description=description,
            auth_type=auth_type,
            auth_key_or_header=auth_header,
            endpoints=endpoints,
            metadata={"source_type": "openapi"},
        )
