import re
import mysql.connector
from db import connect_mysql

# Define the Node structure for the AST
class Node:
    def __init__(self, node_type, value=None, left=None, right=None):
        self.type = node_type  # 'operator' or 'operand'
        self.value = value  # Could be condition for operands or AND/OR for operators
        self.left = left  # Left child (another Node)
        self.right = right  # Right child (another Node)

    def __repr__(self):
        return f"Node(type={self.type}, value={self.value})"


# Connect to the database
connection = connect_mysql()


# Helper function to store rules into the database
def store_rule(rule):
    """Stores a rule string in the rules table and returns the rule ID."""
    if not connection:
        return None

    try:
        cursor = connection.cursor()
        
        # Insert rule into the rules table
        insert_rule_query = "INSERT INTO rules (rule) VALUES (%s)"
        cursor.execute(insert_rule_query, (rule,))
        connection.commit()

        rule_id = cursor.lastrowid  # Get the last inserted rule ID

        cursor.close()
        return rule_id

    except mysql.connector.Error as err:
        print(f"Database Error: {err}")
        return None
    
    finally:
        if cursor:
            cursor.close()


# Function to store AST nodes in the database with enhanced error handling
def store_ast_nodes(rule_id, node):
    """Recursively stores AST nodes in the database and links left and right children."""
    if not node:
        return None

    connection = connect_mysql()
    if not connection:
        return None

    try:
        cursor = connection.cursor()

        # Insert the AST node
        insert_node_query = """
            INSERT INTO ast_nodes (rule_id, node_type, value) 
            VALUES (%s, %s, %s)
        """
        cursor.execute(insert_node_query, (rule_id, node.type, node.value))
        connection.commit()

        node_id = cursor.lastrowid  # Get the ID of the inserted node

        # Recursively store left child and update the left_child field
        if node.left:
            left_id = store_ast_nodes(rule_id, node.left)
            update_query = "UPDATE ast_nodes SET left_child = %s WHERE id = %s"
            cursor.execute(update_query, (left_id, node_id))
            connection.commit()

        # Recursively store right child and update the right_child field
        if node.right:
            right_id = store_ast_nodes(rule_id, node.right)
            update_query = "UPDATE ast_nodes SET right_child = %s WHERE id = %s"
            cursor.execute(update_query, (right_id, node_id))
            connection.commit()

        return node_id

    except mysql.connector.Error as err:
        print(f"Database Error: Failed to store AST node - {err}")
        return None

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


# Error classes for specific rule parsing and validation errors
class RuleParseError(Exception):
    """Custom exception for rule parsing errors."""
    pass


class DataFormatError(Exception):
    """Custom exception for data format errors."""
    pass


class InvalidAttributeError(Exception):
    """Custom exception for invalid attributes in rule creation."""
    pass


# Attribute catalog with expected types
ATTRIBUTE_CATALOG = {
    "age": int,
    "department": str,
    "salary": int,
    "experience": int
}


def validate_attribute(attribute, value):
    """Validate if the attribute exists in the catalog and check its type."""
    if attribute not in ATTRIBUTE_CATALOG:
        raise InvalidAttributeError(
            f"Invalid attribute '{attribute}'. Allowed attributes: {list(ATTRIBUTE_CATALOG.keys())}"
        )

    expected_type = ATTRIBUTE_CATALOG[attribute]
    if not isinstance(value, expected_type):
        raise InvalidAttributeError(
            f"Attribute '{attribute}' should be of type {expected_type.__name__}, but got {type(value).__name__}."
        )
    
    return True  # Return True if validation passes


# Improved rule parsing function with stricter structure checks
def create_rule(rule):
    # Check for unbalanced parentheses
    if rule.count("(") != rule.count(")"):
        raise RuleParseError("Unbalanced parentheses in rule string.")

    # Split the rule string into tokens using regex
    tokens = re.findall(r"\(|\)|\bAND\b|\bOR\b|<=|>=|!=|[=<>]|'[^']*'|[a-zA-Z_]+|\d+", rule)
    tokens = [t.strip() for t in tokens if t.strip()]

    if not tokens:
        raise RuleParseError("Empty rule string or invalid format.")
    
    if not rule:
        raise RuleParseError("Rule string cannot be empty.")


    def parse(tokens):
        """Parse tokens recursively to build the AST"""
        stack = []
        current_operator = None
        expect_operand = True  # We expect an operand first

        while tokens:
            token = tokens.pop(0)

            if token == "(":
                # Recursively parse nested expression
                node = parse(tokens)
                if stack and current_operator:
                    # Combine the last expression with the new one using the current operator
                    operator_node = Node(node_type="operator", value=current_operator)
                    operator_node.left = stack.pop()
                    operator_node.right = node
                    stack.append(operator_node)
                    current_operator = None  # Reset operator after use
                else:
                    stack.append(node)
                expect_operand = False  # After operand, expect operator
            elif token == ")":
                break  # End of current nested expression
            elif token in {"AND", "OR"}:
                if expect_operand:
                    raise RuleParseError(f"Unexpected operator '{token}' without preceding operand.")
                current_operator = token  # Set the operator for the next expression
                expect_operand = True  # After operator, expect operand
            else:
                # Handle operand (attribute, operator, value)
                if token in ATTRIBUTE_CATALOG:
                    attribute = token
                    operator = tokens.pop(0)
                    value = tokens.pop(0)

                    # Handle strings enclosed in single quotes
                    if value.startswith("'") and value.endswith("'"):
                        value = value.strip("'")

                    # Create operand node
                    operand_node = Node(node_type="operand", value=f"{attribute} {operator} {value}")
                    
                    if current_operator and stack:
                        # Combine with previous node using operator
                        operator_node = Node(node_type="operator", value=current_operator)
                        operator_node.left = stack.pop()
                        operator_node.right = operand_node
                        stack.append(operator_node)
                        current_operator = None  # Reset operator
                    else:
                        stack.append(operand_node)

                    expect_operand = False  # After operand, expect operator

        # At the end, check if there are too many or too few nodes in the stack
        if len(stack) != 1:
            raise RuleParseError("Invalid rule structure: incomplete expression or missing operators.")

        return stack[0]  # Return the root of the AST


        # Try to parse the tokens and handle any parsing errors
    try:
        return parse(tokens)
    except RuleParseError as e:
        print(f"Error parsing rule: {e}")
        return None


