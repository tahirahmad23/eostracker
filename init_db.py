#!/usr/bin/env python3
"""
Database initialization script.

Run this to set up the database from scratch:
1. Check connection
2. Run migrations
3. Seed data (optional)
"""

import sys
from database import init_db, check_connection, seed_devices


def main():
    """Initialize database with all tables and seed data."""
    print("=" * 60)
    print("EOS Tracker - Database Initialization")
    print("=" * 60)
    print()
    
    # Step 1: Check connection
    print("Step 1: Checking database connection...")
    result = check_connection()
    if not result["success"]:
        print(f"❌ Connection failed: {result['error']}")
        print("\nMake sure:")
        print("  1. PostgreSQL is running")
        print("  2. DATABASE_URL environment variable is set")
        print("  3. Database credentials are correct")
        sys.exit(1)
    
    print(f"✅ Connected to: {result['data']['url']}")
    print()
    
    # Step 2: Create tables
    print("Step 2: Creating database tables...")
    result = init_db()
    if not result["success"]:
        print(f"❌ Failed to create tables: {result['error']}")
        sys.exit(1)
    
    print(f"✅ {result['data']}")
    print()
    
    # Step 3: Seed data
    print("Step 3: Seeding device catalog...")
    seed_choice = input("Seed with ~100 network devices? (y/n): ").lower()
    
    if seed_choice == 'y':
        result = seed_devices()
        if not result["success"]:
            print(f"❌ Seeding failed: {result['error']}")
            sys.exit(1)
        
        print(f"✅ Created {result['data']} devices")
    else:
        print("⏭️  Skipped seeding")
    
    print()
    print("=" * 60)
    print("✅ Database initialization complete!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("  1. Run tests: pytest tests/test_database.py -v")
    print("  2. Start building Module 2: Authentication Service")
    print()


if __name__ == "__main__":
    main()
