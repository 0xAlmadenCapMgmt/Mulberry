"""Initialize cache database"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mulberry.cache.models import create_cache_db
from mulberry.utils.config import config

def main():
    """Create cache database with all tables"""
    print(f"Initializing cache database at: {config.cache_db_path}")

    try:
        engine = create_cache_db(str(config.cache_db_path))
        print("✓ Cache database created successfully")
        print(f"  Tables: quotes_cache, fundamentals_cache, filings_cache")
        return 0

    except Exception as e:
        print(f"✗ Failed to create cache database: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
