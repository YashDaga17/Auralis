"""
Database configuration and connection management for Auralis.
Supports PostgreSQL (via Supabase) and Neo4j for multi-tenant architecture.
"""
import os
from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

# PostgreSQL Configuration (Supabase)
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("[WARNING] DATABASE_URL not set. PostgreSQL features will be disabled.")
    DATABASE_URL = "postgresql+psycopg://localhost/dummy"  # Dummy URL to prevent crashes

# Convert postgresql:// to postgresql+psycopg:// for psycopg3 driver
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)

# Create SQLAlchemy engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,  # Verify connections before using
    pool_recycle=3600,   # Recycle connections after 1 hour
    echo=False           # Set to True for SQL query logging
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for ORM models
Base = declarative_base()

# Neo4j Configuration
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

neo4j_driver = None
if NEO4J_URI and NEO4J_PASSWORD:
    neo4j_driver = GraphDatabase.driver(
        NEO4J_URI,
        auth=(NEO4J_USER, NEO4J_PASSWORD),
        max_connection_pool_size=50,
        connection_timeout=5.0
    )

# Dependency for FastAPI routes
def get_db():
    """Dependency that provides a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_neo4j_session():
    """Dependency that provides a Neo4j session."""
    if not neo4j_driver:
        raise RuntimeError("Neo4j driver not initialized. Check NEO4J_URI and NEO4J_PASSWORD.")
    with neo4j_driver.session() as session:
        yield session

# Health check functions
def check_postgres_health() -> bool:
    """Check if PostgreSQL connection is healthy."""
    try:
        with engine.connect() as conn:
            from sqlalchemy import text
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"PostgreSQL health check failed: {e}")
        return False

def check_neo4j_health() -> bool:
    """Check if Neo4j connection is healthy."""
    if not neo4j_driver:
        return False
    try:
        with neo4j_driver.session() as session:
            session.run("RETURN 1")
        return True
    except Exception as e:
        print(f"Neo4j health check failed: {e}")
        return False

# Cleanup on shutdown
def close_connections():
    """Close all database connections."""
    engine.dispose()
    if neo4j_driver:
        neo4j_driver.close()
