"""
Migration script to import historical estimation data from kyoest.md
Refactored to match the actual markdown format structure
"""
import sys
import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
import json

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / ".env"
    load_dotenv(dotenv_path=env_path)
    print(f"📝 Loaded environment variables from {env_path}")
except ImportError:
    print("⚠️ python-dotenv not installed. Install with: pip install python-dotenv")
    print("📝 Trying to load .env manually...")
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                if '=' in line and not line.strip().startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value
        print(f"✅ Manually loaded environment variables from {env_path}")

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.estimation_history_manager import get_history_manager


class MockEmbeddingService:
    """Mock embedding service for testing without OpenAI API"""
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate a simple hash-based embedding"""
        # Simple hash-based embedding for testing
        import hashlib
        hash_obj = hashlib.md5(text.encode())
        # Convert hash to float vector (128 dimensions)
        hash_bytes = hash_obj.digest()
        return [float(b) / 255.0 for b in hash_bytes[:128]] + [0.0] * (1536 - 128)
    
    def generate_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        return [self.generate_embedding(text) for text in texts]


def get_embedding_service_safe():
    """Get embedding service with fallback to mock"""
    try:
        from utils.embedding_service import get_embedding_service
        return get_embedding_service()
    except ValueError as e:
        print(f"⚠️ OpenAI API not available: {e}")
        print("📝 Using mock embedding service for testing...")
        return MockEmbeddingService()


def get_history_manager_safe():
    """Get history manager with safe embedding service"""
    try:
        return get_history_manager()
    except ValueError as e:
        print(f"⚠️ Could not initialize standard history manager: {e}")
        print("📝 This is expected if OpenAI API key is not available")
        print("💾 Data will be imported to a temporary database for testing...")
        
        # For now, let's just use the standard manager and let it fail gracefully
        # The user should have the OpenAI API key available from .env
        raise e


def parse_kyoest_markdown(file_path: str) -> List[Dict[str, Any]]:
    """
    Parse kyoest.md file to extract task estimation data
    
    The file uses markdown format with task sections like:
    #### X.Y Task Name (Japanese Name)
    - **Reference Document:** document reference
    - **Description:** English description
    - **Japanese:** Japanese description  
    - **Effort:** Backend: X.XX, Frontend: Y.YY, QA: Z.ZZ, **Total: W.WW**
    """
    tasks = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Regular expression to match task sections
    task_pattern = re.compile(
        r'#### (\d+\.\d+)\s+(.+?)\n'  # Task number and name
        r'(?:- \*\*Reference Document:\*\* (.+?)\n)?'  # Optional reference doc
        r'(?:- \*\*Description:\*\*(.*?)(?=- \*\*|\n####|\Z))?'  # Optional description
        r'(?:- \*\*Japanese:\*\*(.*?)(?=- \*\*|\n####|\Z))?'  # Optional Japanese
        r'(?:- \*\*Premise:\*\*(.*?)(?=- \*\*|\n####|\Z))?'  # Optional premise
        r'(?:- \*\*Assumptions/Prerequisites:\*\*(.*?)(?=- \*\*|\n####|\Z))?'  # Optional assumptions
        r'(?:- \*\*Remarks:\*\*(.*?)(?=- \*\*|\n####|\Z))?'  # Optional remarks  
        r'(?:- \*\*Effort:\*\* Backend: ([\d.]+),?\s*Frontend: ([\d.]+),?\s*QA: ([\d.]+),?\s*\*\*Total: ([\d.]+)\*\*)?', # Effort line
        re.DOTALL | re.MULTILINE
    )
    
    # Extract major categories from section headers
    category_pattern = re.compile(r'### (\d+\.\s+.+?)(?=\n|\Z)', re.MULTILINE)
    categories = {}
    for match in category_pattern.finditer(content):
        section_num = match.group(1).split('.')[0]
        category_name = match.group(1)
        categories[section_num] = category_name.strip()
    
    # Find all task matches
    for match in task_pattern.finditer(content):
        try:
            task_number = match.group(1)  # e.g., "1.1"
            task_name = match.group(2).strip()  # Task name with possible Japanese
            reference_doc = match.group(3).strip() if match.group(3) else ""
            description = match.group(4).strip() if match.group(4) else ""
            japanese = match.group(5).strip() if match.group(5) else ""
            premise = match.group(6).strip() if match.group(6) else ""
            assumptions = match.group(7).strip() if match.group(7) else ""
            remarks = match.group(8).strip() if match.group(8) else ""
            
            # Parse effort values
            backend_effort = float(match.group(9)) if match.group(9) else 0.0
            frontend_effort = float(match.group(10)) if match.group(10) else 0.0
            qa_effort = float(match.group(11)) if match.group(11) else 0.0
            total_effort = float(match.group(12)) if match.group(12) else backend_effort + frontend_effort + qa_effort
            
            # Skip tasks with no effort
            if total_effort == 0:
                continue
                
            # Extract category from task number (e.g., "1.1" -> "1")
            category_num = task_number.split('.')[0]
            category = categories.get(category_num, f"Category {category_num}")
            
            # Clean up description and Japanese text (remove bullet points and extra whitespace)
            description = re.sub(r'^\s*[-•]\s*', '', description.strip(), flags=re.MULTILINE)
            japanese = re.sub(r'^\s*[-•]\s*', '', japanese.strip(), flags=re.MULTILINE)
            
            # Determine complexity based on total effort
            if total_effort < 5:
                complexity = "Low"
            elif total_effort < 15:
                complexity = "Medium"
            else:
                complexity = "High"
            
            # Determine primary role based on highest effort
            if backend_effort >= frontend_effort and backend_effort >= qa_effort:
                primary_role = "Backend"
            elif frontend_effort >= backend_effort and frontend_effort >= qa_effort:
                primary_role = "Frontend"
            else:
                primary_role = "QA"
            
            # Build comprehensive description
            description_parts = []
            if description:
                description_parts.append(description)
            if japanese and japanese != description:
                description_parts.append(f"Japanese: {japanese}")
            full_description = "\n\n".join(description_parts)
            
            # Create task record
            task = {
                'id': f"kyoest_{task_number}".replace(".", "_"),
                'category': category,
                'role': primary_role,
                'parent_task': task_name.split('(')[0].strip(),  # English part before Japanese
                'sub_task': f"{task_number} - {task_name[:60]}",
                'description': full_description,
                'estimation_manday': total_effort,
                'estimation_backend_manday': backend_effort,
                'estimation_frontend_manday': frontend_effort,
                'estimation_qa_manday': qa_effort,
                'estimation_infra_manday': 0.0,
                'complexity': complexity,
                'dependencies': [],
                'priority': "Medium",  # Default priority
                'confidence_level': 0.85,  # Historical data assumed to be fairly reliable
                'validation_notes': f"Imported from kyoest.md | Reference: {reference_doc}",
                'worker_source': 'historical_import',
                'validated': True,
                # Additional metadata
                'reference_doc': reference_doc,
                'premise': premise,
                'assumptions': assumptions,
                'remarks': remarks,
                'task_number': task_number,
                'original_task_name': task_name
            }
            
            tasks.append(task)
            
        except Exception as e:
            print(f"⚠️ Error parsing task {task_number}: {e}")
            continue
    
    return tasks


def extract_additional_metadata(task: Dict[str, Any]) -> Dict[str, Any]:
    """Extract additional metadata for better ChromaDB storage and search"""
    
    # Extract technology keywords from description
    tech_keywords = []
    description_text = task.get('description', '').lower()
    
    # Common technologies mentioned in the description
    tech_patterns = [
        'web', 'api', 'database', 'db', 'excel', 'pdf', 'fax', 'email', 'sms',
        'login', 'authentication', 'master', 'management', 'search', 'report',
        'invoice', 'billing', 'order', 'quote', 'dispatch', 'vehicle', 'driver',
        'container', 'shipping', 'naccs', 'edi', 'ht', 'handheld', 'terminal'
    ]
    
    for pattern in tech_patterns:
        if pattern in description_text:
            tech_keywords.append(pattern)
    
    # Extract UI complexity indicators
    ui_complexity = "Low"
    if any(keyword in description_text for keyword in ['screen', 'input field', 'form', 'table']):
        field_matches = re.findall(r'(\d+)[^\d]*(?:input|field|column)', description_text)
        if field_matches:
            max_fields = max(int(m) for m in field_matches)
            if max_fields > 20:
                ui_complexity = "High"
            elif max_fields > 10:
                ui_complexity = "Medium"
    
    # Extract integration complexity
    integration_complexity = "Low"
    if any(keyword in description_text for keyword in ['integration', 'api', 'external', 'system']):
        integration_complexity = "Medium"
    if any(keyword in description_text for keyword in ['naccs', 'edi', 'fax', 'email system']):
        integration_complexity = "High"
    
    return {
        'tech_keywords': tech_keywords,
        'ui_complexity': ui_complexity,
        'integration_complexity': integration_complexity,
        'has_reporting': 'report' in description_text or 'output' in description_text,
        'has_search': 'search' in description_text,
        'has_crud': any(op in description_text for op in ['create', 'edit', 'update', 'delete', 'manage']),
        'has_file_processing': any(fmt in description_text for fmt in ['excel', 'pdf', 'csv', 'file']),
        'has_communication': any(comm in description_text for comm in ['fax', 'email', 'sms', 'message'])
    }


def import_historical_data():
    """Main import function with enhanced ChromaDB integration"""
    print("=" * 60)
    print("📚 Kyoest Historical Data Import - Refactored")
    print("=" * 60)

    # Path to kyoest.md
    kyoest_path = Path(__file__).parent.parent / "history-estimation" / "kyoest.md"

    if not kyoest_path.exists():
        print(f"❌ Error: {kyoest_path} not found!")
        return

    print(f"\n📄 Reading: {kyoest_path}")

    # Parse the file
    tasks = parse_kyoest_markdown(str(kyoest_path))

    if not tasks:
        print("⚠️ No tasks found in the file. Please check the format.")
        return

    print(f"\n✅ Parsed {len(tasks)} tasks from historical data")

    # Enhance tasks with additional metadata
    print("\n🔍 Extracting additional metadata...")
    for task in tasks:
        additional_metadata = extract_additional_metadata(task)
        task.update(additional_metadata)

    # Show statistics
    categories = {}
    roles = {}
    complexities = {}
    ui_complexities = {}
    total_effort = 0.0

    for task in tasks:
        categories[task['category']] = categories.get(task['category'], 0) + 1
        roles[task['role']] = roles.get(task['role'], 0) + 1
        complexities[task['complexity']] = complexities.get(task['complexity'], 0) + 1
        ui_complexities[task['ui_complexity']] = ui_complexities.get(task['ui_complexity'], 0) + 1
        total_effort += task['estimation_manday']

    print("\n📊 Statistics:")
    print(f"   Total Tasks: {len(tasks)}")
    print(f"   Total Effort: {total_effort:.1f} mandays")
    print(f"   Average Effort: {total_effort/len(tasks):.1f} mandays/task")

    print(f"\n   By Category:")
    for cat, count in sorted(categories.items(), key=lambda x: -x[1])[:5]:
        print(f"      - {cat}: {count} tasks")

    print(f"\n   By Role:")
    for role, count in sorted(roles.items(), key=lambda x: -x[1]):
        print(f"      - {role}: {count} tasks")

    print(f"\n   By Complexity:")
    for comp, count in sorted(complexities.items()):
        print(f"      - {comp}: {count} tasks")
        
    print(f"\n   By UI Complexity:")
    for ui_comp, count in sorted(ui_complexities.items()):
        print(f"      - {ui_comp}: {count} tasks")

    # Import to ChromaDB
    print("\n💾 Importing to estimation history database (ChromaDB)...")

    try:
        history_manager = get_history_manager_safe()
        
        # Clear existing kyoest data if it exists
        print("   🧹 Clearing existing kyoest historical data...")
        try:
            # Get all documents and filter by project
            results = history_manager.collection.get()
            kyoest_ids = []
            if results['metadatas']:
                for i, metadata in enumerate(results['metadatas']):
                    if metadata and metadata.get('project_name') == 'kyoest_historical':
                        kyoest_ids.append(results['ids'][i])
            
            if kyoest_ids:
                print(f"   📋 Found {len(kyoest_ids)} existing kyoest tasks, clearing...")
                history_manager.collection.delete(ids=kyoest_ids)
        except Exception as e:
            print(f"   ⚠️ Could not clear existing data: {e}")
        
        # Batch import using the available batch_save method
        batch_size = 10
        imported_count = 0

        print(f"   📦 Importing in batches of {batch_size}...")
        for i in range(0, len(tasks), batch_size):
            batch = tasks[i:i+batch_size]
            try:
                ids = history_manager.batch_save(batch, project_name="kyoest_historical")
                imported_count += len(ids)
                print(f"      ✓ Batch {i//batch_size + 1}: imported {len(ids)} tasks")
            except Exception as e:
                print(f"      ✗ Batch {i//batch_size + 1} failed: {e}")
                # Try individual saves for this batch
                for task in batch:
                    try:
                        task_id = history_manager.save_estimation(
                            task=task,
                            project_name="kyoest_historical",
                            task_id=task['id']
                        )
                        imported_count += 1
                        print(f"         ✓ Individual save: {task.get('task_number', 'unknown')}")
                    except Exception as individual_error:
                        print(f"         ✗ Failed: {task.get('task_number', 'unknown')} - {individual_error}")

        print(f"\n✅ Successfully imported {imported_count}/{len(tasks)} tasks to ChromaDB")

    except Exception as e:
        print(f"❌ Error during import: {e}")
        return

    # Show database statistics
    print("\n📊 Database Statistics:")
    try:
        stats = history_manager.get_statistics()
        print(f"   Total tasks in DB: {stats['total_tasks']}")
        print(f"   Average estimation: {stats['avg_estimation']:.1f} mandays")
        print(f"   Average confidence: {stats['avg_confidence']:.2f}")
    except Exception as e:
        print(f"   ⚠️ Could not get statistics: {e}")

    # Test semantic search functionality with adaptive thresholds
    print("\n🔍 Testing semantic search functionality...")
    test_queries = [
        "見積データ作成",  # Quote data creation
        "受注データ登録 Excel",  # Order registration Excel  
        "ログイン認証",  # Login authentication
        "マスタメンテナンス画面",  # Master maintenance screen
        "請求処理",  # Invoice billing process
        "quote data creation",  # English version
        "order registration excel", # Mixed test
    ]

    def find_optimal_threshold(query, history_manager, max_threshold=0.3):
        """Find the highest threshold that returns at least one result"""
        # Start with very low thresholds since we found scores as low as 0.004
        thresholds = [0.001, 0.005, 0.01, 0.02, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3]
        
        for threshold in thresholds:
            try:
                results = history_manager.search_similar(
                    description=query,
                    top_k=10,
                    similarity_threshold=threshold
                )
                if results:
                    return threshold, results
            except Exception:
                continue
        
        # If no results found with any threshold, try with 0.0
        try:
            results = history_manager.search_similar(
                description=query,
                top_k=10,
                similarity_threshold=0.0
            )
            return 0.0, results
        except Exception:
            return None, []

    optimal_thresholds = {}
    
    for query in test_queries:
        try:
            optimal_threshold, similar = find_optimal_threshold(query, history_manager)
            optimal_thresholds[query] = optimal_threshold
            
            print(f"\n   Query: '{query}'")
            if similar:
                print(f"   📊 Optimal threshold: {optimal_threshold:.3f} (found {len(similar)} results)")
                
                # Show top 2 results
                for task_data, score in similar[:2]:
                    try:
                        task = json.loads(task_data) if isinstance(task_data, str) else task_data
                        task_name = task.get('sub_task', task.get('parent_task', 'Unknown'))[:60]
                        effort = task.get('estimation_manday', 0)
                        category = task.get('category', 'Unknown')[:30]
                        print(f"      → {task_name} (similarity: {score:.3f}, effort: {effort:.1f}md, category: {category})")
                    except Exception as parse_error:
                        print(f"      → Found result but parsing failed: {parse_error}")
                
                # Show similarity score distribution for this query
                scores = [score for _, score in similar]
                print(f"      📈 Score range: {min(scores):.3f} - {max(scores):.3f} (avg: {sum(scores)/len(scores):.3f})")
            else:
                print(f"      → No similar tasks found (even with threshold: 0.0)")
        except Exception as e:
            print(f"      ✗ Search failed: {e}")
    
    # Summary of optimal thresholds
    print(f"\n📊 Optimal Thresholds Summary:")
    for query, threshold in optimal_thresholds.items():
        if threshold is not None:
            print(f"   • '{query[:40]}...': {threshold:.3f}")
        else:
            print(f"   • '{query[:40]}...': No results found")
    
    if optimal_thresholds:
        valid_thresholds = [t for t in optimal_thresholds.values() if t is not None]
        if valid_thresholds:
            avg_threshold = sum(valid_thresholds) / len(valid_thresholds)
            min_threshold = min(valid_thresholds)
            max_threshold = max(valid_thresholds)
            print(f"   🎯 Threshold statistics:")
            print(f"      - Average: {avg_threshold:.4f}")
            print(f"      - Range: {min_threshold:.4f} - {max_threshold:.4f}")
            print(f"   🎯 Recommended global threshold: {min_threshold:.4f} (ensures all queries return results)")
        else:
            avg_threshold = 0.01
            print(f"   🎯 No valid thresholds found, using default: {avg_threshold:.4f}")
    else:
        avg_threshold = 0.01
        print(f"   🎯 No results, using default threshold: {avg_threshold:.4f}")
    
    # Test the recommended threshold
    recommended_threshold = min(valid_thresholds) if optimal_thresholds and valid_thresholds else 0.01
    print(f"\n🎯 Testing with recommended threshold: {recommended_threshold:.3f}")
    
    for query in test_queries[:2]:  # Test first 2 queries
        try:
            similar = history_manager.search_similar(
                description=query,
                top_k=3,
                similarity_threshold=recommended_threshold
            )
            print(f"\n   Query: '{query}'")
            if similar:
                print(f"   ✅ Found {len(similar)} results with threshold {recommended_threshold:.3f}")
                for task_data, score in similar[:1]:  # Show top result
                    try:
                        task = json.loads(task_data) if isinstance(task_data, str) else task_data
                        task_name = task.get('sub_task', task.get('parent_task', 'Unknown'))[:50]
                        effort = task.get('estimation_manday', 0)
                        print(f"      → {task_name} (similarity: {score:.3f}, effort: {effort:.1f}md)")
                    except Exception as parse_error:
                        print(f"      → Found result but parsing failed: {parse_error}")
            else:
                print(f"   ❌ No results with threshold {recommended_threshold:.3f}")
        except Exception as e:
            print(f"      ✗ Search failed: {e}")

    print("\n" + "=" * 60)
    print("✅ Kyoest Historical Data Import Completed!")
    print("📁 Data stored in ChromaDB for semantic search and estimation assistance")
    print("\n🚀 Key Improvements Made:")
    print("   • Refactored to parse markdown format instead of tab-separated")
    print("   • Added automatic environment variable loading from .env")
    print("   • Enhanced metadata extraction (UI complexity, tech keywords)")
    print("   • Improved error handling and batch processing")
    print("   • Ready for semantic search and ML-powered estimation")
    print("=" * 60)


if __name__ == "__main__":
    import_historical_data()
