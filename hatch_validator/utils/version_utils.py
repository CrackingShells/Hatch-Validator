"""Version constraint utilities for dependency validation.

This module provides utilities for parsing, validating, and checking version
constraints that are independent of specific schema versions.
"""

import re
from typing import Dict, List, Set, Tuple, Optional
from packaging import version
from packaging.specifiers import SpecifierSet, InvalidSpecifier


class VersionConstraintError(Exception):
    """Exception raised for version constraint related errors."""
    pass


class VersionConstraintValidator:
    """Utility class for validating version constraints.
    
    Provides methods for parsing version constraint strings, validating them,
    and checking compatibility between versions and constraints.
    """
    
    # Common version constraint patterns
    VERSION_PATTERN = re.compile(r'^[0-9]+(?:\.[0-9]+)*(?:[-+][a-zA-Z0-9.-]*)?$')
    CONSTRAINT_PATTERN = re.compile(r'^[<>=!~^]*[0-9]+(?:\.[0-9]+)*(?:[-+][a-zA-Z0-9.-]*)?(?:\s*,\s*[<>=!~^]*[0-9]+(?:\.[0-9]+)*(?:[-+][a-zA-Z0-9.-]*)?)*$')
    
    @staticmethod
    def validate_version(version_str: str) -> Tuple[bool, Optional[str]]:
        """Validate a version string.
        
        Args:
            version_str (str): Version string to validate (e.g., "1.2.3").
            
        Returns:
            Tuple[bool, Optional[str]]: A tuple containing:
                - bool: Whether the version is valid
                - Optional[str]: Error message if invalid, None otherwise
        """
        if not version_str or not isinstance(version_str, str):
            return False, "Version must be a non-empty string"
        
        try:
            # Use packaging library to validate version
            version.Version(version_str)
            return True, None
        except version.InvalidVersion as e:
            return False, f"Invalid version format: {e}"
    
    @staticmethod
    def validate_constraint(constraint: str) -> Tuple[bool, Optional[str]]:
        """Validate a version constraint string.
        
        Supports standard constraint operators like >=, <=, ==, !=, ~=, etc.
        
        Args:
            constraint (str): Version constraint string (e.g., ">=1.0.0,<2.0.0").
            
        Returns:
            Tuple[bool, Optional[str]]: A tuple containing:
                - bool: Whether the constraint is valid
                - Optional[str]: Error message if invalid, None otherwise
        """
        if not constraint or not isinstance(constraint, str):
            return False, "Constraint must be a non-empty string"
        
        try:
            # Use packaging library to validate constraint
            SpecifierSet(constraint)
            return True, None
        except InvalidSpecifier as e:
            return False, f"Invalid constraint format: {e}"
    
    @staticmethod
    def is_version_compatible(version_str: str, constraint: str) -> Tuple[bool, Optional[str]]:
        """Check if a version satisfies a constraint.
        
        Args:
            version_str (str): Version string to check.
            constraint (str): Version constraint to check against.
            
        Returns:
            Tuple[bool, Optional[str]]: A tuple containing:
                - bool: True if version satisfies constraint
                - Optional[str]: Error message if there's an issue, None otherwise
        """
        # First validate both version and constraint
        version_valid, version_error = VersionConstraintValidator.validate_version(version_str)
        if not version_valid:
            return False, f"Invalid version: {version_error}"
        
        constraint_valid, constraint_error = VersionConstraintValidator.validate_constraint(constraint)
        if not constraint_valid:
            return False, f"Invalid constraint: {constraint_error}"
        
        try:
            ver = version.Version(version_str)
            spec = SpecifierSet(constraint)
            is_compatible = ver in spec
            return is_compatible, None
        except Exception as e:
            return False, f"Error checking compatibility: {e}"
    
    @staticmethod
    def parse_constraint_operators(constraint: str) -> List[Tuple[str, str]]:
        """Parse a constraint string to extract operators and versions.
        
        Args:
            constraint (str): Version constraint string.
            
        Returns:
            List[Tuple[str, str]]: List of (operator, version) tuples.
            
        Raises:
            VersionConstraintError: If the constraint format is invalid.
        """
        valid, error = VersionConstraintValidator.validate_constraint(constraint)
        if not valid:
            raise VersionConstraintError(f"Invalid constraint: {error}")
        
        try:
            spec_set = SpecifierSet(constraint)
            result = []
            for spec in spec_set:
                result.append((spec.operator, spec.version))
            return result
        except Exception as e:
            raise VersionConstraintError(f"Error parsing constraint: {e}")
    
    @staticmethod
    def get_constraint_bounds(constraint: str) -> Tuple[Optional[str], Optional[str]]:
        """Get the minimum and maximum version bounds from a constraint.
        
        Args:
            constraint (str): Version constraint string.
            
        Returns:
            Tuple[Optional[str], Optional[str]]: A tuple containing:
                - Optional[str]: Minimum version (None if no lower bound)
                - Optional[str]: Maximum version (None if no upper bound)
                
        Raises:
            VersionConstraintError: If the constraint format is invalid.
        """
        operators = VersionConstraintValidator.parse_constraint_operators(constraint)
        
        min_version = None
        max_version = None
        
        for operator, ver_str in operators:
            if operator in ['>=', '>']:
                if min_version is None or version.Version(ver_str) > version.Version(min_version):
                    min_version = ver_str
            elif operator in ['<=', '<']:
                if max_version is None or version.Version(ver_str) < version.Version(max_version):
                    max_version = ver_str
            elif operator == '==':
                min_version = max_version = ver_str
        
        return min_version, max_version
    
    @staticmethod
    def _generate_test_versions(min1: Optional[str], max1: Optional[str], 
                               min2: Optional[str], max2: Optional[str]) -> List[str]:
        """Generate a list of version strings to test for constraint overlap.
        
        Args:
            min1 (Optional[str]): Minimum version of first constraint.
            max1 (Optional[str]): Maximum version of first constraint.
            min2 (Optional[str]): Minimum version of second constraint.
            max2 (Optional[str]): Maximum version of second constraint.
            
        Returns:
            List[str]: List of version strings to test.
        """
        # Base set of versions to always test
        test_versions = []
        
        # Add specific versions from the constraints
        for ver in [min1, max1, min2, max2]:
            if ver:
                test_versions.append(ver)
        
        # Add intermediate versions that might be in the overlap
        if min1 and min2:
            higher_min = max(version.Version(min1), version.Version(min2))
            test_versions.append(str(higher_min))
        
        if max1 and max2:
            lower_max = min(version.Version(max1), version.Version(max2))
            test_versions.append(str(lower_max))
            
        # Add commonly used versions that might be in the overlap
        common_versions = ['0.0.1', '1.0.0', '2.0.0', '10.0.0']
        
        return test_versions + common_versions
    
    @staticmethod
    def constraints_overlap(constraint1: str, constraint2: str) -> Tuple[bool, Optional[str]]:
        """Check if two version constraints overlap (have a common version range).
        
        Args:
            constraint1 (str): First version constraint.
            constraint2 (str): Second version constraint.
            
        Returns:
            Tuple[bool, Optional[str]]: A tuple containing:
                - bool: True if constraints overlap
                - Optional[str]: Error message if there's an issue, None otherwise
        """
        # Validate both constraints
        valid1, error1 = VersionConstraintValidator.validate_constraint(constraint1)
        if not valid1:
            return False, f"Invalid constraint1: {error1}"
        
        valid2, error2 = VersionConstraintValidator.validate_constraint(constraint2)
        if not valid2:
            return False, f"Invalid constraint2: {error2}"
        
        try:
            spec1 = SpecifierSet(constraint1)
            spec2 = SpecifierSet(constraint2)
            
            # For the specific case where one constraint is an exact version
            if "==" in constraint1 or "==" in constraint2:
                if "==" in constraint1:
                    exact_version = next(s.version for s in spec1 if s.operator == "==")
                    exact_ver = version.Version(exact_version)
                    return exact_ver in spec2, None
                else:
                    exact_version = next(s.version for s in spec2 if s.operator == "==")
                    exact_ver = version.Version(exact_version)
                    return exact_ver in spec1, None
            
            # Get min/max bounds from both constraints
            min1, max1 = VersionConstraintValidator.get_constraint_bounds(constraint1)
            min2, max2 = VersionConstraintValidator.get_constraint_bounds(constraint2)
            
            # If either constraint has no bounds, it's essentially unbounded
            if (min1 is None and max1 is None) or (min2 is None and max2 is None):
                return True, None
            
            # Check for definite non-overlap using range boundaries
            if min1 is not None and max2 is not None and version.Version(min1) > version.Version(max2):
                return False, None
            if min2 is not None and max1 is not None and version.Version(min2) > version.Version(max1):
                return False, None
            
            # If we have both min and max for both constraints, we can determine overlap mathematically
            if min1 and max1 and min2 and max2:
                min1_v = version.Version(min1)
                max1_v = version.Version(max1)
                min2_v = version.Version(min2)
                max2_v = version.Version(max2)
                
                # If one range is entirely within the other, they overlap
                if (min1_v <= min2_v <= max1_v) or (min2_v <= min1_v <= max2_v):
                    return True, None
            
            # For complex cases, use test versions to verify overlap
            test_versions = VersionConstraintValidator._generate_test_versions(min1, max1, min2, max2)
            
            # Check if any version satisfies both constraints
            for test_ver in test_versions:
                try:
                    ver = version.Version(test_ver)
                    if ver in spec1 and ver in spec2:
                        return True, None
                except:
                    continue
            
            return False, None
        except Exception as e:
            return False, f"Error checking constraint overlap: {e}"
    
    @staticmethod
    def normalize_constraint(constraint: str) -> Tuple[str, Optional[str]]:
        """Normalize a version constraint to a standard format.
        
        Args:
            constraint (str): Version constraint string to normalize.
            
        Returns:
            Tuple[str, Optional[str]]: A tuple containing:
                - str: Normalized constraint string
                - Optional[str]: Error message if normalization failed, None otherwise
        """
        valid, error = VersionConstraintValidator.validate_constraint(constraint)
        if not valid:
            return constraint, f"Invalid constraint: {error}"
        
        try:
            spec_set = SpecifierSet(constraint)
            return str(spec_set), None
        except Exception as e:
            return constraint, f"Error normalizing constraint: {e}"


