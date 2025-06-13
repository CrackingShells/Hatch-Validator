"""Factory for creating validator chains.

This module provides the validator factory responsible for creating the appropriate
validator chain based on the target schema version.
"""

from typing import Optional

from .validator_base import SchemaValidator


class ValidatorFactory:
    """Factory class for creating schema validator chains.
    
    This factory creates the appropriate validator chain based on the target
    schema version, setting up the Chain of Responsibility pattern correctly.
    """
    
    @staticmethod
    def create_validator_chain(target_version: Optional[str] = None) -> SchemaValidator:
        """Create appropriate validator chain based on target version.
        
        Creates a chain of validators ordered from newest to oldest schema versions.
        If a specific version is requested, the chain will start with that version's
        validator.
        
        Args:
            target_version (str, optional): Specific schema version to target. Defaults to None.
            
        Returns:
            SchemaValidator: Head of the validator chain
            
        Raises:
            ValueError: If the target version is not supported
        """
        # Import here to avoid circular imports - we can't import this at module level
        from hatch_validator.schemas.v1_1_0.schema_validators import SchemaValidator as V110Validator
        
        # Create validators (newest to oldest when we have more versions)
        v1_1_0_validator = V110Validator()
        
        # If specific version requested, return that validator
        if target_version == "1.1.0":
            return v1_1_0_validator
        elif target_version is None:
            # Default to v1.1.0 for now (will be latest when we add more versions)
            return v1_1_0_validator
        else:
            raise ValueError(f"Unsupported schema version: {target_version}")
            
        # In the future, when v1.2.0 is implemented:
        # from hatch_validator.schemas.v1_2_0.schema_validators import SchemaValidator as V120Validator
        # v1_2_0_validator = V120Validator()
        # v1_2_0_validator.set_next(v1_1_0_validator)
        #
        # if target_version == "1.2.0":
        #     return v1_2_0_validator
        # elif target_version == "1.1.0":
        #     return v1_1_0_validator
        # elif target_version is None:
        #     # Default to latest version (v1.2.0)
        #     return v1_2_0_validator
        # else:
        #     raise ValueError(f"Unsupported schema version: {target_version}")
