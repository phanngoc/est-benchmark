"""
File Upload Manager

Manages file upload tracking in SQLite database.
Tracks uploaded files with metadata, hash for deduplication, and project association.
"""

import os
import sqlite3
import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from utils.logger import get_logger

logger = get_logger(__name__)


class FileUploadManager:
    """
    SQLite-based manager for file upload tracking
    
    Manages the uploaded_files table with:
    - File metadata (name, path, size, type)
    - Hash for deduplication
    - Project association
    - Upload timestamp and status
    """

    def __init__(self, db_path: str = "./estimation_tracker.db"):
        """
        Initialize FileUploadManager with SQLite database
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._init_database()
        logger.info(f"📁 File Upload Manager initialized: {db_path}")

    def _init_database(self):
        """Create uploaded_files table if it doesn't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create uploaded_files table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS uploaded_files (
                file_id TEXT PRIMARY KEY,
                project_id TEXT,
                filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                file_hash TEXT NOT NULL,
                file_type TEXT,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'active',
                FOREIGN KEY (project_id) REFERENCES projects(project_id)
            )
        """)

        # Create indexes for performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_uploaded_files_project_id
            ON uploaded_files(project_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_uploaded_files_hash
            ON uploaded_files(file_hash)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_uploaded_files_uploaded_at
            ON uploaded_files(uploaded_at)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_uploaded_files_status
            ON uploaded_files(status)
        """)

        conn.commit()
        conn.close()

        logger.debug("✅ uploaded_files table and indexes initialized")

    def save_file(
        self,
        file_id: str,
        project_id: Optional[str],
        filename: str,
        file_path: str,
        file_size: int,
        file_hash: str,
        file_type: Optional[str] = None,
        status: str = "active"
    ) -> str:
        """
        Save file metadata to database
        
        Args:
            file_id: Unique identifier for the file
            project_id: Associated project ID (optional)
            filename: Original filename
            file_path: Path where file is stored
            file_size: Size of file in bytes
            file_hash: SHA256 hash of file content
            file_type: MIME type or file extension
            status: File status (default: 'active')
            
        Returns:
            file_id of the saved file
            
        Raises:
            ValueError: If file already exists or required fields are missing
        """
        if not filename or not file_path:
            raise ValueError("Filename and file_path are required")
        
        if not file_id:
            raise ValueError("file_id is required")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO uploaded_files 
                (file_id, project_id, filename, file_path, file_size, 
                 file_hash, file_type, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                file_id,
                project_id,
                filename,
                file_path,
                file_size,
                file_hash,
                file_type,
                status
            ))
            
            conn.commit()
            logger.info(f"✅ Saved file: {file_id} - {filename} (project: {project_id})")
            
            return file_id
            
        except sqlite3.IntegrityError as e:
            logger.error(f"❌ Error saving file: {e}")
            raise ValueError(f"File with ID '{file_id}' already exists")
            
        finally:
            conn.close()

    def get_file(self, file_id: str) -> Optional[Dict[str, Any]]:
        """
        Get file metadata by file_id
        
        Args:
            file_id: ID of the file to retrieve
            
        Returns:
            Dictionary with file metadata or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT * FROM uploaded_files
                WHERE file_id = ?
            """, (file_id,))
            
            row = cursor.fetchone()
            
            if row:
                return dict(row)
            
            logger.warning(f"⚠️ File not found: {file_id}")
            return None
            
        finally:
            conn.close()

    def list_files(
        self,
        project_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List files with optional filtering
        
        Args:
            project_id: Filter by project ID
            status: Filter by status (active, deleted, etc.)
            limit: Maximum number of results (default: 100)
            offset: Number of results to skip (default: 0)
            
        Returns:
            List of file metadata dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            query = "SELECT * FROM uploaded_files WHERE 1=1"
            params = []
            
            if project_id:
                query += " AND project_id = ?"
                params.append(project_id)
            
            if status:
                query += " AND status = ?"
                params.append(status)
            
            query += " ORDER BY uploaded_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            cursor.execute(query, params)
            
            rows = cursor.fetchall()
            files = [dict(row) for row in rows]
            
            logger.info(f"📋 Listed {len(files)} files (project: {project_id}, status: {status})")
            
            return files
            
        finally:
            conn.close()

    def delete_file(self, file_id: str, soft_delete: bool = True) -> bool:
        """
        Delete a file (soft or hard delete)
        
        Args:
            file_id: ID of the file to delete
            soft_delete: If True, marks as deleted; if False, removes from database
            
        Returns:
            True if file was deleted, False if not found
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            if soft_delete:
                cursor.execute("""
                    UPDATE uploaded_files
                    SET status = 'deleted'
                    WHERE file_id = ?
                """, (file_id,))
            else:
                cursor.execute("""
                    DELETE FROM uploaded_files
                    WHERE file_id = ?
                """, (file_id,))
            
            conn.commit()
            
            if cursor.rowcount > 0:
                delete_type = "soft" if soft_delete else "hard"
                logger.info(f"🗑️ Deleted file ({delete_type}): {file_id}")
                return True
            else:
                logger.warning(f"⚠️ File not found for deletion: {file_id}")
                return False
            
        finally:
            conn.close()

    def search_files(
        self,
        filename_pattern: Optional[str] = None,
        file_hash: Optional[str] = None,
        file_type: Optional[str] = None,
        project_id: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Search files with multiple criteria
        
        Args:
            filename_pattern: Search pattern for filename (uses LIKE)
            file_hash: Exact file hash match
            file_type: Filter by file type
            project_id: Filter by project ID
            date_from: Filter files uploaded after this date (ISO format)
            date_to: Filter files uploaded before this date (ISO format)
            status: Filter by status
            limit: Maximum number of results (default: 100)
            
        Returns:
            List of matching file metadata dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            query = "SELECT * FROM uploaded_files WHERE 1=1"
            params = []
            
            if filename_pattern:
                query += " AND filename LIKE ?"
                params.append(f"%{filename_pattern}%")
            
            if file_hash:
                query += " AND file_hash = ?"
                params.append(file_hash)
            
            if file_type:
                query += " AND file_type = ?"
                params.append(file_type)
            
            if project_id:
                query += " AND project_id = ?"
                params.append(project_id)
            
            if date_from:
                query += " AND uploaded_at >= ?"
                params.append(date_from)
            
            if date_to:
                query += " AND uploaded_at <= ?"
                params.append(date_to)
            
            if status:
                query += " AND status = ?"
                params.append(status)
            
            query += " ORDER BY uploaded_at DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            
            rows = cursor.fetchall()
            files = [dict(row) for row in rows]
            
            logger.info(f"🔍 Search found {len(files)} files matching criteria")
            
            return files
            
        finally:
            conn.close()

    def get_files_by_hash(self, file_hash: str) -> List[Dict[str, Any]]:
        """
        Find all files with the same hash (duplicates)
        
        Args:
            file_hash: SHA256 hash to search for
            
        Returns:
            List of file metadata dictionaries with matching hash
        """
        return self.search_files(file_hash=file_hash)

    def update_file_status(self, file_id: str, status: str) -> bool:
        """
        Update file status
        
        Args:
            file_id: ID of the file to update
            status: New status value
            
        Returns:
            True if updated, False if not found
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE uploaded_files
                SET status = ?
                WHERE file_id = ?
            """, (status, file_id))
            
            conn.commit()
            
            if cursor.rowcount > 0:
                logger.info(f"✅ Updated file status: {file_id} -> {status}")
                return True
            else:
                logger.warning(f"⚠️ File not found for update: {file_id}")
                return False
            
        finally:
            conn.close()

    def get_project_files_stats(self, project_id: str) -> Dict[str, Any]:
        """
        Get statistics about files for a project
        
        Args:
            project_id: Project ID to get stats for
            
        Returns:
            Dictionary with statistics:
            - total_files: Total number of files
            - total_size: Total size in bytes
            - file_types: Count by file type
            - status_counts: Count by status
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            # Total files and size
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_files,
                    SUM(file_size) as total_size
                FROM uploaded_files
                WHERE project_id = ?
            """, (project_id,))
            
            row = cursor.fetchone()
            stats = {
                'total_files': row['total_files'] or 0,
                'total_size': row['total_size'] or 0
            }
            
            # File types breakdown
            cursor.execute("""
                SELECT file_type, COUNT(*) as count
                FROM uploaded_files
                WHERE project_id = ?
                GROUP BY file_type
            """, (project_id,))
            
            stats['file_types'] = {row['file_type']: row['count'] for row in cursor.fetchall()}
            
            # Status breakdown
            cursor.execute("""
                SELECT status, COUNT(*) as count
                FROM uploaded_files
                WHERE project_id = ?
                GROUP BY status
            """, (project_id,))
            
            stats['status_counts'] = {row['status']: row['count'] for row in cursor.fetchall()}
            
            return stats
            
        finally:
            conn.close()


def calculate_file_hash(file_path: str) -> str:
    """
    Calculate SHA256 hash of a file
    
    Args:
        file_path: Path to the file
        
    Returns:
        SHA256 hash as hex string
        
    Raises:
        FileNotFoundError: If file doesn't exist
        IOError: If file cannot be read
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    sha256_hash = hashlib.sha256()
    
    try:
        with open(file_path, "rb") as f:
            # Read file in chunks to handle large files
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        
        return sha256_hash.hexdigest()
        
    except IOError as e:
        logger.error(f"❌ Error reading file for hash: {e}")
        raise


def get_file_type_from_path(file_path: str) -> str:
    """
    Get file type from file path
    
    Args:
        file_path: Path to the file
        
    Returns:
        File extension (e.g., '.txt', '.pdf')
    """
    return Path(file_path).suffix.lower()
