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
    """Manages estimation history with semantic search capabilities"""

    def __init__(
        self,
        db_path: str = "./estimation_history_db",
        collection_name: str = "estimation_history"
    ):
        """
        Initialize history manager

        Args:
            db_path: Path to ChromaDB storage
            collection_name: Name of the collection
        """
        self.db_path = db_path
        self.collection_name = collection_name
        self.embedding_service = get_embedding_service()

        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=db_path,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        # Create or get collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"description": "Task estimation history with embeddings"}
        )

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
        """Prepare metadata for storage"""
        metadata = {
            'project_name': project_name,
            'category': task.get('category', ''),
            'role': task.get('role', ''),
            'parent_task': task.get('parent_task', ''),
            'sub_task': task.get('sub_task', ''),
            'complexity': task.get('complexity', 'Medium'),
            'priority': task.get('priority', 'Medium'),
            'estimation_manday': float(task.get('estimation_manday', 0.0)),
            'estimation_backend_manday': float(task.get('estimation_backend_manday', 0.0)),
            'estimation_frontend_manday': float(task.get('estimation_frontend_manday', 0.0)),
            'estimation_qa_manday': float(task.get('estimation_qa_manday', 0.0)),
            'estimation_infra_manday': float(task.get('estimation_infra_manday', 0.0)),
            'confidence_level': float(task.get('confidence_level', 0.7)),
            'created_at': datetime.now().isoformat(),
            'validated': task.get('validated', False)
        }

        # Store complex fields as JSON strings
        if task.get('dependencies'):
            metadata['dependencies_json'] = json.dumps(task['dependencies'])
        if task.get('risk_factors'):
            metadata['risk_factors_json'] = json.dumps(task['risk_factors'])
        if task.get('assumptions'):
            metadata['assumptions_json'] = json.dumps(task['assumptions'])

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

        # Build where filter
        where_filter = {}
        if category:
            where_filter['category'] = category
        if role:
            where_filter['role'] = role
        if complexity:
            where_filter['complexity'] = complexity

        # Search
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_filter if where_filter else None
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

            # Show role-specific breakdown
            if task.get('estimation_backend_manday', 0) > 0:
                prompt_parts.append(f"  - Backend: {task.get('estimation_backend_manday', 0):.1f} mandays")
            if task.get('estimation_frontend_manday', 0) > 0:
                prompt_parts.append(f"  - Frontend: {task.get('estimation_frontend_manday', 0):.1f} mandays")
            if task.get('estimation_qa_manday', 0) > 0:
                prompt_parts.append(f"  - QA: {task.get('estimation_qa_manday', 0):.1f} mandays")
            if task.get('estimation_infra_manday', 0) > 0:
                prompt_parts.append(f"  - Infra: {task.get('estimation_infra_manday', 0):.1f} mandays")

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


# Singleton instance
_history_manager_instance = None

def get_history_manager() -> EstimationHistoryManager:
    """Get or create singleton EstimationHistoryManager instance"""
    global _history_manager_instance
    if _history_manager_instance is None:
        _history_manager_instance = EstimationHistoryManager()
    return _history_manager_instance
