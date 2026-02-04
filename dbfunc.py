# dbfunc.py
import mysql.connector
import sys
from config import conn  # this is now a DICTIONARY
print("DEBUG conn type:", type(conn))
def getConnection():
    """
    Establish a connection to MySQL database
    Returns a connection object or None if failed
    """
    try:
        connection = mysql.connector.connect(**conn)
        return connection
    except mysql.connector.Error as e:
        print(f"Error connecting to DB: {e}", file=sys.stderr)
        return None