# Function to update the operator in the AST
def update_operator(node, new_operator):
    if node and node.type == "operator":
        node.value = new_operator
    else:
        raise RuleParseError("Cannot update operator. The node is not an operator.")


# Function to update an operand value in the AST
def update_operand(node, new_value):
    if node and node.type == "operand":
        try:
            # Validate new attribute if it's part of the condition
            attribute = re.split(r"([<>=]+)", new_value)[0].strip()
            validate_attribute(attribute)
            node.value = new_value
        except InvalidAttributeError as e:
            print(f"Attribute Validation Error: {e}")
    else:
        raise RuleParseError("Cannot update operand. The node is not an operand.")


# Function to add a sub-expression (as an operand) to the AST
def add_sub_expression(root_node, new_sub_expression, operator="AND"):
    # Create a new operator node combining the root node and the new sub-expression
    new_operator_node = Node(node_type="operator", value=operator)
    new_operator_node.left = root_node
    new_operator_node.right = create_rule(new_sub_expression)
    return new_operator_node


# Function to remove a sub-expression (remove a node) from the AST
def remove_sub_expression(root_node, sub_expression_value):
    if not root_node:
        return None
    
    # Recursively traverse the AST and remove the node with the matching sub-expression
    if root_node.type == "operand" and root_node.value == sub_expression_value:
        return None  # Remove this node

    if root_node.left:
        root_node.left = remove_sub_expression(root_node.left, sub_expression_value)
    if root_node.right:
        root_node.right = remove_sub_expression(root_node.right, sub_expression_value)
    
    return root_node


def combine_rules(rules, operator="AND"):
    """Combine multiple ASTs into a single AST using the provided operator"""
    if not rules:
        return None

    combined_ast = rules[0]

    for rule_ast in rules[1:]:
        combined_ast = Node(node_type="operator", value=operator, left=combined_ast, right=rule_ast)

    return combined_ast
def parse_conditions(condition_string):
    """Parse a condition string into a list of (attribute, operator, value) tuples."""
    # Enhanced regex pattern to match operators >=, <=, >, <, =, and !=
    pattern = r'(\s*[<>=!]+)\s*'
    
    # Split the conditions using the regex pattern while preserving the delimiters
    tokens = re.split(pattern, condition_string)
    
    # Remove empty tokens and strip whitespace
    tokens = [token.strip() for token in tokens if token.strip()]

    # Combine tokens into condition tuples (attribute, operator, value)
    conditions = []
    for i in range(0, len(tokens), 2):
        if i + 2 < len(tokens):  # Ensure there is an attribute, operator, and value
            attribute = tokens[i]
            operator = tokens[i + 1]
            value = tokens[i + 2]
            conditions.append((attribute, operator, value))

    return conditions


def evaluate_rule(ast, attributes):
    """Evaluate the AST against provided attributes."""
    if not ast:
        return False

    if ast.type == "operand":
        # Assuming ast.value is in the format "attribute operator value"
        condition = ast.value
        conditions = parse_conditions(condition)

        if not conditions:
            return False
        
        # Extract the first condition for evaluation
        attribute, operator, value = conditions[0]

        # Check if the attribute exists in the provided attributes
        if attribute not in attributes:
            raise InvalidAttributeError(f"Attribute '{attribute}' not found in provided attributes.")

        # Get the actual value from the attributes
        actual_value = attributes[attribute]

        # Check the expected type of the attribute
        expected_type = ATTRIBUTE_CATALOG.get(attribute)

        # Cast the value to the expected type for comparison
        if expected_type == int:
            value = int(value)
        elif expected_type == str:
            value = str(value)

        # Perform the evaluation based on the operator
        if operator == "=":
            return actual_value == value
        elif operator == "!=":
            return actual_value != value
        elif operator == ">":
            return actual_value > value
        elif operator == "<":
            return actual_value < value
        elif operator == ">=":
            return actual_value >= value
        elif operator == "<=":
            return actual_value <= value
        else:
            raise RuleParseError(f"Unknown operator '{operator}' in condition.")

    elif ast.type == "operator":
        # Evaluate left and right subtrees based on the operator
        left_result = evaluate_rule(ast.left, attributes)
        right_result = evaluate_rule(ast.right, attributes)

        if ast.value == "AND":
            return left_result and right_result
        elif ast.value == "OR":
            return left_result or right_result

    return False  # Default case, return False
