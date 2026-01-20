import sqlite3
import json
import hashlib
import os
from functools import wraps
from typing import Any, Optional

DB_PATH = "cache.db"

class CacheManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CacheManager, cls).__new__(cls)
            cls._instance.init_db()
        return cls._instance
    
    def init_db(self):
        """Initialize the SQLite database for caching."""
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
    
    def _generate_key(self, func_name: str, args_dict: dict) -> str:
        """Generate a unique key based on function name and arguments."""
        # Sort keys to ensure consistent ordering
        serialized_args = json.dumps(args_dict, sort_keys=True)
        combined = f"{func_name}:{serialized_args}"
        return hashlib.sha256(combined.encode()).hexdigest()
    
    def get(self, func_name: str, args_dict: dict) -> Optional[Any]:
        """Retrieve a value from the cache."""
        key = self._generate_key(func_name, args_dict)
        data = None
        
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT value FROM cache WHERE key = ?", (key,))
                row = cursor.fetchone()
                if row:
                    data = json.loads(row[0])
        except Exception as e:
            print(f"Cache get error: {e}")
            
        return data

    def set(self, func_name: str, args_dict: dict, value: Any):
        """Save a value to the cache."""
        key = self._generate_key(func_name, args_dict)
        try:
            serialized_value = json.dumps(value)
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT OR REPLACE INTO cache (key, value) VALUES (?, ?)", 
                    (key, serialized_value)
                )
                conn.commit()
        except Exception as e:
            print(f"Cache set error: {e}")

# Decorator for easy usage
def cached(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Create a dictionary of all arguments
        # simplified for now: just using args and kwargs
        # Ideally we should bind to signature but for our use case this might be enough
        # assuming simple args
        
        args_dict = {
            "args": args,
            "kwargs": kwargs
        }
        
        manager = CacheManager()
        cached_result = manager.get(func.__name__, args_dict)
        
        if cached_result is not None:
            print(f"[CACHE HIT] {func.__name__}")
            return cached_result
            
        print(f"[CACHE MISS] {func.__name__}")
        result = func(*args, **kwargs)
        manager.set(func.__name__, args_dict, result)
        return result
    return wrapper
