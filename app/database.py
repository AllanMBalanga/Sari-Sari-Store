import mysql.connector
from mysql.connector import Error
from mysql.connector.cursor import MySQLCursorDict
from .config import settings

conn = mysql.connector.connect(
    host=settings.database_host,
    user=settings.database_user,
    password=settings.database_password,
)

cursor = conn.cursor()
cursor.execute("CREATE DATABASE IF NOT EXISTS yagudjob")
conn.commit()

class Database:
    def __init__(self):
        try:
            self.conn = mysql.connector.connect(
                host=settings.database_host,
                user=settings.database_user,
                password=settings.database_password,
                database=settings.database_name,
                use_pure=True
            )


            self.cursor = self.conn.cursor(cursor_class=MySQLCursorDict, buffered=True)

        except Error as e:
            print(f"Database connection error: {e}")
            raise

    def create_tables(self):
        commands = (
            """
            CREATE TABLE IF NOT EXISTS customers (
                id INT AUTO_INCREMENT PRIMARY KEY,
                email VARCHAR(64) NOT NULL UNIQUE,
                password VARCHAR(120) NOT NULL,
                first_name VARCHAR(30) NOT NULL,
                last_name VARCHAR(30) NOT NULL,
                role ENUM('user', 'admin') NOT NULL,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NULL ON UPDATE CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP NULL,
                updated_by VARCHAR(30),
                deleted_by VARCHAR(30)
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS balances (
                id INT AUTO_INCREMENT PRIMARY KEY,
                customer_id INT NOT NULL,
                total DECIMAL(10, 2) NOT NULL DEFAULT 0.00,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NULL ON UPDATE CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP NULL,
                updated_by VARCHAR(30),
                deleted_by VARCHAR(30),

                FOREIGN KEY (customer_id) REFERENCES customers(id)
                ON UPDATE CASCADE ON DELETE CASCADE
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS transactions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                customer_id INT NOT NULL,
                balance_id INT NOT NULL,
                type ENUM('withdraw', 'deposit') NOT NULL,
                amount DECIMAL(10, 2) NOT NULL DEFAULT 0.00,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NULL ON UPDATE CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP NULL,
                updated_by VARCHAR(30),
                deleted_by VARCHAR(30),

                FOREIGN KEY (customer_id) REFERENCES customers(id)
                ON UPDATE CASCADE ON DELETE CASCADE,
                FOREIGN KEY (balance_id) REFERENCES balances(id)
                ON UPDATE CASCADE ON DELETE CASCADE
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS orders (
                id INT AUTO_INCREMENT PRIMARY KEY,
                customer_id INT NOT NULL,
                payment_method ENUM('cash', 'balance') NOT NULL,
                note TEXT,
                total DECIMAL(10, 2) DEFAULT 0.00,
                store_notes TEXT,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NULL ON UPDATE CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP NULL,
                updated_by VARCHAR(30),
                deleted_by VARCHAR(30),

                FOREIGN KEY (customer_id) REFERENCES customers(id)
                ON UPDATE CASCADE ON DELETE CASCADE
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS items (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(60) NOT NULL,
                quantity INT NOT NULL,
                orig_price DECIMAL(10, 2) NOT NULL,
                total_orig_price DECIMAL(10, 2) GENERATED ALWAYS AS (quantity * orig_price) STORED,
                selling_price DECIMAL(10, 2) NOT NULL,
                total_selling_price DECIMAL(10, 2) GENERATED ALWAYS AS (quantity * selling_price) STORED,
                profit DECIMAL(10, 2) GENERATED ALWAYS AS ((quantity * selling_price) - (quantity * orig_price)) STORED,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NULL ON UPDATE CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP NULL,
                updated_by VARCHAR(30),
                deleted_by VARCHAR(30)
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS order_items (
                id INT AUTO_INCREMENT PRIMARY KEY,
                order_id INT NOT NULL,
                item_id INT NOT NULL,
                quantity INT NOT NULL,
                unit_price DECIMAL(10, 2) NOT NULL,
                subtotal DECIMAL(10, 2) GENERATED ALWAYS AS (quantity * unit_price) STORED,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NULL ON UPDATE CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP NULL,
                updated_by VARCHAR(30),
                deleted_by VARCHAR(30),

                FOREIGN KEY (order_id) REFERENCES orders(id)
                ON UPDATE CASCADE ON DELETE CASCADE,
                FOREIGN KEY (item_id) REFERENCES items(id)
                ON UPDATE CASCADE ON DELETE CASCADE
            );
            """
        )
        for command in commands:
            self.cursor.execute(command)

        self.conn.commit()
        self.conn.close()

db = Database()
db.create_tables()
print("Database connected successfully")