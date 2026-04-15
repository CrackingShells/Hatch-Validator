"""Citations validation for schema version 2.0.0.

This module provides optional citations validation logic beyond JSON schema.
"""

import logging
from typing import Dict, List, Tuple

logger = logging.getLogger("hatch.schema.v2_0_0.citations_validation")


class CitationsValidation:
    """Strategy for validating package citations metadata for v2.0.0."""

    def validate_citations(self, metadata: Dict, context) -> Tuple[bool, List[str]]:
        """Validate citations metadata for v2.0.0."""
        citations = metadata.get('citations')
        if citations is None:
            return True, []

        if not isinstance(citations, list):
            return False, ["Citations must be a list of citation objects"]

        errors = []
        for index, citation in enumerate(citations):
            if not isinstance(citation, dict):
                errors.append(f"Citation at index {index} must be an object")
                continue

            if 'format' not in citation or not isinstance(citation['format'], str):
                errors.append(f"Citation at index {index} must include a string 'format'")
            if 'value' not in citation or not isinstance(citation['value'], str):
                errors.append(f"Citation at index {index} must include a string 'value'")
            if 'note' in citation and not isinstance(citation['note'], str):
                errors.append(f"Citation at index {index} field 'note' must be a string")

        if errors:
            return False, errors
        return True, []
