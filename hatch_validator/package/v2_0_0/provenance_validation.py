"""Provenance validation for schema version 2.0.0.

This module provides optional provenance validation logic beyond JSON schema.
"""

import logging
from typing import Dict, List, Tuple

logger = logging.getLogger("hatch.schema.v2_0_0.provenance_validation")


class ProvenanceValidation:
    """Strategy for validating package provenance metadata for v2.0.0."""

    def validate_provenance(self, metadata: Dict, context) -> Tuple[bool, List[str]]:
        """Validate provenance metadata for v2.0.0."""
        provenance = metadata.get('provenance')
        if provenance is None:
            return True, []

        if not isinstance(provenance, dict):
            return False, ["Provenance must be an object"]

        if not provenance:
            return False, ["Provenance metadata must not be empty"]

        errors = []
        if 'source' in provenance and not isinstance(provenance['source'], str):
            errors.append("Provenance.source must be a string")

        if errors:
            return False, errors
        return True, []
