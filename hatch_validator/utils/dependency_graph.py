"""Graph utilities for dependency analysis.

This module provides utilities for working with dependency graphs,
including cycle detection and path analysis that are independent
of specific schema versions.
"""

from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict, deque


class DependencyGraphError(Exception):
    """Exception raised for dependency graph related errors."""
    pass


class DependencyGraph:
    """Utility class for working with dependency graphs.
    
    Provides methods for building graphs, detecting cycles, and other
    graph operations that are independent of schema version.
    """
    
    def __init__(self, adjacency_list: Optional[Dict[str, List[Dict]]] = None):
        """Initialize the dependency graph.
        
        Args:
            adjacency_list (Dict[str, List[Dict]], optional): Initial adjacency list.
                Maps package names to their direct dependencies. Each dependency is a dict
                with keys: name, version_constraint, resolved_version. Defaults to None.
        """
        self.adjacency_list = adjacency_list or {}

    def to_dict(self) -> Dict[str, List[Dict]]:
        """Convert the graph to a dictionary representation.
        
        Returns:
            Dict[str, List[Dict]]: Adjacency list representation of the graph.
        """
        return self.adjacency_list.copy()

    def __str__(self) -> str:
        """String representation of the dependency graph.
        
        Returns:
            str: String representation of the adjacency list.
        """
        return str(self.to_dict())
        
    def __repr__(self) -> str:
        """Official string representation for debugging."""
        return f"{self.__class__.__name__}({self.to_dict()})"
        
    def add_dependency(self, package: str, dependency: Dict) -> None:
        """Add a dependency relationship to the graph.
        
        Args:
            package (str): The package that depends on another package.
            dependency (Dict): Dependency object with keys: name, version_constraint, resolved_version.
        """
        if package not in self.adjacency_list:
            self.adjacency_list[package] = []
        
        dep_name = dependency.get("name")
        if not dep_name:
            raise ValueError("Dependency dict must contain 'name' key")
        
        # Avoid duplicates by name and resolved_version
        existing = any(
            d.get("name") == dep_name and d.get("resolved_version") == dependency.get("resolved_version")
            for d in self.adjacency_list[package]
        )
        if not existing:
            self.adjacency_list[package].append(dependency)
            
    def add_package(self, package: str) -> None:
        """Add a package to the graph without dependencies.
        
        Args:
            package (str): The package name to add.
        """
        if package not in self.adjacency_list:
            self.adjacency_list[package] = []
    
    def _get_dependency_name(self, dependency: Dict) -> str:
        """Extract dependency name from dict format.
        
        Args:
            dependency (Dict): Dependency in dict format.
            
        Returns:
            str: The dependency name.
        """
        return dependency.get("name", "")
    
    def get_all_packages(self) -> Set[str]:
        """Get all packages in the graph.
        
        Returns:
            Set[str]: Set of all package names in the graph.
        """
        packages = set(self.adjacency_list.keys())
        for deps in self.adjacency_list.values():
            for dep in deps:
                packages.add(self._get_dependency_name(dep))
        return packages
    
    def detect_cycles(self) -> Tuple[bool, List[List[str]]]:
        """Detect cycles in the dependency graph using DFS.
        
        Uses depth-first search with three colors (white, gray, black) to detect
        cycles in the directed graph. Gray nodes indicate a back edge which
        forms a cycle.
        
        Returns:
            Tuple[bool, List[List[str]]]: A tuple containing:
                - bool: Whether cycles were detected
                - List[List[str]]: List of cycles found, each represented as a path
        """
        # Color states: 0 = white (unvisited), 1 = gray (visiting), 2 = black (visited)
        colors = defaultdict(int)
        cycles = []
        path = []
        
        def dfs(node: str) -> bool:
            """Depth-first search helper function.
            
            Args:
                node (str): Current node being visited.
                
            Returns:
                bool: True if a cycle is found from this node.
            """
            if colors[node] == 1:  # Gray - back edge found, cycle detected
                # Find the cycle in the current path
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                cycles.append(cycle)
                return True
            
            if colors[node] == 2:  # Black - already processed
                return False
            
            # Mark as gray (visiting)
            colors[node] = 1
            path.append(node)
              # Visit all dependencies
            for dep in self.adjacency_list.get(node, []):
                dep_name = self._get_dependency_name(dep)
                if dfs(dep_name):
                    # Continue searching for more cycles instead of returning immediately
                    pass
            
            # Mark as black (visited)
            colors[node] = 2
            path.pop()
            return False
        
        # Check all nodes to find all cycles
        for package in self.get_all_packages():
            if colors[package] == 0:  # White - unvisited
                dfs(package)
        
        return len(cycles) > 0, cycles
    
    def topological_sort(self) -> Tuple[bool, List[str]]:
        """Perform topological sort of the dependency graph.
        
        Returns packages in an order where dependencies come after their dependents.
        It is possible users may expect the reverse order (dependencies before dependents),
        but this implementation follows the standard convention. Simply reverse the result
        if the reverse order is desired.
        Only works for acyclic graphs.
        
        Returns:
            Tuple[bool, List[str]]: A tuple containing:
                - bool: Whether the sort was successful (graph is acyclic)
                - List[str]: Topologically sorted list of packages
        """
        # First check if the graph has cycles
        has_cycles, _ = self.detect_cycles()
        if has_cycles:
            return False, []
        
        # Kahn's algorithm
        in_degree = defaultdict(int)
        all_packages = self.get_all_packages()
        
        # Calculate in-degrees
        for package in all_packages:
            if package not in in_degree:
                in_degree[package] = 0        
        for package, deps in self.adjacency_list.items():
            for dep in deps:
                dep_name = self._get_dependency_name(dep)
                in_degree[dep_name] += 1
        
        # Start with packages that have no incoming edges
        queue = deque([pkg for pkg in all_packages if in_degree[pkg] == 0])
        result = []
        
        while queue:
            current = queue.popleft()
            result.append(current)            
            # Remove edges from current package
            for dep in self.adjacency_list.get(current, []):
                dep_name = self._get_dependency_name(dep)
                in_degree[dep_name] -= 1
                if in_degree[dep_name] == 0:
                    queue.append(dep_name)
        
        return len(result) == len(all_packages), result
    
    def find_dependency_path(self, start: str, target: str) -> Optional[List[str]]:
        """Find a path from start package to target package.
        
        Uses breadth-first search to find the shortest dependency path.
        
        Args:
            start (str): Starting package name.
            target (str): Target package name.
            
        Returns:
            Optional[List[str]]: Path from start to target, or None if no path exists.
        """
        if start == target:
            return [start]
        
        queue = deque([(start, [start])])
        visited = {start}        
        while queue:
            current, path = queue.popleft()
            
            for dep in self.adjacency_list.get(current, []):
                dep_name = self._get_dependency_name(dep)
                if dep_name == target:
                    return path + [dep_name]
                
                if dep_name not in visited:
                    visited.add(dep_name)
                    queue.append((dep_name, path + [dep_name]))
        
        return None      
    
    @classmethod
    def from_dependency_dict(cls, dependencies: Dict[str, List[Dict]]) -> 'DependencyGraph':
        """Create a dependency graph from a dependency dictionary.
        
        Args:
            dependencies (Dict[str, List[Dict]]): Dictionary mapping package names
                to their direct dependencies.
                
        Returns:
            DependencyGraph: New dependency graph instance.
        """
        return cls(adjacency_list=dict(dependencies))
    
    def get_direct_dependencies(self, package: str) -> List[str]:
        """Get direct dependencies of a package.
        
        Args:
            package (str): Package name to get dependencies for.
            
        Returns:
            List[str]: List of direct dependency names.
        """
        deps = self.adjacency_list.get(package, [])
        return [self._get_dependency_name(dep) for dep in deps]    
    
    def get_direct_dependency_objects(self, package: str) -> List[Dict]:
        """Get direct dependency objects of a package.
        
        Args:
            package (str): Package name to get dependencies for.
            
        Returns:
            List[Dict]: List of direct dependency objects.
        """
        return self.adjacency_list.get(package, []).copy()
    
    def get_install_order_dependencies(self) -> List[Dict]:
        """Return install-ready dependency objects in topological order.
        
        Returns a list of unique dependency objects in the order they should be installed,
        with duplicates removed (keeping the first occurrence).
        
        Returns:
            List[Dict]: List of dependency objects with keys: name, version_constraint, resolved_version.
            
        Raises:
            DependencyGraphError: If the dependency graph contains cycles.
        """
        ok, order = self.topological_sort()
        if not ok:
            raise DependencyGraphError("Dependency graph contains cycles")
        
        # Collect all dependency objects in install order
        seen = set()
        result = []
        
        for pkg in order:
            for dep in self.adjacency_list.get(pkg, []):
                dep_name = dep.get("name")
                resolved_version = dep.get("resolved_version")
                # Use (name, resolved_version) as unique key
                dep_key = (dep_name, resolved_version)
                if dep_key not in seen:
                    seen.add(dep_key)
                    result.append(dep)
        
        return result
    
    def get_all_dependencies(self, package: str) -> Set[str]:
        """Get all transitive dependencies of a package.
        
        Args:
            package (str): Package name to get all dependencies for.
            
        Returns:
            Set[str]: Set of all transitive dependencies.
            
        Raises:
            DependencyGraphError: If the graph contains cycles.
        """
        has_cycles, cycles = self.detect_cycles()
        if has_cycles:
            raise DependencyGraphError(f"Cannot compute transitive dependencies: graph contains cycles: {cycles}")
        
        visited = set()
        stack = [package]
        
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)            
            for dep in self.adjacency_list.get(current, []):
                dep_name = self._get_dependency_name(dep)
                if dep_name not in visited:
                    stack.append(dep_name)
        
        # Remove the starting package from the result
        visited.discard(package)
        return visited
