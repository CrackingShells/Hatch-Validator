#!/usr/bin/env python3
"""Development test runner for Hatch-Validator refactoring.

This module runs development tests for the enhanced Chain of Responsibility pattern
implementation and other refactoring-related tests. It's designed to support the
refactoring process with targeted test execution.
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
        logging.FileHandler("dev_test_results.log")
    ]
)
logger = logging.getLogger("hatch.dev_test_runner")


def configure_parser():
    """Configure command-line argument parser.
    
    Returns:
        argparse.ArgumentParser: Configured argument parser
    """
    parser = argparse.ArgumentParser(
        description="Run development tests for Hatch-Validator refactoring",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    # Create test groups
    test_group = parser.add_argument_group("Test selection")
    
    # Add mutual exclusion for test types
    test_type = test_group.add_mutually_exclusive_group()
    test_type.add_argument(
        "--all",
        action="store_true",
        help="Run all development tests"
    )
    test_type.add_argument(
        "--validator-chain",
        action="store_true",
        help="Run Chain of Responsibility validator tests"
    )
    test_type.add_argument(
        "--validator-factory",
        action="store_true",
        help="Run ValidatorFactory tests"
    )
    test_type.add_argument(
        "--delegation",
        action="store_true",
        help="Run delegation mechanism tests"
    )
    test_type.add_argument(
        "--validators",
        action="store_true",
        help="Run all validator implementation tests"
    )
    test_type.add_argument(
        "--v110-implementation",
        action="store_true",
        help="Run v1.1.0 validator implementation tests"
    )
    test_type.add_argument(
        "--custom",
        metavar="MODULE_OR_CLASS",
        help="Run specific test module or class (e.g., 'dev_test_validator_chain.TestValidatorEnhancements')"
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
    test_suite = unittest.TestSuite()
    
    # Load the appropriate tests based on arguments
    if args.all:
        # Run all development tests by discovering them
        logger.info("Running all development tests...")
        dev_tests = test_loader.discover(str(Path(__file__).parent), pattern='dev_test_*.py')
        test_suite.addTest(dev_tests)
    elif args.validator_chain:
        # Run Chain of Responsibility tests
        logger.info("Running Chain of Responsibility validator tests...")
        try:
            test_suite.addTest(test_loader.loadTestsFromName("tests.dev_test_validator_chain"))
        except (ImportError, AttributeError) as e:
            logger.error(f"Failed to load validator chain tests: {e}")
            return False
    
    elif args.validator_factory:
        # Run ValidatorFactory tests
        logger.info("Running ValidatorFactory tests...")
        try:
            test_suite.addTest(test_loader.loadTestsFromName("tests.dev_test_validator_factory"))
        except (ImportError, AttributeError) as e:
            logger.error(f"Failed to load validator factory tests: {e}")
            return False
    elif args.delegation:
        # Run delegation mechanism tests
        logger.info("Running delegation mechanism tests...")
        try:
            test_suite.addTest(test_loader.loadTestsFromName(
                "tests.dev_test_validator_chain.TestValidatorEnhancements.test_base_validator_delegation"
            ))
            test_suite.addTest(test_loader.loadTestsFromName(
                "tests.dev_test_validator_chain.TestValidatorEnhancements.test_validator_no_next_raises"
            ))
        except (ImportError, AttributeError) as e:
            logger.error(f"Failed to load delegation tests: {e}")
            return False
    elif args.validators:
        # Run all validator implementation tests
        logger.info("Running all validator implementation tests...")
        try:
            test_suite.addTest(test_loader.loadTestsFromName("tests.dev_test_validator_implementations"))
        except (ImportError, AttributeError) as e:
            logger.error(f"Failed to load validator implementation tests: {e}")
            # Try to fall back to existing tests
            try:
                test_suite.addTest(test_loader.loadTestsFromName(
                    "tests.dev_test_validator_chain.TestValidatorEnhancements.test_v110_validator_implementation"
                ))
                logger.warning("Falling back to v1.1.0 validator implementation tests")
            except (ImportError, AttributeError):
                logger.error("No validator implementation tests available")
                return False
    elif args.v110_implementation:
        # Run v1.1.0 validator implementation tests
        logger.info("Running v1.1.0 validator implementation tests...")
        try:
            test_suite.addTest(test_loader.loadTestsFromName(
                "tests.dev_test_validator_chain.TestValidatorEnhancements.test_v110_validator_implementation"
            ))
        except (ImportError, AttributeError) as e:
            logger.error(f"Failed to load v1.1.0 implementation tests: {e}")
            return False
    
    elif args.custom:
        # Run custom specified tests
        logger.info(f"Running custom tests: {args.custom}")
        try:
            test_suite.addTest(test_loader.loadTestsFromName(args.custom))
        except (ImportError, AttributeError) as e:
            logger.error(f"Failed to load custom tests '{args.custom}': {e}")
            return False
    else:
        # Default: Run the main validator chain tests
        logger.info("Running default Chain of Responsibility validator tests...")
        try:
            test_suite.addTest(test_loader.loadTestsFromName("tests.dev_test_validator_chain"))
        except (ImportError, AttributeError) as e:
            logger.error(f"Failed to load default tests: {e}")
            return False

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
