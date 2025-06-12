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
    if len(sys.argv) > 1 and sys.argv[1] == "--schemas-only":
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
    else:
        # Run all tests
        logger.info("Running all Hatch-Validator tests...")
        test_suite = test_loader.discover('.', pattern='test_*.py')

    # Run the tests
    test_runner = unittest.TextTestRunner(verbosity=2)
    result = test_runner.run(test_suite)
    
    # Log test results summary
    logger.info(f"Tests run: {result.testsRun}")
    logger.info(f"Errors: {len(result.errors)}")
    logger.info(f"Failures: {len(result.failures)}")
    
    # Exit with appropriate status code
    sys.exit(not result.wasSuccessful())