import streamlit as st
from db import connect_mysql
from main import (
    create_rule,
    store_rule,
    store_ast_nodes,
    evaluate_rule,
    Node
)

connection = connect_mysql()

def main():
    st.title("Rule Engine UI")
    
    # Store the AST in session state to persist between button clicks
    if 'ast' not in st.session_state:
        st.session_state.ast = None

    st.subheader("Input a Rule")
    rule = st.text_area("Enter your rule (e.g., ((age > 30 AND department = 'Sales') OR (salary > 50000)))")

    if st.button("Parse Rule"):
        try:
            st.session_state.ast = create_rule(rule)
            if st.session_state.ast:
                st.success("Rule parsed successfully!")
                st.write("Abstract Syntax Tree (AST):")
                st.write(st.session_state.ast)
            else:
                st.error("Failed to parse rule.")

        except Exception as e:
            st.error(f"Error: {e}")

    # Only show "Store Rule" button if the AST has been successfully parsed
    if st.session_state.ast:
        if st.button("Store Rule"):
            rule_id = store_rule(rule)
            if rule_id:
                store_ast_nodes(rule_id, st.session_state.ast)
                st.success(f"Rule stored with ID: {rule_id}")
            else:
                st.error("Failed to store the rule.")

    st.subheader("Evaluate Rule")
    st.write("Sample Data:")
    age = st.number_input("Age", min_value=0, value=30)
    department = st.text_input("Department", value="Sales")
    salary = st.number_input("Salary", min_value=0, value=50000)
    experience = st.number_input("Experience", min_value=0, value=5)

    if st.button("Evaluate"):
        sample_data = {
            "age": age,
            "department": department,
            "salary": salary,
            "experience": experience
        }
        try:
            result = evaluate_rule(st.session_state.ast, sample_data)
            st.success(f"Evaluation Result: {result}")
        except Exception as e:
            st.error(f"Evaluation Error: {e}")

if __name__ == "__main__":
    main()
