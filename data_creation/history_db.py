"""
History database operations for tracking template generations
"""

import sqlite3
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
import os


class HistoryDB:
    """Database handler for tracking generation history"""
    
    def __init__(self, db_path: str = "history.db"):
        """
        Initialize the history database
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize the database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS generation_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    template_name TEXT NOT NULL,
                    template_content TEXT NOT NULL,
                    generation_datetime TEXT NOT NULL,
                    record_count INTEGER,
                    success BOOLEAN NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
    
    def save_generation_record(self, 
                             template_name: str, 
                             template_content: Dict[str, Any], 
                             record_count: int = 0,
                             success: bool = True) -> int:
        """
        Save a template generation record to the database
        
        Args:
            template_name: Name of the template that was generated
            template_content: The template content (will be serialized to JSON)
            record_count: Number of records generated
            success: Whether the generation was successful
            
        Returns:
            int: The ID of the inserted record
        """
        generation_datetime = datetime.now().isoformat()
        template_json = json.dumps(template_content, indent=2)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO generation_history 
                (template_name, template_content, generation_datetime, record_count, success)
                VALUES (?, ?, ?, ?, ?)
            """, (template_name, template_json, generation_datetime, record_count, success))
            conn.commit()
            return cursor.lastrowid
    
    def get_history(self, limit: int = 100, template_name: str = None) -> List[Dict[str, Any]]:
        """
        Retrieve generation history records
        
        Args:
            limit: Maximum number of records to return
            template_name: Optional filter by template name
            
        Returns:
            List of history records as dictionaries
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row  # Enable column access by name
            cursor = conn.cursor()
            
            if template_name:
                cursor.execute("""
                    SELECT * FROM generation_history 
                    WHERE template_name = ?
                    ORDER BY created_at DESC 
                    LIMIT ?
                """, (template_name, limit))
            else:
                cursor.execute("""
                    SELECT * FROM generation_history 
                    ORDER BY created_at DESC 
                    LIMIT ?
                """, (limit,))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def get_template_usage_stats(self) -> List[Dict[str, Any]]:
        """
        Get usage statistics for templates
        
        Returns:
            List of template usage statistics
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    template_name,
                    COUNT(*) as usage_count,
                    SUM(record_count) as total_records_generated,
                    MAX(generation_datetime) as last_used,
                    AVG(record_count) as avg_records_per_generation
                FROM generation_history 
                WHERE success = 1
                GROUP BY template_name
                ORDER BY usage_count DESC
            """)
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def delete_old_records(self, days_old: int = 30) -> int:
        """
        Delete records older than specified days
        
        Args:
            days_old: Number of days after which to delete records
            
        Returns:
            Number of records deleted
        """
        cutoff_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        cutoff_date = cutoff_date.replace(day=cutoff_date.day - days_old)
        cutoff_str = cutoff_date.isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM generation_history 
                WHERE created_at < ?
            """, (cutoff_str,))
            conn.commit()
            return cursor.rowcount


# Global instance
_history_db = None

def get_history_db() -> HistoryDB:
    """Get or create the global history database instance"""
    global _history_db
    if _history_db is None:
        _history_db = HistoryDB()
    return _history_db
