import unittest
from main import (
    create_rule,
    evaluate_rule,
    Node,
    RuleParseError,
    InvalidAttributeError
)

class TestRuleEngine(unittest.TestCase):

    def setUp(self):
        # Set up any necessary resources for the tests
        self.valid_rule = "((age > 30 AND department = 'Sales') OR (salary <= 50000))"
        self.invalid_rule = "((age > 30 AND department = 'Sales' OR (salary <= 50000)"
        self.attributes = {
            "age": 35,
            "department": "Sales",
            "salary": 45000,
            "experience": 5
        }
        
        self.attributes_invalid = {
            "age": 25,
            "department": "Engineering",
            "salary": 60000,
            "experience": 2
        }

    def test_create_rule_valid(self):
        """Test creating a valid rule"""
        ast = create_rule(self.valid_rule)
        self.assertIsInstance(ast, Node, "Should return a Node instance for a valid rule")
    
    def test_create_rule_invalid(self):
        """Test creating an invalid rule"""
        with self.assertRaises(RuleParseError):
            create_rule(self.invalid_rule)

    def test_evaluate_rule_valid(self):
        """Test evaluating a valid rule against attributes"""
        ast = create_rule(self.valid_rule)
        result = evaluate_rule(ast, self.attributes)
        self.assertTrue(result, "The rule should evaluate to True for the provided attributes")

    def test_evaluate_rule_invalid(self):
        """Test evaluating a rule against invalid attributes"""
        ast = create_rule(self.valid_rule)
        result = evaluate_rule(ast, self.attributes_invalid)
        self.assertFalse(result, "The rule should evaluate to False for the provided invalid attributes")
    
    def test_invalid_attribute_error(self):
        """Test raising InvalidAttributeError for unknown attributes"""
        with self.assertRaises(InvalidAttributeError):
            attributes = {"unknown": 100}
            evaluate_rule(create_rule(self.valid_rule), attributes)

    def tearDown(self):
        # Clean up any resources after tests
        pass

if __name__ == "__main__":
    unittest.main()
