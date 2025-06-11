#!/usr/bin/env python3
import sys
import unittest
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("validator_test_results.log")
    ]
)
logger = logging.getLogger("hatch.validator_test_runner")

if __name__ == "__main__":
    # Discover and run all tests
    test_loader = unittest.TestLoader()
    
    # Run the tests
    test_suite = test_loader.discover('tests', pattern='test_*.py')
    
    logger.info("Running Hatch-Validator tests...")
    test_runner = unittest.TextTestRunner(verbosity=2)
    result = test_runner.run(test_suite)
    
    # Log test results summary
    logger.info(f"Tests run: {result.testsRun}")
    logger.info(f"Errors: {len(result.errors)}")
    logger.info(f"Failures: {len(result.failures)}")
    
    # Exit with appropriate status code
    sys.exit(not result.wasSuccessful())