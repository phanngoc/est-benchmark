"""
Estimation History Manager with ChromaDB for semantic search
"""
import os
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions

from .embedding_service import get_embedding_service


class EstimationHistoryManager:
    """Manages estimation history with semantic search capabilities and project isolation"""

    def __init__(
        self,
        db_path: str = "./estimation_history_db",
        collection_name: str = "estimation_history",
        project_id: Optional[str] = None
    ):
        """
        Initialize history manager with optional project isolation

        Args:
            db_path: Path to ChromaDB storage
            collection_name: Base name of the collection
            project_id: Optional project ID for project-scoped collection.
                       If provided, creates collection named "project_{project_id}_history"
        """
        self.db_path = db_path
        self.base_collection_name = collection_name
        self.project_id = project_id
        self.embedding_service = get_embedding_service()

        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=db_path,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        # Create or get collection (project-scoped if project_id provided)
        self.collection = self.get_or_create_project_collection()

    def get_or_create_project_collection(self):
        """
        Get or create collection with project-specific name if project_id is set
        
        Returns:
            ChromaDB collection instance
        """
        if self.project_id:
            # Create project-specific collection name
            collection_name = f"project_{self.project_id}_history"
            from utils.logger import get_logger
            logger = get_logger(__name__)
            logger.info(f"Using project-scoped collection: {collection_name}")
        else:
            # Use base collection name for global history
            collection_name = self.base_collection_name
            from utils.logger import get_logger
            logger = get_logger(__name__)
            logger.info(f"Using global collection: {collection_name}")
        
        # Store the actual collection name being used
        self.collection_name = collection_name
        
        # Get or create collection
        collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={
                "description": f"Task estimation history with embeddings",
                "project_id": self.project_id if self.project_id else "global"
            }
        )
        
        return collection

    def _prepare_task_text(self, task: Dict[str, Any]) -> str:
        """
        Prepare task text for embedding

        Combines category, parent_task, sub_task, and description
        """
        parts = []

        if task.get('category'):
            parts.append(f"Category: {task['category']}")
        if task.get('parent_task'):
            parts.append(f"Parent: {task['parent_task']}")
        if task.get('sub_task'):
            parts.append(f"Task: {task['sub_task']}")
        if task.get('description'):
            parts.append(f"Description: {task['description']}")

        return " | ".join(parts)

    def _prepare_metadata(self, task: Dict[str, Any], project_name: str) -> Dict[str, Any]:
        """
        Prepare metadata for storage
        
        Args:
            task: Task dictionary
            project_name: Name of the project
            
        Returns:
            Metadata dictionary with project_id if available
        """
        metadata = {
            'project_name': project_name,
            'category': task.get('category', ''),
            'role': task.get('role', ''),
            'parent_task': task.get('parent_task', ''),
            'sub_task': task.get('sub_task', ''),
            'complexity': task.get('complexity', 'Medium'),
            'priority': task.get('priority', 'Medium'),
            'estimation_manday': float(task.get('estimation_manday', 0.0)),
            
            # Detailed effort breakdown by task type per role (matching workflow.py)
            'backend_implement': float(task.get('backend_implement', 0.0)),
            'backend_fixbug': float(task.get('backend_fixbug', 0.0)),
            'backend_unittest': float(task.get('backend_unittest', 0.0)),
            'frontend_implement': float(task.get('frontend_implement', 0.0)),
            'frontend_fixbug': float(task.get('frontend_fixbug', 0.0)),
            'frontend_unittest': float(task.get('frontend_unittest', 0.0)),
            'responsive_implement': float(task.get('responsive_implement', 0.0)),
            'testing_implement': float(task.get('testing_implement', 0.0)),
            
            'confidence_level': float(task.get('confidence_level', 0.7)),
            'created_at': datetime.now().isoformat(),
            'validated': task.get('validated', False)
        }
        
        # Add project_id to metadata if this is a project-scoped instance
        if self.project_id:
            metadata['project_id'] = self.project_id

        return metadata

    def save_estimation(
        self,
        task: Dict[str, Any],
        project_name: str,
        task_id: Optional[str] = None
    ) -> str:
        """
        Save estimation to history

        Args:
            task: Task dictionary with estimation data
            project_name: Name of the project
            task_id: Optional custom ID (auto-generated if None)

        Returns:
            Task ID
        """
        if task_id is None:
            task_id = task.get('id', f"{project_name}_{datetime.now().timestamp()}")

        # Prepare text for embedding
        task_text = self._prepare_task_text(task)

        # Generate embedding
        embedding = self.embedding_service.generate_embedding(task_text)

        # Prepare metadata
        metadata = self._prepare_metadata(task, project_name)

        # Store full task data as document
        document = json.dumps(task, ensure_ascii=False)

        # Add to collection
        self.collection.add(
            ids=[task_id],
            embeddings=[embedding],
            documents=[document],
            metadatas=[metadata]
        )

        return task_id

    def batch_save(
        self,
        tasks: List[Dict[str, Any]],
        project_name: str
    ) -> List[str]:
        """
        Batch save multiple estimations

        Args:
            tasks: List of task dictionaries
            project_name: Name of the project

        Returns:
            List of task IDs
        """
        if not tasks:
            return []

        ids = []
        embeddings = []
        documents = []
        metadatas = []

        # Prepare all data
        for task in tasks:
            task_id = task.get('id', f"{project_name}_{datetime.now().timestamp()}_{len(ids)}")
            ids.append(task_id)

            task_text = self._prepare_task_text(task)
            documents.append(json.dumps(task, ensure_ascii=False))
            metadatas.append(self._prepare_metadata(task, project_name))

        # Generate embeddings in batch
        task_texts = [self._prepare_task_text(task) for task in tasks]
        embeddings = self.embedding_service.generate_batch_embeddings(task_texts)

        # Add to collection
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )

        return ids

    def search_similar(
        self,
        description: str,
        category: Optional[str] = None,
        role: Optional[str] = None,
        complexity: Optional[str] = None,
        top_k: int = 5,
        similarity_threshold: float = 0.7
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        Search for similar tasks using semantic search

        Args:
            description: Task description to search for
            category: Optional category filter
            role: Optional role filter
            complexity: Optional complexity filter
            top_k: Number of results to return
            similarity_threshold: Minimum similarity score (0-1)

        Returns:
            List of (task_dict, similarity_score) tuples
        """
        # Build query text
        query_parts = [f"Description: {description}"]
        if category:
            query_parts.insert(0, f"Category: {category}")
        query_text = " | ".join(query_parts)

        # Generate embedding for query
        query_embedding = self.embedding_service.generate_embedding(query_text)

        # Build where filter with proper ChromaDB syntax
        where_conditions = []
        if category:
            where_conditions.append({'category': category})
        if role:
            where_conditions.append({'role': role})
        if complexity:
            where_conditions.append({'complexity': complexity})

        # Use $and operator for multiple conditions
        where_filter = None
        if len(where_conditions) == 1:
            where_filter = where_conditions[0]
        elif len(where_conditions) > 1:
            where_filter = {'$and': where_conditions}

        # Search
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_filter
        )

        # Parse results
        similar_tasks = []
        if results['ids'] and results['ids'][0]:
            for i in range(len(results['ids'][0])):
                # Calculate similarity score (1 - distance for cosine similarity)
                distance = results['distances'][0][i]
                similarity = 1.0 - distance

                if similarity >= similarity_threshold:
                    task_data = json.loads(results['documents'][0][i])
                    task_data['_metadata'] = results['metadatas'][0][i]
                    similar_tasks.append((task_data, similarity))

        return similar_tasks

    def build_few_shot_prompt(
        self,
        similar_tasks: List[Tuple[Dict[str, Any], float]],
        max_examples: int = 5
    ) -> str:
        """
        Build few-shot prompt from similar tasks

        Args:
            similar_tasks: List of (task, similarity) tuples
            max_examples: Maximum number of examples to include

        Returns:
            Formatted prompt string
        """
        if not similar_tasks:
            return "No similar historical tasks found."

        prompt_parts = ["## Historical Reference Examples (Similar Tasks):\n"]

        for i, (task, similarity) in enumerate(similar_tasks[:max_examples], 1):
            prompt_parts.append(f"\n**Example {i}** (Similarity: {similarity:.2f}):")
            prompt_parts.append(f"- Category: {task.get('category', 'N/A')}")
            prompt_parts.append(f"- Role: {task.get('role', 'N/A')}")
            prompt_parts.append(f"- Parent Task: {task.get('parent_task', 'N/A')}")
            prompt_parts.append(f"- Sub Task: {task.get('sub_task', 'N/A')}")
            prompt_parts.append(f"- Description: {task.get('description', 'N/A')}")
            prompt_parts.append(f"- Complexity: {task.get('complexity', 'N/A')}")
            prompt_parts.append(f"- **Estimated Effort**: {task.get('estimation_manday', 0):.1f} mandays total")

            # Show detailed task type breakdown per role
            backend_total = task.get('backend_implement', 0) + task.get('backend_fixbug', 0) + task.get('backend_unittest', 0)
            if backend_total > 0:
                prompt_parts.append(f"  - Backend: {backend_total:.1f} mandays (Impl: {task.get('backend_implement', 0):.1f}, Fix: {task.get('backend_fixbug', 0):.1f}, Test: {task.get('backend_unittest', 0):.1f})")
            
            frontend_total = task.get('frontend_implement', 0) + task.get('frontend_fixbug', 0) + task.get('frontend_unittest', 0)
            if frontend_total > 0:
                prompt_parts.append(f"  - Frontend: {frontend_total:.1f} mandays (Impl: {task.get('frontend_implement', 0):.1f}, Fix: {task.get('frontend_fixbug', 0):.1f}, Test: {task.get('frontend_unittest', 0):.1f})")
            
            if task.get('responsive_implement', 0) > 0:
                prompt_parts.append(f"  - Responsive: {task.get('responsive_implement', 0):.1f} mandays")
            if task.get('testing_implement', 0) > 0:
                prompt_parts.append(f"  - Testing: {task.get('testing_implement', 0):.1f} mandays")

            prompt_parts.append(f"- Confidence: {task.get('confidence_level', 0.7):.2f}")

            # Add project context if available
            metadata = task.get('_metadata', {})
            if metadata.get('project_name'):
                prompt_parts.append(f"- Project: {metadata['project_name']}")

        prompt_parts.append("\n**Instructions**: Based on these similar historical estimations, estimate the current task. Consider:")
        prompt_parts.append("- Relative complexity compared to examples")
        prompt_parts.append("- Role-specific effort patterns")
        prompt_parts.append("- Confidence levels from similar tasks")
        prompt_parts.append("- Adjust for any unique aspects of the current task\n")

        return "\n".join(prompt_parts)

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the history database"""
        count = self.collection.count()

        # Get all metadata to calculate stats
        all_data = self.collection.get()

        stats = {
            'total_tasks': count,
            'by_role': {},
            'by_category': {},
            'by_complexity': {},
            'avg_estimation': 0.0,
            'avg_confidence': 0.0
        }

        if all_data['metadatas']:
            total_estimation = 0.0
            total_confidence = 0.0

            for metadata in all_data['metadatas']:
                # Count by role
                role = metadata.get('role', 'Unknown')
                stats['by_role'][role] = stats['by_role'].get(role, 0) + 1

                # Count by category
                category = metadata.get('category', 'Unknown')
                stats['by_category'][category] = stats['by_category'].get(category, 0) + 1

                # Count by complexity
                complexity = metadata.get('complexity', 'Medium')
                stats['by_complexity'][complexity] = stats['by_complexity'].get(complexity, 0) + 1

                # Sum for averages
                total_estimation += metadata.get('estimation_manday', 0.0)
                total_confidence += metadata.get('confidence_level', 0.7)

            if count > 0:
                stats['avg_estimation'] = total_estimation / count
                stats['avg_confidence'] = total_confidence / count

        return stats

    def clear_history(self):
        """Clear all history (use with caution!)"""
        self.client.delete_collection(self.collection_name)
        self.collection = self.client.create_collection(
            name=self.collection_name,
            metadata={"description": "Task estimation history with embeddings"}
        )

    # ========================
    # CSV Import/Export Methods
    # ========================

    def import_from_csv(self, csv_path: str) -> int:
        """
        Import tasks from CSV file

        Args:
            csv_path: Path to CSV file

        Returns:
            Number of tasks imported
        """
        import pandas as pd

        try:
            # Read CSV
            df = pd.read_csv(csv_path)

            # Validate required columns
            required_cols = ['category', 'role', 'sub_task', 'description', 'estimation_manday']
            missing_cols = [col for col in required_cols if col not in df.columns]

            if missing_cols:
                raise ValueError(f"Missing required columns: {missing_cols}")

            # Convert to task dicts
            tasks = []
            for _, row in df.iterrows():
                task = row.to_dict()

                # Handle NaN values
                task = {k: (v if pd.notna(v) else '') for k, v in task.items()}

                # Ensure numeric fields are floats
                numeric_fields = [
                    'estimation_manday', 'backend_implement', 'backend_fixbug', 'backend_unittest',
                    'frontend_implement', 'frontend_fixbug', 'frontend_unittest',
                    'responsive_implement', 'testing_implement', 'confidence_level'
                ]
                for field in numeric_fields:
                    if field in task:
                        try:
                            task[field] = float(task[field]) if task[field] else 0.0
                        except (ValueError, TypeError):
                            task[field] = 0.0

                tasks.append(task)

            # Batch save with project name from CSV or default
            project_name = tasks[0].get('project_name', 'imported') if tasks else 'imported'
            task_ids = self.batch_save(tasks, project_name=project_name)

            return len(task_ids)

        except Exception as e:
            raise ValueError(f"Failed to import CSV: {e}")

    def export_to_csv(self, filepath: str) -> str:
        """
        Export all tasks to CSV file

        Args:
            filepath: Path to output CSV file

        Returns:
            Path to exported file
        """
        import pandas as pd

        try:
            # Get all tasks
            all_data = self.collection.get()

            if not all_data['documents']:
                raise ValueError("No tasks to export")

            # Parse to list of dicts
            tasks = []
            for i, doc in enumerate(all_data['documents']):
                task = json.loads(doc)
                # Merge with metadata
                metadata = all_data['metadatas'][i]
                task.update(metadata)
                tasks.append(task)

            # Create DataFrame
            df = pd.DataFrame(tasks)

            # Reorder columns for better readability
            column_order = [
                'id', 'category', 'role', 'parent_task', 'sub_task', 'description',
                'complexity', 'priority', 'estimation_manday',
                'backend_implement', 'backend_fixbug', 'backend_unittest',
                'frontend_implement', 'frontend_fixbug', 'frontend_unittest',
                'responsive_implement', 'testing_implement',
                'confidence_level', 'validated', 'project_name', 'created_at'
            ]

            # Only include columns that exist
            existing_cols = [col for col in column_order if col in df.columns]
            df = df[existing_cols]

            # Export to CSV
            df.to_csv(filepath, index=False)

            return filepath

        except Exception as e:
            raise ValueError(f"Failed to export CSV: {e}")

    def validate_csv_format(self, csv_path: str) -> Tuple[bool, str]:
        """
        Validate CSV file format

        Args:
            csv_path: Path to CSV file

        Returns:
            Tuple of (is_valid, error_message)
        """
        import pandas as pd

        try:
            df = pd.read_csv(csv_path)

            # Check required columns
            required_cols = ['category', 'role', 'sub_task', 'description', 'estimation_manday']
            missing_cols = [col for col in required_cols if col not in df.columns]

            if missing_cols:
                return False, f"Missing required columns: {', '.join(missing_cols)}"

            # Check if file is empty
            if len(df) == 0:
                return False, "CSV file is empty"

            # Validate estimation_manday is numeric
            try:
                pd.to_numeric(df['estimation_manday'], errors='coerce')
            except:
                return False, "estimation_manday column must contain numeric values"

            return True, "CSV format is valid"

        except Exception as e:
            return False, f"Failed to read CSV: {e}"

    # ========================
    # CRUD Operations
    # ========================

    def get_task_by_id(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get single task by ID

        Args:
            task_id: Task ID

        Returns:
            Task dictionary or None if not found
        """
        try:
            result = self.collection.get(ids=[task_id])

            if result['documents'] and len(result['documents']) > 0:
                task = json.loads(result['documents'][0])
                # Merge with metadata
                task['_metadata'] = result['metadatas'][0]
                return task
            else:
                return None

        except Exception as e:
            return None

    def update_task(self, task_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update existing task

        Args:
            task_id: Task ID to update
            updates: Dictionary with fields to update

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get existing task
            existing_task = self.get_task_by_id(task_id)

            if not existing_task:
                return False

            # Merge updates
            existing_task.update(updates)

            # Remove metadata field if present
            existing_task.pop('_metadata', None)

            # Delete old version
            self.collection.delete(ids=[task_id])

            # Re-save with same ID
            project_name = updates.get('project_name', existing_task.get('project_name', 'updated'))
            self.save_estimation(existing_task, project_name=project_name, task_id=task_id)

            return True

        except Exception as e:
            return False

    def delete_task(self, task_id: str) -> bool:
        """
        Delete task by ID

        Args:
            task_id: Task ID to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            self.collection.delete(ids=[task_id])
            return True
        except Exception as e:
            return False

    def get_all_tasks_paginated(
        self,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get all tasks with pagination

        Args:
            limit: Maximum number of tasks to return
            offset: Number of tasks to skip

        Returns:
            List of task dictionaries
        """
        try:
            # Get all data (ChromaDB doesn't support offset directly)
            all_data = self.collection.get()

            if not all_data['documents']:
                return []

            # Parse tasks
            tasks = []
            for i, doc in enumerate(all_data['documents']):
                task = json.loads(doc)
                task['_metadata'] = all_data['metadatas'][i]
                task['_id'] = all_data['ids'][i]
                tasks.append(task)

            # Apply pagination
            start = offset
            end = offset + limit

            return tasks[start:end]

        except Exception as e:
            return []

    def filter_by_criteria(
        self,
        category: Optional[str] = None,
        role: Optional[str] = None,
        complexity: Optional[str] = None,
        project_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Filter tasks by multiple criteria

        Args:
            category: Filter by category
            role: Filter by role
            complexity: Filter by complexity
            project_name: Filter by project name

        Returns:
            List of matching task dictionaries
        """
        # Build where filter
        where_conditions = []

        if category:
            where_conditions.append({'category': category})
        if role:
            where_conditions.append({'role': role})
        if complexity:
            where_conditions.append({'complexity': complexity})
        if project_name:
            where_conditions.append({'project_name': project_name})

        # Use $and operator for multiple conditions
        where_filter = None
        if len(where_conditions) == 1:
            where_filter = where_conditions[0]
        elif len(where_conditions) > 1:
            where_filter = {'$and': where_conditions}

        try:
            if where_filter:
                result = self.collection.get(where=where_filter)
            else:
                result = self.collection.get()

            # Parse results
            tasks = []
            if result['documents']:
                for i, doc in enumerate(result['documents']):
                    task = json.loads(doc)
                    task['_metadata'] = result['metadatas'][i]
                    task['_id'] = result['ids'][i]
                    tasks.append(task)

            return tasks

        except Exception as e:
            return []


# Singleton instances (one per project or global)
_history_manager_instances = {}

def get_history_manager(
    db_path: Optional[str] = None,
    collection_name: Optional[str] = None,
    project_id: Optional[str] = None
) -> EstimationHistoryManager:
    """
    Get or create EstimationHistoryManager instance
    
    Creates project-specific instances when project_id is provided,
    or returns global instance when project_id is None.
    
    Args:
        db_path: Optional custom database path
        collection_name: Optional custom collection name
        project_id: Optional project ID for project-scoped instance
        
    Returns:
        EstimationHistoryManager instance
    """
    global _history_manager_instances
    
    # Create key for instance lookup
    instance_key = project_id if project_id else "global"
    
    # Create new instance if not exists
    if instance_key not in _history_manager_instances:
        # Use defaults from config if not provided
        if db_path is None:
            from config import Config
            db_path = Config.ESTIMATION_HISTORY_DB_PATH
        
        if collection_name is None:
            from config import Config
            collection_name = Config.ESTIMATION_HISTORY_COLLECTION
        
        _history_manager_instances[instance_key] = EstimationHistoryManager(
            db_path=db_path,
            collection_name=collection_name,
            project_id=project_id
        )
    
    return _history_manager_instances[instance_key]
