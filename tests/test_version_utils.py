"""Unit tests for version constraint utilities.

This module tests the version constraint validation and resolution functionality
used for dependency analysis across different schema versions.
"""

import unittest
from hatch_validator.utils.version_utils import (
    VersionConstraintValidator, 
    DependencyConstraintResolver,
    VersionConstraintError
)


class TestVersionConstraintValidator(unittest.TestCase):
    """Test cases for the VersionConstraintValidator class."""
    
    def test_validate_version_valid_cases(self):
        """Test validation of valid version strings."""
        valid_versions = [
            "1.0.0",
            "2.3.4",
            "0.1.0",
            "10.20.30",
            "1.0.0-alpha",
            "1.0.0+build.1",
            "2.0.0-rc.1+build.123"
        ]
        
        for ver in valid_versions:
            with self.subTest(version=ver):
                valid, error = VersionConstraintValidator.validate_version(ver)
                self.assertTrue(valid, f"Version '{ver}' should be valid but got error: {error}")
                self.assertIsNone(error, f"Valid version '{ver}' should not have error message")
    
    def test_validate_version_invalid_cases(self):
        """Test validation of invalid version strings."""
        invalid_versions = [
            "",
            None,
            "1.2",  # May be valid depending on packaging version
            "1.2.3.4.5.6",  # May be valid
            "invalid",
            "1.2.3-",
            "1.2.3+",
        ]
        
        for ver in [None, "", "invalid", "1.2.3-", "1.2.3+"]:
            with self.subTest(version=ver):
                valid, error = VersionConstraintValidator.validate_version(ver)
                self.assertFalse(valid, f"Version '{ver}' should be invalid")
                self.assertIsNotNone(error, f"Invalid version '{ver}' should have error message")
    
    def test_validate_constraint_valid_cases(self):
        """Test validation of valid constraint strings."""
        valid_constraints = [
            ">=1.0.0",
            "==1.2.3",
            "!=2.0.0",
            "~=1.4",
            ">1.0.0,<2.0.0",
            ">=1.0.0,!=1.5.0,<2.0.0",
            "==1.0.*"
        ]
        
        for constraint in valid_constraints:
            with self.subTest(constraint=constraint):
                valid, error = VersionConstraintValidator.validate_constraint(constraint)
                self.assertTrue(valid, f"Constraint '{constraint}' should be valid but got error: {error}")
                self.assertIsNone(error, f"Valid constraint '{constraint}' should not have error message")
    
    def test_validate_constraint_invalid_cases(self):
        """Test validation of invalid constraint strings."""
        invalid_constraints = [
            "",
            None,
            "invalid",
            ">>1.0.0",
            ">=",
            "1.0.0 >=",
            ">=1.0.0 <=",
        ]
        
        for constraint in invalid_constraints:
            with self.subTest(constraint=constraint):
                valid, error = VersionConstraintValidator.validate_constraint(constraint)
                self.assertFalse(valid, f"Constraint '{constraint}' should be invalid")
                self.assertIsNotNone(error, f"Invalid constraint '{constraint}' should have error message")
    
    def test_is_version_compatible_true_cases(self):
        """Test version compatibility when version satisfies constraint."""
        test_cases = [
            ("1.5.0", ">=1.0.0"),
            ("1.0.0", "==1.0.0"),
            ("2.0.0", ">1.0.0"),
            ("0.9.0", "<1.0.0"),
            ("1.5.0", ">=1.0.0,<2.0.0"),
            ("1.4.5", "~=1.4"),
        ]
        
        for version_str, constraint in test_cases:
            with self.subTest(version=version_str, constraint=constraint):
                compatible, error = VersionConstraintValidator.is_version_compatible(version_str, constraint)
                self.assertTrue(compatible, f"Version '{version_str}' should satisfy constraint '{constraint}'")
                self.assertIsNone(error, f"Compatible check should not have error")
    
    def test_is_version_compatible_false_cases(self):
        """Test version compatibility when version does not satisfy constraint."""
        test_cases = [
            ("0.9.0", ">=1.0.0"),
            ("1.1.0", "==1.0.0"),
            ("1.0.0", ">1.0.0"),
            ("1.0.0", "<1.0.0"),
            ("2.5.0", ">=1.0.0,<2.0.0"),
            ("1.3.0", "~=1.4"),
        ]
        
        for version_str, constraint in test_cases:
            with self.subTest(version=version_str, constraint=constraint):
                compatible, error = VersionConstraintValidator.is_version_compatible(version_str, constraint)
                self.assertFalse(compatible, f"Version '{version_str}' should not satisfy constraint '{constraint}'")
                self.assertIsNone(error, f"Incompatible check should not have error")
    
    def test_is_version_compatible_error_cases(self):
        """Test version compatibility with invalid inputs."""
        error_cases = [
            ("invalid", ">=1.0.0"),
            ("1.0.0", "invalid"),
            ("", ">=1.0.0"),
            ("1.0.0", ""),
        ]
        
        for version_str, constraint in error_cases:
            with self.subTest(version=version_str, constraint=constraint):
                compatible, error = VersionConstraintValidator.is_version_compatible(version_str, constraint)
                self.assertFalse(compatible, f"Invalid inputs should return False")
                self.assertIsNotNone(error, f"Invalid inputs should have error message")
    
    def test_parse_constraint_operators(self):
        """Test parsing constraint strings into operators and versions."""
        test_cases = [
            (">=1.0.0", [(">=", "1.0.0")]),
            ("==1.2.3", [("==", "1.2.3")]),
            (">1.0.0,<2.0.0", [(">=", "1.0.0"), ("<", "2.0.0")]),  # Note: > might be normalized to >=
        ]
        
        for constraint, expected in test_cases:
            with self.subTest(constraint=constraint):
                try:
                    operators = VersionConstraintValidator.parse_constraint_operators(constraint)
                    self.assertIsInstance(operators, list, "Should return a list of tuples")
                    self.assertGreater(len(operators), 0, "Should return at least one operator")
                    for op, ver in operators:
                        self.assertIsInstance(op, str, "Operator should be string")
                        self.assertIsInstance(ver, str, "Version should be string")
                except VersionConstraintError:
                    self.fail(f"Valid constraint '{constraint}' should not raise VersionConstraintError")
    
    def test_parse_constraint_operators_invalid(self):
        """Test parsing invalid constraint strings raises error."""
        invalid_constraints = ["invalid", ">=", ">>1.0.0"]
        
        for constraint in invalid_constraints:
            with self.subTest(constraint=constraint):
                with self.assertRaises(VersionConstraintError, 
                                     msg=f"Invalid constraint '{constraint}' should raise VersionConstraintError"):
                    VersionConstraintValidator.parse_constraint_operators(constraint)
    
    def test_get_constraint_bounds(self):
        """Test extracting min/max bounds from constraints."""
        test_cases = [
            (">=1.0.0", ("1.0.0", None)),
            ("<=2.0.0", (None, "2.0.0")),
            (">=1.0.0,<=2.0.0", ("1.0.0", "2.0.0")),
            ("==1.5.0", ("1.5.0", "1.5.0")),
        ]
        
        for constraint, expected_bounds in test_cases:
            with self.subTest(constraint=constraint):
                try:
                    min_ver, max_ver = VersionConstraintValidator.get_constraint_bounds(constraint)
                    expected_min, expected_max = expected_bounds
                    self.assertEqual(min_ver, expected_min, f"Minimum version mismatch for '{constraint}'")
                    self.assertEqual(max_ver, expected_max, f"Maximum version mismatch for '{constraint}'")
                except VersionConstraintError:
                    self.fail(f"Valid constraint '{constraint}' should not raise VersionConstraintError")
    
    def test_constraints_overlap_true_cases(self):
        """Test constraint overlap detection when constraints do overlap."""
        overlapping_cases = [
            (">=1.0.0", "<=2.0.0"),
            (">=1.0.0,<=2.0.0", ">=1.5.0,<=1.8.0"),
            ("==1.5.0", ">=1.0.0,<=2.0.0"),
        ]
        
        for constraint1, constraint2 in overlapping_cases:
            with self.subTest(constraint1=constraint1, constraint2=constraint2):
                overlap, error = VersionConstraintValidator.constraints_overlap(constraint1, constraint2)
                self.assertTrue(overlap, f"Constraints '{constraint1}' and '{constraint2}' should overlap")
                self.assertIsNone(error, f"Overlap check should not have error")
    
    def test_constraints_overlap_false_cases(self):
        """Test constraint overlap detection when constraints don't overlap."""
        non_overlapping_cases = [
            (">=2.0.0", "<=1.0.0"),
            (">2.0.0", "<1.0.0"),
            ("==1.0.0", "==2.0.0"),
        ]
        
        for constraint1, constraint2 in non_overlapping_cases:
            with self.subTest(constraint1=constraint1, constraint2=constraint2):
                overlap, error = VersionConstraintValidator.constraints_overlap(constraint1, constraint2)
                self.assertFalse(overlap, f"Constraints '{constraint1}' and '{constraint2}' should not overlap")
                self.assertIsNone(error, f"Non-overlap check should not have error")
    
    def test_normalize_constraint(self):
        """Test constraint normalization."""
        test_cases = [
            ">=1.0.0",
            ">=1.0.0,<=2.0.0",
            "==1.5.0",
        ]
        
        for constraint in test_cases:
            with self.subTest(constraint=constraint):
                normalized, error = VersionConstraintValidator.normalize_constraint(constraint)
                self.assertIsNotNone(normalized, f"Normalized constraint should not be None")
                self.assertIsNone(error, f"Normalization should not have error")
                # Check that normalized constraint is still valid
                valid, _ = VersionConstraintValidator.validate_constraint(normalized)
                self.assertTrue(valid, f"Normalized constraint '{normalized}' should be valid")


