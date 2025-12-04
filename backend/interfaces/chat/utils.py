from typing import Optional, Any, Dict
from core.base_utils import BaseUtils
from .models import PromptData

VALID_TYPES = {"object", "array", "string", "number", "boolean", "null"}

class ChatUtils(BaseUtils):
    
    async def save_prompt(self, prompt: PromptData):
        doc = prompt.dict()
        prompts_collection = self.mongodb.get_collection("prompts")
        prompt = await prompts_collection.insert_one(doc)
        return prompt.inserted_id
    
    async def get_last_project_for_user(self, user_id: str) -> Optional[str]:
        projects_collection = self.mongodb.get_collection("projects")
        project = await projects_collection.find_one(
            {"user_id": str(user_id)},
            sort=[("created_at", -1)]
        )
        return str(project["_id"]) if project else None
    
    def validate_response_schema(self, schema: Dict[str, Any], path: str = "") -> bool:
        """
        Recursively validate a provided JSON schema according to supported fields.

        Supported fields:
        - type: one of "object", "array", "string", "number", "boolean", "null"
        - properties: dict of nested schemas (only for type=object)
        - items: schema or list of schemas (only for type=array)
        - required: list of field names (only for type=object)
        - description: string
        - enum: list of allowed values
        - default: default value (must match type)

        Raises ValueError if invalid.
        Returns True if valid.
        """

        if not isinstance(schema, dict):
            raise ValueError(f"{path or 'root'}: Schema must be a dictionary")

        # Validate type field
        schema_type = schema.get("type")
        if not schema_type or schema_type not in VALID_TYPES:
            raise ValueError(f"{path or 'root'}: Invalid or missing 'type' field: {schema_type}")

        # Validate properties (object)
        if schema_type == "object":
            properties = schema.get("properties")
            if not isinstance(properties, dict) or not properties:
                raise ValueError(f"{path or 'object'}: Objects must define non-empty 'properties'")

            for prop_name, prop_schema in properties.items():
                if not isinstance(prop_schema, dict):
                    raise ValueError(f"{path}.{prop_name}: Each property must be a schema object")
                self.validate_response_schema(prop_schema, path=f"{path}.{prop_name}" if path else prop_name)

            # Validate 'required'
            if "required" in schema:
                if not isinstance(schema["required"], list):
                    raise ValueError(f"{path or 'object'}: 'required' must be a list")
                for field in schema["required"]:
                    if field not in properties:
                        raise ValueError(f"{path or 'object'}: 'required' field '{field}' not defined in properties")

        # Validate items (array)
        elif schema_type == "array":
            items = schema.get("items")
            if not items:
                raise ValueError(f"{path or 'array'}: Arrays must define 'items' schema")

            if isinstance(items, dict):
                self.validate_response_schema(items, path=f"{path}.items" if path else "items")
            elif isinstance(items, list):
                for idx, item_schema in enumerate(items):
                    if not isinstance(item_schema, dict):
                        raise ValueError(f"{path}.items[{idx}]: Each array item must be a schema object")
                    self.validate_response_schema(item_schema, path=f"{path}.items[{idx}]")
            else:
                raise ValueError(f"{path or 'array'}: 'items' must be a schema or list of schemas")

        # Validate enum (any type)
        if "enum" in schema:
            if not isinstance(schema["enum"], list) or not schema["enum"]:
                raise ValueError(f"{path or schema_type}: 'enum' must be a non-empty list")

        # Validate default (must match type)
        if "default" in schema:
            default = schema["default"]
            type_map = {
                "string": str,
                "number": (int, float),
                "boolean": bool,
                "array": list,
                "object": dict,
                "null": type(None)
            }
            expected_type = type_map.get(schema_type)
            if expected_type and not isinstance(default, expected_type):
                raise ValueError(
                    f"{path or schema_type}: Default value {default!r} does not match type '{schema_type}'"
                )

        # Validate description (optional string)
        if "description" in schema and not isinstance(schema["description"], str):
            raise ValueError(f"{path or schema_type}: 'description' must be a string")

        return True
