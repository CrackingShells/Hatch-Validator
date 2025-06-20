"""Unit tests for dependency graph utilities.

This module tests the core graph algorithms used for dependency analysis,
including cycle detection, topological sorting, and path finding.
"""

import unittest
import logging
from hatch_validator.utils.dependency_graph import DependencyGraph, DependencyGraphError

logger = logging.getLogger("hatch.validator_test_dependency_graph")
logger.setLevel(logging.DEBUG)

class TestDependencyGraph(unittest.TestCase):
    """Test cases for the DependencyGraph class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.empty_graph = DependencyGraph()
        
        # Simple acyclic graph: A -> B -> C
        self.simple_acyclic = DependencyGraph({
            'A': ['B'],
            'B': ['C'],
            'C': []
        })
        
        # Graph with cycle: A -> B -> C -> A
        self.simple_cyclic = DependencyGraph({
            'A': ['B'],
            'B': ['C'],
            'C': ['A']
        })
        
        # Complex acyclic graph
        self.complex_acyclic = DependencyGraph({
            'app': ['utils', 'db'],
            'utils': ['math'],
            'db': ['utils'],
            'math': [],
            'standalone': []
        })
        
        # Complex graph with multiple cycles
        self.complex_cyclic = DependencyGraph({
            'A': ['B'],
            'B': ['C', 'D'],
            'C': ['A'],  # Cycle: A -> B -> C -> A
            'D': ['E'],
            'E': ['D']   # Cycle: D -> E -> D
        })
    
    def test_empty_graph_no_cycles(self):
        """Test that empty graph has no cycles."""
        has_cycles, cycles = self.empty_graph.detect_cycles()
        self.assertFalse(has_cycles, "Empty graph should not have any cycles")
        self.assertEqual(cycles, [], "Empty graph should return empty cycles list")
    
    def test_simple_acyclic_no_cycles(self):
        """Test that simple acyclic graph has no cycles."""
        has_cycles, cycles = self.simple_acyclic.detect_cycles()
        self.assertFalse(has_cycles, "Simple acyclic graph (A->B->C) should not have cycles")
        self.assertEqual(cycles, [], "Simple acyclic graph should return empty cycles list")
    
    def test_simple_cyclic_detects_cycle(self):
        """Test that simple cyclic graph detects the cycle."""
        has_cycles, cycles = self.simple_cyclic.detect_cycles()
        self.assertTrue(has_cycles, "Simple cyclic graph (A->B->C->A) should detect cycles")
        self.assertEqual(len(cycles), 1, "Simple cyclic graph should detect exactly one cycle")
        # The cycle should be A -> B -> C -> A
        cycle = cycles[0]
        self.assertIn('A', cycle, "Detected cycle should contain package A")
        self.assertIn('B', cycle, "Detected cycle should contain package B")
        self.assertIn('C', cycle, "Detected cycle should contain package C")
    
    def test_complex_acyclic_no_cycles(self):
        """Test that complex acyclic graph has no cycles."""
        has_cycles, cycles = self.complex_acyclic.detect_cycles()
        self.assertFalse(has_cycles, "Complex acyclic graph should not have cycles")
        self.assertEqual(cycles, [], "Complex acyclic graph should return empty cycles list")
    
    def test_complex_cyclic_detects_multiple_cycles(self):
        """Test that complex graph detects multiple cycles."""
        has_cycles, cycles = self.complex_cyclic.detect_cycles()
        self.assertTrue(has_cycles, "Complex graph with multiple cycles should detect cycles")
        self.assertGreaterEqual(len(cycles), 1, "Complex graph should detect at least one cycle")
    
    def test_topological_sort_acyclic(self):
        """Test topological sort on acyclic graph."""
        success, sorted_packages = self.simple_acyclic.topological_sort()
        self.assertTrue(success, "Topological sort should succeed on acyclic graph")

        # Topological sort puts the roots before the children
        # In the context of dependencies checking, we want the reverse order
        dependencies_first = list(reversed(sorted_packages))

        # Check that dependencies come before dependents
        # In a topological sort, if A depends on B, then B should come BEFORE A in the sorted order
        a_index = dependencies_first.index('A')
        b_index = dependencies_first.index('B')
        c_index = dependencies_first.index('C')
        
        # The implementation correctly puts dependencies first (C depends on nothing, B depends on C, A depends on B)
        # So order should be: C, B, A
        self.assertLess(c_index, b_index, "Package C should come before B in topological order (B depends on C)")
        self.assertLess(b_index, a_index, "Package B should come before A in topological order (A depends on B)")
    
    def test_topological_sort_cyclic_fails(self):
        """Test that topological sort fails on cyclic graph."""
        success, sorted_packages = self.simple_cyclic.topological_sort()
        self.assertFalse(success, "Topological sort should fail on cyclic graph")
        self.assertEqual(sorted_packages, [], "Failed topological sort should return empty list")
    
    def test_find_dependency_path_exists(self):
        """Test finding a path when one exists."""
        path = self.simple_acyclic.find_dependency_path('A', 'C')
        self.assertIsNotNone(path, "Should find a path from A to C in acyclic graph")
        self.assertEqual(path, ['A', 'B', 'C'], "Path from A to C should be A->B->C")
    
    def test_find_dependency_path_not_exists(self):
        """Test finding a path when none exists."""
        path = self.simple_acyclic.find_dependency_path('C', 'A')
        self.assertIsNone(path, "Should not find a path from C to A (reverse direction)")
    
    def test_find_dependency_path_same_package(self):
        """Test finding a path to the same package."""
        path = self.simple_acyclic.find_dependency_path('A', 'A')
        self.assertEqual(path, ['A'], "Path from package to itself should be [package]")
    
    def test_add_dependency(self):
        """Test adding dependencies to the graph."""
        graph = DependencyGraph()
        graph.add_dependency('pkg1', 'pkg2')
        graph.add_dependency('pkg1', 'pkg3')
        
        self.assertEqual(graph.get_direct_dependencies('pkg1'), ['pkg2', 'pkg3'], 
                        "Package pkg1 should have dependencies ['pkg2', 'pkg3'] after adding them")
    
    def test_add_package(self):
        """Test adding a package without dependencies."""
        graph = DependencyGraph()
        graph.add_package('standalone')
        
        self.assertEqual(graph.get_direct_dependencies('standalone'), [], 
                        "Standalone package should have no dependencies")
        self.assertIn('standalone', graph.get_all_packages(), 
                     "Standalone package should be present in all packages")
    
    def test_get_all_packages(self):
        """Test getting all packages from the graph."""
        packages = self.simple_acyclic.get_all_packages()
        expected = {'A', 'B', 'C'}
        self.assertEqual(packages, expected, "Should return all packages in the graph including dependencies")
    
    def test_get_direct_dependencies(self):
        """Test getting direct dependencies of a package."""
        deps = self.simple_acyclic.get_direct_dependencies('A')
        self.assertEqual(deps, ['B'], "Package A should have direct dependency on B")
        
        deps = self.simple_acyclic.get_direct_dependencies('C')
        self.assertEqual(deps, [], "Package C should have no dependencies")
    
    def test_get_all_dependencies_acyclic(self):
        """Test getting all transitive dependencies on acyclic graph."""
        all_deps = self.simple_acyclic.get_all_dependencies('A')
        expected = {'B', 'C'}
        self.assertEqual(all_deps, expected, "Package A should have transitive dependencies B and C")
    
    def test_get_all_dependencies_cyclic_raises_error(self):
        """Test that getting all dependencies on cyclic graph raises error."""
        with self.assertRaises(DependencyGraphError):
            self.simple_cyclic.get_all_dependencies('A')
    
    def test_from_dependency_dict(self):
        """Test creating graph from dependency dictionary."""
        deps = {
            'pkg1': ['pkg2', 'pkg3'],
            'pkg2': ['pkg3'],
            'pkg3': []
        }
        graph = DependencyGraph.from_dependency_dict(deps)
        
        self.assertEqual(graph.get_direct_dependencies('pkg1'), ['pkg2', 'pkg3'], 
                        "pkg1 should have dependencies pkg2 and pkg3")
        self.assertEqual(graph.get_direct_dependencies('pkg2'), ['pkg3'], 
                        "pkg2 should have dependency pkg3")
        self.assertEqual(graph.get_direct_dependencies('pkg3'), [], 
                        "pkg3 should have no dependencies")
    
    def test_self_dependency_cycle(self):
        """Test detection of self-dependency cycles."""
        graph = DependencyGraph({
            'A': ['A']  # Self-dependency
        })
        
        has_cycles, cycles = graph.detect_cycles()
        self.assertTrue(has_cycles, "Graph with self-dependency should detect cycle")
        self.assertEqual(len(cycles), 1, "Self-dependency should create exactly one cycle")
    
    def test_complex_path_finding(self):
        """Test path finding in complex graph."""
        path = self.complex_acyclic.find_dependency_path('app', 'math')
        self.assertIsNotNone(path, "Should find path from app to math in complex graph")
        # Should find path: app -> utils -> math
        self.assertEqual(path, ['app', 'utils', 'math'], "Path should be app->utils->math")
    
    def test_isolated_packages(self):
        """Test handling of isolated packages in the graph."""
        graph = DependencyGraph({
            'connected1': ['connected2'],
            'connected2': [],
            'isolated': []
        })
        
        packages = graph.get_all_packages()
        expected = {'connected1', 'connected2', 'isolated'}
        self.assertEqual(packages, expected, "Should include both connected and isolated packages")
        
        # Should be able to sort even with isolated packages
        success, sorted_packages = graph.topological_sort()
        self.assertTrue(success, "Topological sort should succeed with isolated packages")
        self.assertEqual(len(sorted_packages), 3, "Should include all packages in topological sort")


if __name__ == '__main__':
    unittest.main()
