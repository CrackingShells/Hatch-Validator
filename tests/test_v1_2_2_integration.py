"""Integration test for v1.2.2 schema support.

This test demonstrates the full functionality of v1.2.2 schema validation
including conda package manager support.
"""

import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from hatch_validator.core.validator_factory import ValidatorFactory
from hatch_validator.core.pkg_accessor_factory import HatchPkgAccessorFactory
from hatch_validator.core.validation_context import ValidationContext


class TestV122Integration(unittest.TestCase):
    """Integration tests for v1.2.2 schema support."""
    
    def setUp(self):
        """Set up test environment."""
        self.registry_data = {
            "registry_schema_version": "1.0.0",
            "repositories": []
        }
        self.context = ValidationContext(
            registry_data=self.registry_data,
            allow_local_dependencies=False,
            force_schema_update=False
        )
    
    def test_full_v122_package_with_conda(self):
        """Test complete v1.2.2 package with conda dependencies."""
        metadata = {
            "$schema": "https://raw.githubusercontent.com/CrackingShells/Hatch-Schemas/refs/heads/main/package/v1.2.2/hatch_pkg_metadata_schema.json",
            "package_schema_version": "1.2.2",
            "name": "bioinformatics_tool",
            "version": "2.1.0",
            "description": "A bioinformatics analysis tool using conda packages",
            "tags": ["bioinformatics", "conda", "analysis"],
            "author": {
                "name": "Research Team",
                "email": "research@example.com"
            },
            "license": {
                "name": "MIT",
                "uri": "https://opensource.org/licenses/MIT"
            },
            "repository": "https://github.com/example/bioinformatics-tool",
            "documentation": "https://bioinformatics-tool.readthedocs.io",
            "entry_point": {
                "mcp_server": "server.py",
                "hatch_mcp_server": "hatch_server.py"
            },
            "dependencies": {
                "python": [
                    {
                        "name": "numpy",
                        "version_constraint": ">=1.20.0",
                        "package_manager": "conda",
                        "channel": "conda-forge"
                    },
                    {
                        "name": "biopython",
                        "version_constraint": ">=1.79",
                        "package_manager": "conda",
                        "channel": "bioconda"
                    },
                    {
                        "name": "requests",
                        "version_constraint": ">=2.28.0",
                        "package_manager": "pip"
                    }
                ]
            },
            "tools": [
                {
                    "name": "analyze_sequence",
                    "description": "Analyze DNA/RNA sequences"
                },
                {
                    "name": "compare_genomes",
                    "description": "Compare genomic data"
                }
            ]
        }
        
        # Create validator chain
        validator = ValidatorFactory.create_validator_chain("1.2.2")
        
        # Verify validator can handle v1.2.2
        self.assertTrue(validator.can_handle("1.2.2"))
        
        # Create accessor chain
        accessor = HatchPkgAccessorFactory.create_accessor_chain("1.2.2")
        
        # Verify accessor can handle v1.2.2
        self.assertTrue(accessor.can_handle("1.2.2"))
        
        # Test accessor methods
        self.assertEqual(accessor.get_name(metadata), "bioinformatics_tool")
        self.assertEqual(accessor.get_version(metadata), "2.1.0")
        self.assertEqual(accessor.get_mcp_entry_point(metadata), "server.py")
        self.assertEqual(accessor.get_hatch_mcp_entry_point(metadata), "hatch_server.py")
        
        # Test dependency access
        deps = accessor.get_dependencies(metadata)
        self.assertIn("python", deps)
        self.assertEqual(len(deps["python"]), 3)
        
        # Verify conda dependencies
        conda_deps = [d for d in deps["python"] if d.get("package_manager") == "conda"]
        self.assertEqual(len(conda_deps), 2)
        
        # Verify pip dependencies
        pip_deps = [d for d in deps["python"] if d.get("package_manager", "pip") == "pip"]
        self.assertEqual(len(pip_deps), 1)
        
        print("\n✅ Integration test passed!")
        print(f"   - Validator chain constructed for v1.2.2")
        print(f"   - Accessor chain constructed for v1.2.2")
        print(f"   - Package metadata accessed successfully")
        print(f"   - Conda dependencies: {len(conda_deps)}")
        print(f"   - Pip dependencies: {len(pip_deps)}")
    
    def test_backward_compatibility_v121(self):
        """Test that v1.2.2 chain can handle v1.2.1 packages."""
        metadata_v121 = {
            "package_schema_version": "1.2.1",
            "name": "legacy_package",
            "version": "1.0.0",
            "description": "A legacy v1.2.1 package",
            "tags": ["legacy"],
            "author": {"name": "Legacy Author"},
            "license": {"name": "MIT"},
            "entry_point": {
                "mcp_server": "server.py",
                "hatch_mcp_server": "hatch_server.py"
            },
            "dependencies": {
                "python": [
                    {
                        "name": "requests",
                        "version_constraint": ">=2.28.0",
                        "package_manager": "pip"
                    }
                ]
            }
        }
        
        # Create v1.2.2 validator chain
        validator = ValidatorFactory.create_validator_chain("1.2.2")
        
        # Should delegate to v1.2.1 validator
        self.assertFalse(validator.can_handle("1.2.1"))
        self.assertTrue(validator.next_validator.can_handle("1.2.1"))
        
        print("\n✅ Backward compatibility test passed!")
        print(f"   - v1.2.2 chain correctly delegates to v1.2.1")


if __name__ == '__main__':
    unittest.main(verbosity=2)

