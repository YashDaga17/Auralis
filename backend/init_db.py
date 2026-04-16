"""
Database initialization script.
Creates all tables and sets up initial schema.
"""
from database import engine, Base, check_postgres_health, check_neo4j_health
from models import Company, Agent, WorkflowVersion, ConversationHistory, UserPreference, ExecutionMetric
import sys


def init_database():
    """Initialize PostgreSQL database with all tables."""
    print("[INFO] Initializing PostgreSQL database...")
    
    # Check connection health
    if not check_postgres_health():
        print("[ERROR] PostgreSQL connection failed. Check DATABASE_URL.")
        sys.exit(1)
    
    # Create all tables
    try:
        Base.metadata.create_all(bind=engine)
        print("[SUCCESS] PostgreSQL tables created successfully")
        
        # List created tables
        tables = Base.metadata.tables.keys()
        print(f"[INFO] Created tables: {', '.join(tables)}")
        
    except Exception as e:
        print(f"[ERROR] Failed to create tables: {e}")
        sys.exit(1)


def check_neo4j():
    """Check Neo4j connection (optional)."""
    print("\n[INFO] Checking Neo4j connection...")
    
    if check_neo4j_health():
        print("[SUCCESS] Neo4j connection successful")
    else:
        print("[WARNING] Neo4j not configured or connection failed")
        print("[INFO] Set NEO4J_URI and NEO4J_PASSWORD to enable GraphRAG features")


if __name__ == "__main__":
    init_database()
    check_neo4j()
    print("\n[SUCCESS] Database initialization complete!")
