"""Factory for creating validator chains.

This module provides the validator factory responsible for creating the appropriate
validator chain based on the target schema version.
"""

from typing import Optional, List, Dict, Type
import logging

from .validator_base import Validator

logger = logging.getLogger("hatch.validator_factory")


class ValidatorFactory:
    """Factory class for creating schema validator chains.
    
    This factory creates the appropriate validator chain based on the target
    schema version, setting up the Chain of Responsibility pattern correctly.
    The factory maintains a registry of available validators and constructs
    chains that enable proper delegation between versions.
    """
    
    # Registry of available validator versions (newest to oldest)
    _validator_registry: Dict[str, Type[Validator]] = {}
    _version_order: List[str] = []
    
    @classmethod
    def register_validator(cls, version: str, validator_class: Type[Validator]) -> None:
        """Register a validator class for a specific schema version.
        
        Args:
            version (str): Schema version (e.g., "1.1.0", "1.2.0")
            validator_class (Type[Validator]): Validator class for the version
        """
        cls._validator_registry[version] = validator_class
        if version not in cls._version_order:
            cls._version_order.append(version)
            # Sort versions in descending order (newest first)
            cls._version_order.sort(reverse=True)
        logger.debug(f"Registered validator for version {version}")
    
    @classmethod
    def get_supported_versions(cls) -> List[str]:
        """Get list of supported schema versions.
        
        Returns:
            List[str]: List of supported versions ordered newest to oldest
        """
        cls._ensure_validators_loaded()
        return cls._version_order.copy()
    
    @classmethod
    def _ensure_validators_loaded(cls) -> None:
        """Ensure all available validators are loaded and registered."""
        if not cls._validator_registry:
            # Import and register available validators
            try:
                from hatch_validator.package.v1_1_0.validator import Validator as V110Validator
                cls.register_validator("1.1.0", V110Validator)
            except ImportError as e:
                logger.warning(f"Could not load v1.1.0 validator: {e}")
              # Future versions can be added here:
            try:
                from hatch_validator.package.v1_2_0.validator import Validator as V120Validator
                cls.register_validator("1.2.0", V120Validator)
            except ImportError as e:
                logger.warning(f"Could not load v1.2.0 validator: {e}")
    
    @classmethod
    def create_validator_chain(cls, target_version: Optional[str] = None) -> Validator:
        """Create appropriate validator chain based on target version.
        
        Creates a chain of validators ordered from newest to oldest schema versions.
        Each validator in the chain can handle its specific version and delegate
        to older versions for unchanged validation concerns.
        
        Args:
            target_version (str, optional): Specific schema version to target. 
                If None, uses the latest available version. Defaults to None.
            
        Returns:
            Validator: Head of the validator chain
            
        Raises:
            ValueError: If the target version is not supported or no validators are available
        """
        cls._ensure_validators_loaded()
        
        if not cls._validator_registry:
            raise ValueError("No validators available")
        
        # Determine target version
        if target_version is None:
            target_version = cls._version_order[0]  # Latest version
        elif target_version not in cls._validator_registry:
            raise ValueError(f"Unsupported schema version: {target_version}. "
                           f"Supported versions: {cls._version_order}")
        
        logger.info(f"Creating validator chain for target version: {target_version}")
          # Create chain starting from target version down to oldest
        target_index = cls._version_order.index(target_version)
        chain_versions = cls._version_order[target_index:]
        
        # Create validators in order (newest to oldest)
        validators = []
        for version in chain_versions:
            validator_class = cls._validator_registry[version]
            validator = validator_class()
            validators.append(validator)
            logger.debug(f"Created validator for version {version}")
        
        # Link validators (each points to the next older one)
        for i in range(len(validators) - 1):
            validators[i].set_next(validators[i + 1])
            logger.debug(f"Linked validator {chain_versions[i]} -> {chain_versions[i+1]}")
        
        head_validator = validators[0]
        logger.info(f"Validator chain created successfully, head: {target_version}")
        return head_validator
