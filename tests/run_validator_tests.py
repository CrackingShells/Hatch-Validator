#!/usr/bin/env python3
"""Test runner for Hatch-Validator tests.

This module runs tests for schema retrieval and package validation functionality.
"""
import sys
import unittest
import logging
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

if __name__ == "__main__":
    # Add parent directory to path for imports
    sys.path.insert(0, str(Path(__file__).parent.parent))
      # Discover and run tests
    test_loader = unittest.TestLoader()
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("Usage: python run_validator_tests.py [option]")
        print("Options:")
        print("  --schemas-only           Run only schema retriever tests")
        print("  --validator-only         Run only package validator tests")
        print("  --schema-validators-only Run only schema validator framework tests")
        print("  --v1-1-0-only           Run only v1.1.0 validator implementation tests")
        print("  --dependency-graph-only  Run only dependency graph utility tests")
        print("  --version-utils-only     Run only version constraint utility tests")
        print("  --registry-client-only   Run only registry client utility tests")
        print("  --dependency-v1-1-0-only Run only v1.1.0 dependency validation tests")
        print("  --all                    Run all tests explicitly")
        print("  (no option)              Run all tests using discovery")
        sys.exit(0)
    elif len(sys.argv) > 1 and sys.argv[1] == "--schemas-only":
        # Run only schema retriever integration tests (network tests)
        logger.info("Running schema retriever integration tests only...")
        test_suite = test_loader.loadTestsFromName("test_schemas_retriever.TestSchemaRetrieverIntegration")
    elif len(sys.argv) > 1 and sys.argv[1] == "--validator-only":
        # Run only package validator tests
        logger.info("Running package validator tests only...")
        test_suite = test_loader.loadTestsFromName("test_package_validator.TestHatchPackageValidator")
    elif len(sys.argv) > 1 and sys.argv[1] == "--schema-validators-only":
        # Run only schema validator framework tests
        logger.info("Running schema validator framework tests only...")
        test_suite = test_loader.loadTestsFromName("test_schema_validators")
    elif len(sys.argv) > 1 and sys.argv[1] == "--v1-1-0-only":
        # Run only v1.1.0 validator implementation tests
        logger.info("Running v1.1.0 validator implementation tests only...")
        test_suite = test_loader.loadTestsFromName("test_schema_validators_v1_1_0")
    elif len(sys.argv) > 1 and sys.argv[1] == "--dependency-graph-only":
        # Run only dependency graph utility tests
        logger.info("Running dependency graph utility tests only...")
        test_suite = test_loader.loadTestsFromName("test_dependency_graph.TestDependencyGraph")
    elif len(sys.argv) > 1 and sys.argv[1] == "--version-utils-only":
        # Run only version constraint utility tests
        logger.info("Running version constraint utility tests only...")
        test_suite = test_loader.loadTestsFromName("test_version_utils")
    elif len(sys.argv) > 1 and sys.argv[1] == "--registry-client-only":
        # Run only registry client utility tests
        logger.info("Running registry client utility tests only...")
        test_suite = test_loader.loadTestsFromName("test_registry_client")
    elif len(sys.argv) > 1 and sys.argv[1] == "--dependency-v1-1-0-only":
        # Run only v1.1.0 dependency validation tests
        logger.info("Running v1.1.0 dependency validation tests only...")
        test_suite = test_loader.loadTestsFromName("test_dependency_validation_v1_1_0")
    elif len(sys.argv) > 1 and sys.argv[1] == "--all":
        # Run all tests explicitly
        logger.info("Running all Hatch-Validator tests...")
        test_modules = [
            "test_schemas_retriever",
            "test_package_validator", 
            "test_schema_validators",
            "test_schema_validators_v1_1_0",
            "test_dependency_graph",
            "test_version_utils",
            "test_registry_client",
            "test_dependency_validation_v1_1_0"
        ]
        test_suite = unittest.TestSuite()
        for module_name in test_modules:
            try:
                module_tests = test_loader.loadTestsFromName(module_name)
                test_suite.addTest(module_tests)
                logger.info(f"Added tests from {module_name}")
            except Exception as e:
                logger.warning(f"Could not load tests from {module_name}: {e}")
    else:
        # Run all tests using discovery as fallback
        logger.info("Running all Hatch-Validator tests using discovery...")
        current_dir = Path(__file__).parent
        test_suite = test_loader.discover(str(current_dir), pattern='test_*.py')

    # Run the tests
    test_runner = unittest.TextTestRunner(verbosity=2)
    result = test_runner.run(test_suite)
    
    # Log test results summary
    logger.info(f"Tests run: {result.testsRun}")
    logger.info(f"Errors: {len(result.errors)}")
    logger.info(f"Failures: {len(result.failures)}")
    
    # Exit with appropriate status code
    sys.exit(not result.wasSuccessful())