import mysql.connector

# MySQL connection setup
def connect_mysql():
    try:
        connection = mysql.connector.connect(
            host="localhost", 
            user="root", 
            password="Abc@1234567890", 
            database="rule_engine" 
        )
    
        return connection
    
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return None

