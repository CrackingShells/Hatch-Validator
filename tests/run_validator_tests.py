#!/usr/bin/env python3
"""Test runner for Hatch-Validator tests.

This module runs tests for schema retrieval and package validation functionality.
"""
import sys
import unittest
import logging
import argparse
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("validator_test_results.log")
    ]
)
logger = logging.getLogger("hatch.validator_test_runner")


def configure_parser():
    """Configure command-line argument parser.
    
    Returns:
        argparse.ArgumentParser: Configured argument parser
    """
    parser = argparse.ArgumentParser(
        description="Run tests for Hatch-Validator",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    # Create test groups
    test_group = parser.add_argument_group("Test selection")
    
    # Add mutual exclusion for test types
    test_type = test_group.add_mutually_exclusive_group()
    test_type.add_argument(
        "--schemas-only",
        action="store_true",
        help="Run only schema retriever integration tests (network tests)"
    )
    test_type.add_argument(
        "--validator-only",
        action="store_true",
        help="Run only package validator tests"
    )
    test_type.add_argument(
        "--schema-validators-only",
        action="store_true",
        help="Run only schema validator framework tests"
    )
    test_type.add_argument(
        "--validator_for_pkg_v1_1_0_only",
        action="store_true",
        help="Run only v1.1.0 validator implementation tests"
    )
    test_type.add_argument(
        "--validator_for_pkg_v1_2_0_only",
        action="store_true",
        help="Run only v1.2.0 validator implementation tests"
    )
    test_type.add_argument(
        "--dependency-graph-only",
        action="store_true",
        help="Run only dependency graph utility tests"
    )
    test_type.add_argument(
        "--version-utils-only",
        action="store_true",
        help="Run only version constraint utility tests"
    )
    test_type.add_argument(
        "--dependency-v1-1-0-only",
        action="store_true",
        help="Run only v1.1.0 dependency validation tests"
    )
    test_type.add_argument(
        "--all",
        action="store_true",
        help="Run all tests explicitly"
    )
    test_type.add_argument(
        "--custom",
        metavar="MODULE_OR_CLASS",
        help="Run specific test module or class"
    )
    
    # Add options for test execution
    options_group = parser.add_argument_group("Test options")
    options_group.add_argument(
        "--verbose", "-v",
        action="count",
        default=1,
        help="Increase verbosity level (can be specified multiple times)"
    )
    options_group.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Minimal output"
    )
    options_group.add_argument(
        "--failfast",
        action="store_true",
        help="Stop on first failure"
    )
    
    return parser


def run_tests(args):
    """Run the selected tests.
    
    Args:
        args: Command-line arguments from argparse
        
    Returns:
        bool: True if tests passed, False otherwise
    """
    # Add parent directory to path for imports
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    # Determine test verbosity level
    verbosity = 0 if args.quiet else args.verbose
    
    # Prepare test loader
    test_loader = unittest.TestLoader()
    
    # Determine which tests to run
    if args.schemas_only:
        logger.info("Running schema retriever integration tests only...")
        test_suite = test_loader.loadTestsFromName("test_schemas_retriever.TestSchemaRetrieverIntegration")
    elif args.validator_for_pkg_v1_1_0_only:
        logger.info("Running package validator tests only...")
        test_suite = test_loader.loadTestsFromName("test_package_validator.TestHatchPackageValidator")
    elif args.validator_for_pkg_v1_2_0_only:
        logger.info("Running v1.2.0 validator implementation tests only...")
        test_suite = test_loader.loadTestsFromName("test_package_validator_for_v1_2_0.TestHatchPackageValidator_v1_2_0")
    elif args.schema_validators_only:
        logger.info("Running schema validator framework tests only...")
        test_suite = test_loader.loadTestsFromName("test_schema_validators")
    elif args.dependency_graph_only:
        logger.info("Running dependency graph utility tests only...")
        test_suite = test_loader.loadTestsFromName("test_dependency_graph.TestDependencyGraph")
    elif args.version_utils_only:
        logger.info("Running version constraint utility tests only...")
        test_suite = test_loader.loadTestsFromName("test_version_utils")
    elif args.dependency_v1_1_0_only:
        logger.info("Running v1.1.0 dependency validation tests only...")
        test_suite = test_loader.loadTestsFromName("test_dependency_validation_v1_1_0")
    elif args.all:
        # Run all tests explicitly
        logger.info("Running all Hatch-Validator tests...")
        test_modules = [
            "test_schemas_retriever",
            "test_package_validator", 
            "test_schema_validators",
            "test_schema_validators_v1_1_0",
            "test_dependency_graph",
            "test_version_utils",
            "test_dependency_validation_v1_1_0",
            "test_package_validator_for_v1_2_0"
        ]
        test_suite = unittest.TestSuite()
        for module_name in test_modules:
            try:
                module_tests = test_loader.loadTestsFromName(module_name)
                test_suite.addTest(module_tests)
                logger.info(f"Added tests from {module_name}")
            except Exception as e:
                logger.warning(f"Could not load tests from {module_name}: {e}")
    elif args.custom:
        # Run custom specified tests
        logger.info(f"Running custom tests: {args.custom}")
        try:
            test_suite = test_loader.loadTestsFromName(args.custom)
        except (ImportError, AttributeError) as e:
            logger.error(f"Failed to load custom tests '{args.custom}': {e}")
            return False
    else:
        # Run all tests using discovery as fallback
        logger.info("Running all Hatch-Validator tests using discovery...")
        current_dir = Path(__file__).parent
        test_suite = test_loader.discover(str(current_dir), pattern='test_*.py')

    # Run the tests
    test_runner = unittest.TextTestRunner(
        verbosity=verbosity,
        failfast=args.failfast
    )
    result = test_runner.run(test_suite)
    
    # Log test results summary
    logger.info(f"Tests run: {result.testsRun}")
    logger.info(f"Errors: {len(result.errors)}")
    logger.info(f"Failures: {len(result.failures)}")
    
    if result.wasSuccessful():
        logger.info("All tests PASSED!")
    else:
        logger.warning("Some tests FAILED!")
        
    return result.wasSuccessful()


if __name__ == "__main__":
    parser = configure_parser()
    args = parser.parse_args()
    
    success = run_tests(args)
    sys.exit(0 if success else 1)