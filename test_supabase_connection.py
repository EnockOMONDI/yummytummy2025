#!/usr/bin/env python3
"""
Supabase Database Connection Test
Tests the connection to your Supabase PostgreSQL database
"""

import os
import psycopg2
from urllib.parse import urlparse

def test_supabase_connection():
    """Test connection to Supabase database"""
    
    # Your NEW Supabase connection string
    database_url = "postgresql://postgres.nywjfwuobkbpimevbdvr:yummytummy2025@aws-0-eu-west-1.pooler.supabase.com:6543/postgres?sslmode=require&connect_timeout=10&application_name=yummytummy_django"
    
    print("🔍 Testing Supabase Database Connection...")
    print(f"📍 Host: aws-0-eu-west-1.pooler.supabase.com")
    print(f"🔌 Port: 6543")
    print(f"👤 User: postgres.nywjfwuobkbpimevbdvr")
    print(f"🗄️  Database: postgres")
    print("-" * 50)
    
    try:
        # Parse the URL
        parsed = urlparse(database_url)
        
        # Test connection
        print("⏳ Attempting to connect...")
        conn = psycopg2.connect(database_url)
        
        # Test basic query
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        
        cursor.execute("SELECT current_database();")
        db_name = cursor.fetchone()
        
        cursor.execute("SELECT current_user;")
        user = cursor.fetchone()
        
        print("✅ CONNECTION SUCCESSFUL!")
        print(f"📊 PostgreSQL Version: {version[0]}")
        print(f"🗄️  Connected Database: {db_name[0]}")
        print(f"👤 Connected User: {user[0]}")
        
        # Test if we can create/access tables
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            LIMIT 5;
        """)
        tables = cursor.fetchall()
        
        if tables:
            print(f"📋 Found {len(tables)} tables in database:")
            for table in tables:
                print(f"   - {table[0]}")
        else:
            print("📋 No tables found in public schema")
        
        cursor.close()
        conn.close()
        
        return True
        
    except psycopg2.OperationalError as e:
        print("❌ CONNECTION FAILED!")
        print(f"🚨 Error: {str(e)}")
        
        if "Tenant or user not found" in str(e):
            print("\n💡 DIAGNOSIS:")
            print("   - Your Supabase project may be paused or deleted")
            print("   - The database credentials might be incorrect")
            print("   - The project URL might have changed")
            
        elif "timeout" in str(e).lower():
            print("\n💡 DIAGNOSIS:")
            print("   - Network connectivity issues")
            print("   - Supabase service might be down")
            
        print("\n🔧 SOLUTIONS:")
        print("   1. Check your Supabase dashboard: https://supabase.com/dashboard")
        print("   2. Verify your project is active and not paused")
        print("   3. Get fresh connection credentials from Settings > Database")
        print("   4. Check if your IP is allowed (if using IP restrictions)")
        
        return False
        
    except Exception as e:
        print("❌ UNEXPECTED ERROR!")
        print(f"🚨 Error: {str(e)}")
        return False

def test_alternative_connection_methods():
    """Test alternative connection methods"""
    print("\n" + "="*50)
    print("🔄 TESTING ALTERNATIVE CONNECTION METHODS")
    print("="*50)
    
    # Test direct connection (port 5432)
    direct_url = "postgresql://postgres.nywjfwuobkbpimevbdvr:yummytummy2025@aws-0-eu-west-1.pooler.supabase.com:5432/postgres?sslmode=require"
    
    print("\n📡 Testing Direct Connection (Port 5432)...")
    try:
        conn = psycopg2.connect(direct_url)
        print("✅ Direct connection successful!")
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Direct connection failed: {str(e)}")
    
    return False

if __name__ == "__main__":
    print("🧪 SUPABASE DATABASE CONNECTION TEST")
    print("="*50)
    
    # Test main connection
    success = test_supabase_connection()
    
    if not success:
        # Test alternatives
        test_alternative_connection_methods()
    
    print("\n" + "="*50)
    if success:
        print("🎉 Your Supabase database is working correctly!")
        print("💡 You can uncomment the DATABASE_URL in your .env file")
    else:
        print("🔧 Please check your Supabase dashboard and update credentials")
        print("💡 For now, use SQLite for local development")
    print("="*50)
