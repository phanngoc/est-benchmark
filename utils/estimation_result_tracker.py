"""
Estimation Result Tracker with SQLite Database

Manages estimation run history and provides queryable interface for past estimations.
Stores aggregated run metadata and detailed task data with file path linking.
"""

import os
import sqlite3
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path

from utils.logger import get_logger

logger = get_logger(__name__)


class EstimationResultTracker:
    """
    SQLite-based tracker for estimation results

    Manages two tables:
    - estimation_runs: High-level run metadata with file paths
    - estimation_tasks: Detailed task-level data for each run
    """

    def __init__(self, db_path: str = "./estimation_tracker.db"):
        """
        Initialize tracker with SQLite database

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._init_database()
        logger.info(f"📊 Estimation Result Tracker initialized: {db_path}")

    def _init_database(self):
        """Create database tables if they don't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create estimation_runs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS estimation_runs (
                estimation_id TEXT PRIMARY KEY,
                file_path TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_effort REAL,
                total_tasks INTEGER,
                average_confidence REAL,
                workflow_status TEXT,
                project_description TEXT
            )
        """)

        # Create estimation_tasks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS estimation_tasks (
                task_id INTEGER PRIMARY KEY AUTOINCREMENT,
                estimation_id TEXT NOT NULL,
                id TEXT,
                category TEXT,
                role TEXT,
                parent_task TEXT,
                sub_task TEXT,
                description TEXT,
                estimation_manday REAL,
                estimation_backend_manday REAL,
                estimation_frontend_manday REAL,
                estimation_qa_manday REAL,
                estimation_infra_manday REAL,
                confidence_level REAL,
                complexity TEXT,
                priority TEXT,
                dependencies TEXT,
                risk_factors TEXT,
                assumptions TEXT,
                FOREIGN KEY (estimation_id) REFERENCES estimation_runs(estimation_id)
            )
        """)

        # Create indexes for performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_estimation_id
            ON estimation_tasks(estimation_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_category
            ON estimation_tasks(category)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_role
            ON estimation_tasks(role)
        """)

        conn.commit()
        conn.close()

        logger.debug("✅ Database tables initialized")

    def create_estimation_run(
        self,
        estimation_id: str,
        file_path: str,
        summary_data: Dict[str, Any]
    ) -> str:
        """
        Create a new estimation run entry

        Args:
            estimation_id: Unique identifier for this estimation (timestamp-based)
            file_path: Path to the exported Excel file
            summary_data: Dictionary with run summary:
                - total_effort: Total effort in mandays
                - total_tasks: Number of tasks
                - average_confidence: Average confidence level
                - workflow_status: Status (completed, failed, etc.)
                - project_description: Original task description

        Returns:
            estimation_id
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO estimation_runs
                (estimation_id, file_path, total_effort, total_tasks,
                 average_confidence, workflow_status, project_description)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                estimation_id,
                file_path,
                summary_data.get('total_effort', 0.0),
                summary_data.get('total_tasks', 0),
                summary_data.get('average_confidence', 0.0),
                summary_data.get('workflow_status', 'unknown'),
                summary_data.get('project_description', '')
            ))

            conn.commit()
            logger.info(f"✅ Created estimation run: {estimation_id}")

            return estimation_id

        except sqlite3.IntegrityError as e:
            logger.warning(f"⚠️ Estimation run {estimation_id} already exists: {e}")
            return estimation_id

        finally:
            conn.close()

    def save_estimation_tasks(
        self,
        estimation_id: str,
        tasks_data: List[Dict[str, Any]]
    ) -> int:
        """
        Save detailed task data for an estimation run

        Args:
            estimation_id: ID of the estimation run
            tasks_data: List of task dictionaries with estimation details

        Returns:
            Number of tasks saved
        """
        if not tasks_data:
            logger.warning(f"⚠️ No tasks to save for estimation {estimation_id}")
            return 0

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        saved_count = 0

        try:
            for task in tasks_data:
                # Serialize complex fields to JSON
                dependencies_json = json.dumps(task.get('dependencies', []))
                risk_factors_json = json.dumps(task.get('risk_factors', []))
                assumptions_json = json.dumps(task.get('assumptions', []))

                cursor.execute("""
                    INSERT INTO estimation_tasks
                    (estimation_id, id, category, role, parent_task, sub_task,
                     description, estimation_manday, estimation_backend_manday,
                     estimation_frontend_manday, estimation_qa_manday,
                     estimation_infra_manday, confidence_level, complexity,
                     priority, dependencies, risk_factors, assumptions)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    estimation_id,
                    task.get('id', ''),
                    task.get('category', ''),
                    task.get('role', ''),
                    task.get('parent_task', ''),
                    task.get('sub_task', ''),
                    task.get('description', ''),
                    float(task.get('estimation_manday', 0.0)),
                    float(task.get('estimation_backend_manday', 0.0)),
                    float(task.get('estimation_frontend_manday', 0.0)),
                    float(task.get('estimation_qa_manday', 0.0)),
                    float(task.get('estimation_infra_manday', 0.0)),
                    float(task.get('confidence_level', 0.0)),
                    task.get('complexity', 'Medium'),
                    task.get('priority', 'Medium'),
                    dependencies_json,
                    risk_factors_json,
                    assumptions_json
                ))

                saved_count += 1

            conn.commit()
            logger.info(f"✅ Saved {saved_count} tasks for estimation {estimation_id}")

        except Exception as e:
            logger.error(f"❌ Error saving tasks for {estimation_id}: {e}")
            conn.rollback()

        finally:
            conn.close()

        return saved_count

    def get_estimation_by_id(self, estimation_id: str) -> Optional[Dict[str, Any]]:
        """
        Get estimation run details by ID

        Args:
            estimation_id: ID of the estimation run

        Returns:
            Dictionary with run details or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT * FROM estimation_runs
                WHERE estimation_id = ?
            """, (estimation_id,))

            row = cursor.fetchone()

            if row:
                return dict(row)
            else:
                logger.warning(f"⚠️ Estimation {estimation_id} not found")
                return None

        finally:
            conn.close()

    def get_estimation_tasks(self, estimation_id: str) -> List[Dict[str, Any]]:
        """
        Get all tasks for an estimation run

        Args:
            estimation_id: ID of the estimation run

        Returns:
            List of task dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT * FROM estimation_tasks
                WHERE estimation_id = ?
                ORDER BY task_id
            """, (estimation_id,))

            rows = cursor.fetchall()

            tasks = []
            for row in rows:
                task = dict(row)

                # Deserialize JSON fields
                try:
                    task['dependencies'] = json.loads(task.get('dependencies', '[]'))
                    task['risk_factors'] = json.loads(task.get('risk_factors', '[]'))
                    task['assumptions'] = json.loads(task.get('assumptions', '[]'))
                except json.JSONDecodeError:
                    task['dependencies'] = []
                    task['risk_factors'] = []
                    task['assumptions'] = []

                tasks.append(task)

            logger.debug(f"📋 Retrieved {len(tasks)} tasks for estimation {estimation_id}")
            return tasks

        finally:
            conn.close()

    def list_all_estimations(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List all estimation runs, ordered by creation date (newest first)

        Args:
            limit: Maximum number of results
            offset: Number of results to skip (for pagination)

        Returns:
            List of estimation run dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT * FROM estimation_runs
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """, (limit, offset))

            rows = cursor.fetchall()

            estimations = [dict(row) for row in rows]

            logger.debug(f"📚 Retrieved {len(estimations)} estimation runs")
            return estimations

        finally:
            conn.close()

    def search_estimations(
        self,
        keyword: str = None,
        min_effort: float = None,
        max_effort: float = None,
        status: str = None
    ) -> List[Dict[str, Any]]:
        """
        Search estimations with filters

        Args:
            keyword: Search in project_description
            min_effort: Minimum total effort
            max_effort: Maximum total effort
            status: Workflow status filter

        Returns:
            List of matching estimation runs
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = "SELECT * FROM estimation_runs WHERE 1=1"
        params = []

        if keyword:
            query += " AND project_description LIKE ?"
            params.append(f"%{keyword}%")

        if min_effort is not None:
            query += " AND total_effort >= ?"
            params.append(min_effort)

        if max_effort is not None:
            query += " AND total_effort <= ?"
            params.append(max_effort)

        if status:
            query += " AND workflow_status = ?"
            params.append(status)

        query += " ORDER BY created_at DESC"

        try:
            cursor.execute(query, params)
            rows = cursor.fetchall()

            results = [dict(row) for row in rows]

            logger.debug(f"🔍 Search found {len(results)} estimations")
            return results

        finally:
            conn.close()

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get aggregate statistics across all estimations

        Returns:
            Dictionary with statistics:
                - total_estimations: Number of estimation runs
                - total_tasks: Total tasks across all runs
                - avg_effort: Average effort per estimation
                - avg_confidence: Average confidence level
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Get run-level statistics
            cursor.execute("""
                SELECT
                    COUNT(*) as total_estimations,
                    SUM(total_tasks) as total_tasks,
                    AVG(total_effort) as avg_effort,
                    AVG(average_confidence) as avg_confidence
                FROM estimation_runs
            """)

            row = cursor.fetchone()

            stats = {
                'total_estimations': row[0] or 0,
                'total_tasks': row[1] or 0,
                'avg_effort': round(row[2], 2) if row[2] else 0.0,
                'avg_confidence': round(row[3], 2) if row[3] else 0.0
            }

            logger.debug(f"📊 Statistics: {stats}")
            return stats

        finally:
            conn.close()


# Singleton instance
_tracker_instance = None


def get_result_tracker(db_path: str = None) -> EstimationResultTracker:
    """
    Get singleton instance of EstimationResultTracker

    Args:
        db_path: Optional custom database path

    Returns:
        EstimationResultTracker instance
    """
    global _tracker_instance

    if _tracker_instance is None:
        from config import Config
        db_path = db_path or Config.ESTIMATION_TRACKER_DB
        _tracker_instance = EstimationResultTracker(db_path)

    return _tracker_instance
