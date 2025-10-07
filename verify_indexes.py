#!/usr/bin/env python
"""
Verification script to check if database indexes were created successfully.
Run this after applying migration 0016_additional_performance_indexes.

Usage:
    python verify_indexes.py
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'waterlab.settings')
django.setup()

from django.db import connection
from django.conf import settings


def verify_indexes():
    """Verify that all expected indexes exist in the database."""

    print("=" * 70)
    print("DATABASE INDEX VERIFICATION")
    print("=" * 70)
    print(f"\nDatabase: {settings.DATABASES['default']['ENGINE']}")
    print(f"Name: {settings.DATABASES['default'].get('NAME', 'N/A')}")
    print()

    # Expected indexes by model
    expected_indexes = {
        'core_customuser': [
            'customuser_role_idx',
        ],
        'core_sample': [
            'sample_status_idx',
            'sample_collected_at_idx',
            'sample_received_lab_idx',
            'sample_status_received_idx',
        ],
        'core_testresult': [
            'testresult_date_idx',
            'testresult_tech_idx',
            'testresult_date_tech_idx',
        ],
        'core_consultantreview': [
            'review_status_idx',
            'review_date_idx',
            'review_status_date_idx',
            'review_reviewer_date_idx',
        ],
    }

    with connection.cursor() as cursor:
        db_engine = settings.DATABASES['default']['ENGINE']

        if 'postgresql' in db_engine:
            verify_postgresql_indexes(cursor, expected_indexes)
        elif 'sqlite' in db_engine:
            verify_sqlite_indexes(cursor, expected_indexes)
        else:
            print(f"⚠️  Unsupported database engine: {db_engine}")
            print("Manual verification required.")


def verify_postgresql_indexes(cursor, expected_indexes):
    """Verify indexes in PostgreSQL."""
    print("Checking PostgreSQL indexes...\n")

    # Query to get all indexes
    query = """
        SELECT
            tablename,
            indexname,
            indexdef
        FROM pg_indexes
        WHERE schemaname = 'public'
        AND tablename IN (%s)
        ORDER BY tablename, indexname;
    """

    table_names = "'" + "','".join(expected_indexes.keys()) + "'"
    cursor.execute(query.replace('%s', table_names))

    actual_indexes = {}
    for row in cursor.fetchall():
        table_name, index_name, index_def = row
        if table_name not in actual_indexes:
            actual_indexes[table_name] = []
        actual_indexes[table_name].append((index_name, index_def))

    # Verify each table
    all_found = True
    for table_name, expected_index_names in expected_indexes.items():
        print(f"📊 Table: {table_name}")
        print("-" * 70)

        table_indexes = actual_indexes.get(table_name, [])
        table_index_names = [idx[0] for idx in table_indexes]

        for expected_index in expected_index_names:
            if expected_index in table_index_names:
                # Find the definition
                idx_def = next((d for n, d in table_indexes if n == expected_index), "")
                print(f"  ✓ {expected_index}")
                print(f"    {idx_def[:80]}...")
            else:
                print(f"  ✗ {expected_index} - MISSING")
                all_found = False

        print()

    if all_found:
        print("✅ All expected indexes found!")
    else:
        print("❌ Some indexes are missing. Please run: python manage.py migrate")

    # Show index sizes
    print("\n" + "=" * 70)
    print("INDEX SIZES")
    print("=" * 70)

    size_query = """
        SELECT
            tablename,
            indexname,
            pg_size_pretty(pg_relation_size(indexrelid)) as size
        FROM pg_stat_user_indexes
        WHERE schemaname = 'public'
        AND tablename IN (%s)
        ORDER BY pg_relation_size(indexrelid) DESC;
    """

    cursor.execute(size_query.replace('%s', table_names))
    print(f"\n{'Table':<30} {'Index':<35} {'Size':<10}")
    print("-" * 70)
    for row in cursor.fetchall():
        print(f"{row[0]:<30} {row[1]:<35} {row[2]:<10}")


def verify_sqlite_indexes(cursor, expected_indexes):
    """Verify indexes in SQLite."""
    print("Checking SQLite indexes...\n")

    all_found = True
    for table_name, expected_index_names in expected_indexes.items():
        print(f"📊 Table: {table_name}")
        print("-" * 70)

        # Get indexes for this table
        cursor.execute(f"SELECT name, sql FROM sqlite_master WHERE type='index' AND tbl_name='{table_name}';")
        actual_indexes = cursor.fetchall()
        actual_index_names = [idx[0] for idx in actual_indexes]

        for expected_index in expected_index_names:
            if expected_index in actual_index_names:
                idx_sql = next((sql for name, sql in actual_indexes if name == expected_index), "")
                print(f"  ✓ {expected_index}")
                if idx_sql:
                    print(f"    {idx_sql[:80]}...")
            else:
                print(f"  ✗ {expected_index} - MISSING")
                all_found = False

        print()

    if all_found:
        print("✅ All expected indexes found!")
    else:
        print("❌ Some indexes are missing. Please run: python manage.py migrate")


def show_migration_status():
    """Show current migration status."""
    from django.db.migrations.executor import MigrationExecutor

    print("\n" + "=" * 70)
    print("MIGRATION STATUS")
    print("=" * 70 + "\n")

    executor = MigrationExecutor(connection)
    targets = executor.loader.graph.leaf_nodes()

    # Get applied migrations for core app
    applied = executor.loader.applied_migrations
    core_migrations = sorted([m for m in applied if m[0] == 'core'], key=lambda x: x[1])

    print("Last 5 applied core migrations:")
    for migration in core_migrations[-5:]:
        print(f"  ✓ {migration[1]}")

    # Check if our migration is applied
    target_migration = ('core', '0016_additional_performance_indexes')
    if target_migration in applied:
        print(f"\n✅ Migration 0016_additional_performance_indexes is applied")
    else:
        print(f"\n⚠️  Migration 0016_additional_performance_indexes is NOT applied")
        print("   Run: python manage.py migrate")


if __name__ == '__main__':
    try:
        show_migration_status()
        print()
        verify_indexes()
        print("\n" + "=" * 70)
        print("VERIFICATION COMPLETE")
        print("=" * 70)
    except Exception as e:
        print(f"\n❌ Error during verification: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
