"""MCP input schemas and descriptions for this service package."""

from __future__ import annotations

MCP_CONTRACTS: dict[str, dict[str, object]] = {
    "list_workflow_instructions": {
        "title": "List Workflow Instructions",
        "description": "List bundled workflow instructions for scratch circuit authoring (for example buck-converter-cpp).",
        "input_schema": {"type": "object", "properties": {}},
    },
    "read_workflow_instruction": {
        "title": "Read Workflow Instruction",
        "description": "Read one bundled workflow instruction document with build steps, coordinates, and source templates.",
        "input_schema": {
            "type": "object",
            "required": ["instruction_id"],
            "properties": {"instruction_id": {"type": "string"}},
        },
    },
}