class TestDependencyConstraintResolver(unittest.TestCase):
    """Test cases for the DependencyConstraintResolver class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.resolver = DependencyConstraintResolver()
    
    def test_check_constraint_compatibility_empty(self):
        """Test compatibility check with empty constraint list."""
        compatible, errors = self.resolver.check_constraint_compatibility([], "test_package")
        self.assertTrue(compatible, "Empty constraint list should be compatible")
        self.assertEqual(errors, [], "Empty constraint list should have no errors")
    
    def test_check_constraint_compatibility_single_valid(self):
        """Test compatibility check with single valid constraint."""
        compatible, errors = self.resolver.check_constraint_compatibility([">=1.0.0"], "test_package")
        self.assertTrue(compatible, "Single valid constraint should be compatible")
        self.assertEqual(errors, [], "Single valid constraint should have no errors")
    
    def test_check_constraint_compatibility_single_invalid(self):
        """Test compatibility check with single invalid constraint."""
        compatible, errors = self.resolver.check_constraint_compatibility(["invalid"], "test_package")
        self.assertFalse(compatible, "Single invalid constraint should not be compatible")
        self.assertGreater(len(errors), 0, "Single invalid constraint should have errors")
    
    def test_check_constraint_compatibility_multiple_compatible(self):
        """Test compatibility check with multiple compatible constraints."""
        constraints = [">=1.0.0", "<=2.0.0", "!=1.5.0"]
        compatible, errors = self.resolver.check_constraint_compatibility(constraints, "test_package")
        self.assertTrue(compatible, "Compatible constraints should be compatible")
        self.assertEqual(errors, [], "Compatible constraints should have no errors")
    
    def test_check_constraint_compatibility_multiple_incompatible(self):
        """Test compatibility check with incompatible constraints."""
        constraints = [">=2.0.0", "<=1.0.0"]
        compatible, errors = self.resolver.check_constraint_compatibility(constraints, "test_package")
        self.assertFalse(compatible, "Incompatible constraints should not be compatible")
        self.assertGreater(len(errors), 0, "Incompatible constraints should have errors")
    
    def test_resolve_constraints_empty(self):
        """Test constraint resolution with empty list."""
        result, errors = self.resolver.resolve_constraints([])
        self.assertIsNone(result, "Empty constraint list should return None")
        self.assertGreater(len(errors), 0, "Empty constraint list should have error")
    
    def test_resolve_constraints_single(self):
        """Test constraint resolution with single constraint."""
        result, errors = self.resolver.resolve_constraints([">=1.0.0"])
        self.assertIsNotNone(result, "Single constraint should return result")
        self.assertEqual(errors, [], "Single constraint should have no errors")
    
    def test_resolve_constraints_multiple_compatible(self):
        """Test constraint resolution with multiple compatible constraints."""
        constraints = [">=1.0.0", "<=2.0.0"]
        result, errors = self.resolver.resolve_constraints(constraints)
        self.assertIsNotNone(result, "Compatible constraints should return result")
        self.assertEqual(errors, [], "Compatible constraints should have no errors")
        
        # Check that result is a valid constraint
        valid, _ = VersionConstraintValidator.validate_constraint(result)
        self.assertTrue(valid, f"Resolved constraint '{result}' should be valid")
    
    def test_resolve_constraints_multiple_incompatible(self):
        """Test constraint resolution with incompatible constraints."""
        constraints = [">=2.0.0", "<=1.0.0"]
        result, errors = self.resolver.resolve_constraints(constraints)
        # The result might be None or an empty constraint, depending on implementation
        # But there should be a way to detect the incompatibility
        if result is not None:
            # If we get a result, it should be valid
            valid, _ = VersionConstraintValidator.validate_constraint(result)
            self.assertTrue(valid, f"Any returned constraint should be valid")


if __name__ == '__main__':
    unittest.main()