class DependencyConstraintResolver:
    """Utility class for resolving conflicts between dependency constraints.
    
    Provides methods for checking compatibility between multiple constraints
    on the same dependency and resolving conflicts when possible.
    """
    
    def __init__(self):
        """Initialize the constraint resolver."""
        self.validator = VersionConstraintValidator()
    
    def check_constraint_compatibility(self, constraints: List[str], package_name: str) -> Tuple[bool, List[str]]:
        """Check if a list of constraints on the same package are compatible.
        
        Args:
            constraints (List[str]): List of version constraints for the same package.
            package_name (str): Name of the package being constrained.
            
        Returns:
            Tuple[bool, List[str]]: A tuple containing:
                - bool: Whether all constraints are compatible
                - List[str]: List of error messages (empty if compatible)
        """
        if not constraints:
            return True, []
        
        if len(constraints) == 1:
            valid, error = self.validator.validate_constraint(constraints[0])
            return valid, [error] if error else []
        
        errors = []
        
        # Validate all individual constraints first
        for i, constraint in enumerate(constraints):
            valid, error = self.validator.validate_constraint(constraint)
            if not valid:
                errors.append(f"Constraint {i+1} for {package_name}: {error}")
        
        if errors:
            return False, errors
        
        # Check pairwise compatibility
        for i in range(len(constraints)):
            for j in range(i + 1, len(constraints)):
                overlap, error = self.validator.constraints_overlap(constraints[i], constraints[j])
                if error:
                    errors.append(f"Error checking compatibility between constraints for {package_name}: {error}")
                elif not overlap:
                    errors.append(f"Incompatible constraints for {package_name}: '{constraints[i]}' and '{constraints[j]}' have no overlap")
        
        return len(errors) == 0, errors
    
    def resolve_constraints(self, constraints: List[str]) -> Tuple[Optional[str], List[str]]:
        """Attempt to resolve multiple constraints into a single combined constraint.
        
        Args:
            constraints (List[str]): List of version constraints to combine.
            
        Returns:
            Tuple[Optional[str], List[str]]: A tuple containing:
                - Optional[str]: Combined constraint string if successful, None otherwise
                - List[str]: List of error messages (empty if successful)
        """
        if not constraints:
            return None, ["No constraints provided"]
        
        if len(constraints) == 1:
            valid, error = self.validator.validate_constraint(constraints[0])
            return constraints[0] if valid else None, [error] if error else []
        
        try:
            # Combine all constraints using intersection
            combined_spec = SpecifierSet(constraints[0])
            for constraint in constraints[1:]:
                combined_spec &= SpecifierSet(constraint)
            
            return str(combined_spec), []
        except Exception as e:
            return None, [f"Error combining constraints: {e}"]
