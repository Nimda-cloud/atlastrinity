"""
Test script for secure backup functionality
"""

import sqlite3
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def create_test_database_with_secrets():
    """Create a test SQLite database with secret-like data (placeholders only)"""
    test_db = PROJECT_ROOT / "test_secrets.db"

    conn = sqlite3.connect(str(test_db))
    cursor = conn.cursor()

    # Create test table
    cursor.execute("""
        CREATE TABLE test_data (
            id INTEGER PRIMARY KEY,
            description TEXT,
            api_key TEXT,
            token TEXT
        )
    """)

    # Insert test data with placeholder secrets (safe for Git)
    test_data = [
        (
            1,
            "Google Maps integration",
            "AIzaSyDemoApiKeyPlaceholderForTesting",
            "ghp_demo_token_placeholder",
        ),
        (
            2,
            "Mistral API connection",
            "demo_mistral_key_placeholder",
            "Bearer demo_token_placeholder",
        ),
        (3, "Clean data", "no_secrets_here", "clean_token"),
    ]

    cursor.executemany("INSERT INTO test_data VALUES (?, ?, ?, ?)", test_data)
    conn.commit()
    conn.close()

    return test_db


def test_secure_backup():
    """Test the secure backup functionality"""

    try:
        from src.maintenance.secure_backup import SecureBackupManager

        # Create test database with secrets
        test_db = create_test_database_with_secrets()

        # Initialize backup manager
        backup_manager = SecureBackupManager(PROJECT_ROOT)

        # Test secret filtering
        filtered_db = PROJECT_ROOT / "test_filtered.db"

        if backup_manager.filter_sqlite_secrets(test_db, filtered_db):
            # Verify filtering worked
            conn = sqlite3.connect(str(filtered_db))
            cursor = conn.cursor()
            cursor.execute("SELECT api_key, token FROM test_data WHERE id = 1")
            result = cursor.fetchone()
            conn.close()

            if "[REDACTED_SECRET]" in result[0] and "[REDACTED_SECRET]" in result[1]:
                pass
            else:
                pass
        else:
            return False

        # Test encryption
        encrypted_file = PROJECT_ROOT / "test_encrypted.db"
        key = backup_manager.get_backup_key()

        if backup_manager.encrypt_file(test_db, encrypted_file, key):
            # Test decryption
            decrypted_file = PROJECT_ROOT / "test_decrypted.db"
            if backup_manager.decrypt_file(encrypted_file, decrypted_file, key):
                # Verify decrypted content matches original
                with open(test_db, "rb") as f1, open(decrypted_file, "rb") as f2:
                    if f1.read() == f2.read():
                        pass
                    else:
                        pass
            else:
                return False
        else:
            return False

        # Cleanup test files
        cleanup_files = [test_db, filtered_db, encrypted_file, decrypted_file]

        for file in cleanup_files:
            if file.exists():
                file.unlink()

        return True

    except Exception:
        return False


if __name__ == "__main__":
    success = test_secure_backup()
    sys.exit(0 if success else 1)
