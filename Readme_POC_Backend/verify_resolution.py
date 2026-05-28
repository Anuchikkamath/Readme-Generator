
import sys
import os
sys.path.append(os.getcwd())

from app.services.project_resolver import ProjectResolver
from app.services.storage.postgres_client import PostgresClient
from schema_manager import SchemaManager

def test_resolution():
    print("--- Starting Resolution Logic Verification ---")
    
    # 1. Setup
    sm = SchemaManager()
    sm.ensure_metadata_table_exists()
    pc = PostgresClient()
    resolver = ProjectResolver()
    
    # Clean up any previous test project
    conn = sm._get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM projects_metadata WHERE canonical_name = 'Test Project'")
    conn.commit()
    
    # 2. Register a test project with participants
    print("\n1. Registering 'Test Project' with participants [user1@example.com, user2@example.com]")
    cursor.execute("""
        INSERT INTO projects_metadata (canonical_name, normalized_name, participants)
        VALUES (%s, %s, %s)
    """, ('Test Project', 'test_project', ['user1@example.com', 'user2@example.com']))
    conn.commit()
    
    # 3. Test generic subject "Notes: Demo" with matching participants
    print("\n2. Testing 'Notes: Demo' with matching participants...")
    p1 = ['user1@example.com', 'user2@example.com', 'extra@example.com']
    res1 = resolver.resolve_canonical_project("Notes: Demo", participants=p1)
    print(f"   Result for 'Notes: Demo' (overlap 2/3): {res1}")
    
    # 4. Test strict Notes: requirement
    print("\n3. Testing strict 'Notes:' requirement...")
    res2 = resolver._extract_base_from_subject("Meeting about project")
    print(f"   Result for 'Meeting about project': {res2}")
    
    res3 = resolver._extract_base_from_subject("Notes: Project Alpha")
    print(f"   Result for 'Notes: Project Alpha': {res3}")
    
    # 5. Clean up
    # cursor.execute("DELETE FROM projects_metadata WHERE canonical_name = 'Test Project'")
    # conn.commit()
    cursor.close()
    conn.close()
    
    print("\n--- Verification Complete ---")

if __name__ == "__main__":
    test_resolution()
