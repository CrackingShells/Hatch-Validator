"""Test utilities for handling singletons in tests.

This module provides utilities for properly handling singleton objects
in test environments, particularly for setup and teardown operations.
"""

import functools
from typing import Any, Callable, Type, TypeVar

from hatch_validator.utils.registry_client import RegistryManager

T = TypeVar('T')


def reset_registry_manager_for_test(test_method: Callable) -> Callable:
    """Decorator to reset the RegistryManager singleton before and after a test.
    
    Args:
        test_method (Callable): Test method to decorate.
        
    Returns:
        Callable: Wrapped test method with singleton reset.
    """
    @functools.wraps(test_method)
    def wrapper(self, *args, **kwargs):
        # Reset before test
        RegistryManager.reset_instance()
        try:
            # Run the test
            return test_method(self, *args, **kwargs)
        finally:
            # Reset after test
            RegistryManager.reset_instance()
    
    return wrapper


class SingletonTestMixin:
    """Mixin class for test cases that need to handle singletons.
    
    This mixin provides methods for setting up and tearing down
    singleton instances for testing.
    """
    
    def setUp_singletons(self):
        """Reset all singletons before test."""
        RegistryManager.reset_instance()
    
    def tearDown_singletons(self):
        """Reset all singletons after test."""
        RegistryManager.reset_instance()
