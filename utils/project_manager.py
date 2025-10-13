"""
Project Manager

Manages project CRUD operations for the estimation system.
Each project can have multiple estimation runs and tasks.
"""

import sqlite3
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime

from utils.logger import get_logger

logger = get_logger(__name__)


class ProjectManager:
    """
    Manager for project CRUD operations
    
    Handles creation, retrieval, updating, deletion, and listing of projects
    in the SQLite database.
    """

    def __init__(self, db_path: str = "./estimation_tracker.db"):
        """
        Initialize ProjectManager with database path
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        logger.info(f"📁 Project Manager initialized: {db_path}")

    def create_project(
        self,
        name: str,
        description: str = "",
        status: str = "active",
        project_id: Optional[str] = None
    ) -> str:
        """
        Create a new project
        
        Args:
            name: Project name (required)
            description: Project description
            status: Project status (default: 'active')
            project_id: Optional custom project ID (auto-generated if not provided)
            
        Returns:
            project_id of the created project
        """
        if not name:
            raise ValueError("Project name is required")
        
        if project_id is None:
            project_id = f"proj_{uuid.uuid4().hex[:12]}"
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO projects (project_id, name, description, status)
                VALUES (?, ?, ?, ?)
            """, (project_id, name, description, status))
            
            conn.commit()
            logger.info(f"✅ Created project: {project_id} - {name}")
            
            return project_id
            
        except sqlite3.IntegrityError as e:
            logger.error(f"❌ Error creating project: {e}")
            raise ValueError(f"Project with ID '{project_id}' already exists")
            
        finally:
            conn.close()

    def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a project by ID
        
        Args:
            project_id: ID of the project to retrieve
            
        Returns:
            Dictionary with project details or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT * FROM projects
                WHERE project_id = ?
            """, (project_id,))
            
            row = cursor.fetchone()
            
            if row:
                return dict(row)
            else:
                logger.warning(f"⚠️ Project {project_id} not found")
                return None
                
        finally:
            conn.close()

    def update_project(
        self,
        project_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None
    ) -> bool:
        """
        Update a project's details
        
        Args:
            project_id: ID of the project to update
            name: New project name (optional)
            description: New project description (optional)
            status: New project status (optional)
            
        Returns:
            True if update was successful, False otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Build dynamic update query
        updates = []
        params = []
        
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        
        if description is not None:
            updates.append("description = ?")
            params.append(description)
        
        if status is not None:
            updates.append("status = ?")
            params.append(status)
        
        if not updates:
            logger.warning(f"⚠️ No updates provided for project {project_id}")
            conn.close()
            return False
        
        # Always update the updated_at timestamp
        updates.append("updated_at = CURRENT_TIMESTAMP")
        
        query = f"UPDATE projects SET {', '.join(updates)} WHERE project_id = ?"
        params.append(project_id)
        
        try:
            cursor.execute(query, params)
            conn.commit()
            
            if cursor.rowcount > 0:
                logger.info(f"✅ Updated project: {project_id}")
                return True
            else:
                logger.warning(f"⚠️ Project {project_id} not found")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error updating project {project_id}: {e}")
            conn.rollback()
            return False
            
        finally:
            conn.close()

    def delete_project(self, project_id: str, cascade: bool = False) -> bool:
        """
        Delete a project
        
        Args:
            project_id: ID of the project to delete
            cascade: If True, also delete associated estimation runs and tasks
                    If False, only delete if no associated data exists
            
        Returns:
            True if deletion was successful, False otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            if not cascade:
                # Check if project has associated estimation runs
                cursor.execute("""
                    SELECT COUNT(*) FROM estimation_runs
                    WHERE project_id = ?
                """, (project_id,))
                
                count = cursor.fetchone()[0]
                
                if count > 0:
                    logger.warning(
                        f"⚠️ Cannot delete project {project_id}: "
                        f"has {count} associated estimation runs. "
                        f"Use cascade=True to force deletion."
                    )
                    return False
            
            else:
                # Delete associated estimation tasks first
                cursor.execute("""
                    DELETE FROM estimation_tasks
                    WHERE project_id = ?
                """, (project_id,))
                
                tasks_deleted = cursor.rowcount
                
                # Delete associated estimation runs
                cursor.execute("""
                    DELETE FROM estimation_runs
                    WHERE project_id = ?
                """, (project_id,))
                
                runs_deleted = cursor.rowcount
                
                if tasks_deleted > 0 or runs_deleted > 0:
                    logger.info(
                        f"🗑️ Cascade deleted {runs_deleted} estimation runs "
                        f"and {tasks_deleted} tasks for project {project_id}"
                    )
            
            # Delete the project
            cursor.execute("""
                DELETE FROM projects
                WHERE project_id = ?
            """, (project_id,))
            
            conn.commit()
            
            if cursor.rowcount > 0:
                logger.info(f"✅ Deleted project: {project_id}")
                return True
            else:
                logger.warning(f"⚠️ Project {project_id} not found")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error deleting project {project_id}: {e}")
            conn.rollback()
            return False
            
        finally:
            conn.close()

    def list_projects(
        self,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List all projects with optional filtering
        
        Args:
            status: Filter by project status (optional)
            limit: Maximum number of results
            offset: Number of results to skip (for pagination)
            
        Returns:
            List of project dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM projects WHERE 1=1"
        params = []
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        try:
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            projects = [dict(row) for row in rows]
            
            logger.debug(f"📚 Retrieved {len(projects)} projects")
            return projects
            
        finally:
            conn.close()

    def get_project_statistics(self, project_id: str) -> Dict[str, Any]:
        """
        Get statistics for a specific project
        
        Args:
            project_id: ID of the project
            
        Returns:
            Dictionary with project statistics:
                - total_estimations: Number of estimation runs
                - total_tasks: Total tasks across all runs
                - total_effort: Total effort in mandays
                - avg_confidence: Average confidence level
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Get estimation run statistics
            cursor.execute("""
                SELECT
                    COUNT(*) as total_estimations,
                    SUM(total_tasks) as total_tasks,
                    SUM(total_effort) as total_effort,
                    AVG(average_confidence) as avg_confidence
                FROM estimation_runs
                WHERE project_id = ?
            """, (project_id,))
            
            row = cursor.fetchone()
            
            stats = {
                'project_id': project_id,
                'total_estimations': row[0] or 0,
                'total_tasks': row[1] or 0,
                'total_effort': round(row[2], 2) if row[2] else 0.0,
                'avg_confidence': round(row[3], 2) if row[3] else 0.0
            }
            
            logger.debug(f"📊 Statistics for project {project_id}: {stats}")
            return stats
            
        finally:
            conn.close()

    def search_projects(
        self,
        keyword: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search projects by keyword and/or status
        
        Args:
            keyword: Search in project name and description
            status: Filter by project status
            
        Returns:
            List of matching project dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM projects WHERE 1=1"
        params = []
        
        if keyword:
            query += " AND (name LIKE ? OR description LIKE ?)"
            params.extend([f"%{keyword}%", f"%{keyword}%"])
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        query += " ORDER BY created_at DESC"
        
        try:
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            projects = [dict(row) for row in rows]
            
            logger.debug(f"🔍 Search found {len(projects)} projects")
            return projects
            
        finally:
            conn.close()


# Singleton instance
_project_manager_instance = None


def get_project_manager(db_path: str = None) -> ProjectManager:
    """
    Get singleton instance of ProjectManager
    
    Args:
        db_path: Optional custom database path
        
    Returns:
        ProjectManager instance
    """
    global _project_manager_instance
    
    if _project_manager_instance is None:
        from config import Config
        db_path = db_path or Config.ESTIMATION_TRACKER_DB
        _project_manager_instance = ProjectManager(db_path)
    
    return _project_manager_instance
