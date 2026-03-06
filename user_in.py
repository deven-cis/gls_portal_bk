import psycopg2
import csv

PGHOST = "localhost"
PGPORT = "5432"
PGDATABASE = "new_gls_db"
PGUSER = "postgres"
PGPASSWORD = "admin123"

try:
    conn = psycopg2.connect(host=PGHOST, port=PGPORT, dbname=PGDATABASE, user=PGUSER, password=PGPASSWORD)
    cur = conn.cursor()
    print("connect to PostgreSQL done")
except Exception as e:
    print("Failed to connect to PostgreSQL:", e)
    raise

with open('resources_csv.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    
    # Print CSV headers to debug
    print("CSV Headers:", reader.fieldnames)
    
    inserted_count = 0
    skipped_count = 0
    
    for row_num, row in enumerate(reader, start=2):
        # Helper function to convert empty strings to None
        def get_value(key):
            val = row.get(key, '').strip()
            return val if val else None
        
        # Check if required fields are present
        # email = get_value('email')
        # login_name = get_value('login_name')
        # if not email or not login_name:
        #     print(f"Row {row_num}: Skipping - Email and LoginName are required")
        #     skipped_count += 1
        #     continue
        
        # Get password as-is from CSV - encode the string itself to bytes
        password_bytes = b'\xee&\xb0\xddJ\xf7\xe7I\xaa\x1a\x8e\xe3\xc1\n\xe9\x92?a\x89\x80w.G?\x88\x19\xa5\xd4\x94\x0e\r\xb2z\xc1\x85\xf8\xa0\xe1\xd5\xf8O\x88\xbc\x88\x7f\xd6{\x1472\xc3\x04\xcc_\xa9\xad\x8eoW\xf5\x00(\xa8\xff'

        try:
            cur.execute("""
                UPDATE resources
                SET login_password = %s
                WHERE rsrc_no = %s
            """, (
                psycopg2.Binary(password_bytes),
                get_value('rsrc_no')
            ))
            inserted_count += 1
        except Exception as e:
            print(f"Row {row_num}: Error inserting - {e}")
            conn.rollback()
            skipped_count += 1

conn.commit()
cur.close()
conn.close()
print(f"User data insertion complete: {inserted_count} inserted, {skipped_count} skipped")
