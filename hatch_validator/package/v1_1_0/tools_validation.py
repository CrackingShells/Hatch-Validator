import ast
import logging
from typing import Dict, List, Tuple

from hatch_validator.core.validation_strategy import ToolsValidationStrategy
from hatch_validator.core.validation_context import ValidationContext
from hatch_validator.package.package_service import PackageService

logger = logging.getLogger("hatch_validator.schemas.v1_1_0.tools_validation")
logger.setLevel(logging.INFO)

class ToolsValidation(ToolsValidationStrategy):
    """Strategy for validating tool declarations for v1.1.0."""
    
    def validate_tools(self, metadata: Dict, context: ValidationContext) -> Tuple[bool, List[str]]:
        """Validate tools according to v1.1.0 schema.
        
        Args:
            metadata (Dict): Package metadata containing tool declarations
            context (ValidationContext): Validation context with resources
            
        Returns:
            Tuple[bool, List[str]]: Tuple containing:
                - bool: Whether tool validation was successful
                - List[str]: List of tool validation errors
        """
        package_service = context.get_data("package_service", None)
        if package_service is None:
            package_service = PackageService(metadata)
        tools = package_service.get_tools()
        if not tools:
            return True, []
        entry_point = package_service.get_entry_point()
        if not entry_point:
            return False, ["Entry point required for tool validation"]
        
        if not context.package_dir:
            return False, ["Package directory not provided for tool validation"]
        
        errors = []
        all_exist = True
        
        # Parse the entry point file to get function names
        try:
            module_path = context.package_dir / entry_point
            with open(module_path, 'r', encoding='utf-8') as file:
                try:
                    tree = ast.parse(file.read(), filename=str(module_path))
                    
                    # Get all function names defined in the file
                    function_names = [node.name for node in ast.walk(tree) 
                                    if isinstance(node, ast.FunctionDef)]
                    
                    logger.debug(f"Found functions in {entry_point}: {function_names}")
                    
                    # Check for each tool
                    for tool in tools:
                        tool_name = tool.get('name')
                        if not tool_name:
                            logger.error(f"Tool metadata missing name: {tool}")
                            errors.append("Tool missing name in metadata")
                            all_exist = False
                            continue
                        
                        # Check if the tool function is defined in the file
                        if tool_name not in function_names:
                            logger.error(f"Tool '{tool_name}' not found in entry point")
                            errors.append(f"Tool '{tool_name}' not found in entry point")
                            all_exist = False
                    
                except SyntaxError as e:
                    logger.error(f"Syntax error in {entry_point}: {e}")
                    return False, [f"Syntax error in {entry_point}: {e}"]
                    
        except Exception as e:
            logger.error(f"Error validating tools: {str(e)}")
            return False, [f"Error validating tools: {str(e)}"]
            
        return all_exist, errors