"""
Enhanced Estimation Workflow using LangGraph Orchestrator-Worker Pattern
=======================================================================

Kiến trúc mới với 3 workers chuyên biệt:
1. Worker 1: Task Breakdown với GraphRAG integration
2. Worker 2: Estimation Worker cho effort calculation
3. Worker 3: Effort Calculator & Validator với validation logic

Tích hợp với GraphRAG handler từ app.py để phân tích thông minh hơn.

Author: AI Assistant
Date: 2025-09-28
"""

import os
import json
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, TypedDict, Annotated
import operator
from dataclasses import dataclass, field
import uuid

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send
from langgraph.checkpoint.memory import MemorySaver

# ========================
# Enhanced Data Models
# ========================

@dataclass
class TaskBreakdown:
    """Enhanced model cho việc break task với validation"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    category: str = ""
    parent_task: str = ""
    sub_task: str = ""
    description: str = ""
    estimation_manday: float = 0.0
    complexity: str = "Medium"  # Low, Medium, High
    dependencies: List[str] = field(default_factory=list)
    priority: str = "Medium"  # Low, Medium, High
    confidence_level: float = 0.8  # 0.0 - 1.0
    validation_notes: str = ""
    worker_source: str = ""  # Which worker created this

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'category': self.category,
            'parent_task': self.parent_task,
            'sub_task': self.sub_task,
            'description': self.description,
            'estimation_manday': self.estimation_manday,
            'complexity': self.complexity,
            'dependencies': self.dependencies,
            'priority': self.priority,
            'confidence_level': self.confidence_level,
            'validation_notes': self.validation_notes,
            'worker_source': self.worker_source
        }

@dataclass
class GraphRAGInsight:
    """Model để lưu insights từ GraphRAG"""
    query: str
    response: str
    references: List[str]
    timestamp: str
    confidence: float = 0.8

# ========================
# Enhanced State Definitions
# ========================

class EnhancedOrchestratorState(TypedDict):
    """Enhanced state cho Orchestrator với GraphRAG integration"""
    original_task: str  # Task gốc từ user
    graphrag_insights: List[Dict[str, Any]]  # Insights từ GraphRAG queries

    # Category planning
    main_categories: List[str]  # Các category chính

    # Worker results với consistent annotations
    breakdown_results: Annotated[List[Dict[str, Any]], operator.add]  # Kết quả từ Worker 1
    estimation_results: Annotated[List[Dict[str, Any]], operator.add]  # Kết quả từ Worker 2
    validated_results: Annotated[List[Dict[str, Any]], operator.add]  # Kết quả từ Worker 3

    # Final outputs
    final_estimation_data: List[Dict[str, Any]]  # Final serializable data
    total_effort: float  # Tổng effort (manday)
    total_confidence: float  # Confidence score trung bình
    mermaid_diagram: str  # Mermaid code cho visualization
    validation_summary: Dict[str, Any]  # Summary của validation process
    workflow_status: str  # Trạng thái workflow

# ========================
# Enhanced LLM Configuration
# ========================

class EnhancedEstimationLLM:
    """Enhanced LLM wrapper với prompts chuyên biệt cho từng worker"""

    def __init__(self, model_name: str = "gpt-4o-mini"):
        self.llm = ChatOpenAI(
            model=model_name,
            temperature=0.1,
            max_tokens=3000
        )

    def get_orchestrator_prompt(self) -> str:
        return """
        Bạn là một Senior Project Manager với 15 năm kinh nghiệm trong việc phân tích và breakdown các dự án phần mềm phức tạp.

        Nhiệm vụ của bạn:
        1. Phân tích task được cung cấp với context từ GraphRAG
        2. Xác định các category chính cần cho dự án
        3. Tạo chiến lược để breakdown task một cách toàn diện
        4. Chuẩn bị input cho các workers chuyên biệt

        Bạn sẽ có thông tin từ GraphRAG để hiểu rõ hơn về context và requirements.

        Trả về kết quả dưới dạng JSON với format:
        {
            "categories": ["Frontend", "Backend", "Database", "DevOps", "Testing", "Documentation"],
            "analysis_strategy": "Chiến lược phân tích tổng thể",
            "complexity_assessment": "Low/Medium/High",
            "estimated_timeline": "Ước tính thời gian tổng thể"
        }
        """

    def get_breakdown_worker_prompt(self) -> str:
        return """
        Bạn là một Technical Lead chuyên gia trong việc break down technical requirements thành các task cụ thể.

        Nhiệm vụ của bạn:
        1. Sử dụng thông tin từ GraphRAG để hiểu sâu về requirements
        2. Break down category được giao thành parent tasks và sub tasks
        3. Tạo description chi tiết cho mỗi task
        4. Xác định dependencies và priority

        Nguyên tắc breakdown:
        - Mỗi sub-task phải có scope rõ ràng và có thể estimate được
        - Task size lý tưởng: 0.5-3 mandays cho middle developer
        - Xem xét dependencies giữa các task
        - Ưu tiên các task critical path

        Trả về kết quả dưới dạng JSON với format:
        {
            "breakdown": [
                {
                    "id": "unique_id",
                    "category": "category_name",
                    "parent_task": "Parent Task Name",
                    "sub_task": "Specific Sub Task",
                    "description": "Detailed description",
                    "complexity": "Low/Medium/High",
                    "dependencies": ["task_id_1", "task_id_2"],
                    "priority": "Low/Medium/High",
                    "notes": "Additional technical notes"
                }
            ]
        }
        """

    def get_estimation_worker_prompt(self) -> str:
        return """
        Bạn là một Senior Developer với 8 năm kinh nghiệm, chuyên gia trong việc estimation effort cho các dự án phần mềm.

        Nhiệm vụ của bạn:
        1. Phân tích từng sub-task được cung cấp
        2. Estimate effort dựa trên middle developer (3 năm kinh nghiệm)
        3. Tính toán effort với unit là manday (7 giờ/ngày)
        4. Đánh giá confidence level của estimation

        Tiêu chuẩn estimation cho middle developer (3 năm kinh nghiệm):
        - Simple CRUD operations: 0.5-1 manday
        - Complex business logic: 1-3 manday
        - API integration (simple): 0.5-1.5 manday
        - API integration (complex): 1.5-3 manday
        - UI components (basic): 0.5-1 manday
        - UI components (complex/responsive): 1-2.5 manday
        - Database design/migration: 0.5-2 manday
        - Authentication/Authorization: 1-2 manday
        - Unit testing: 20-30% của development effort
        - Integration testing: 10-20% của development effort
        - Documentation: 10-15% của development effort

        Factors ảnh hưởng đến estimation:
        - Complexity: Low (-20%), Medium (baseline), High (+50%)
        - Dependencies: Nhiều dependencies (+20-30%)
        - Risk level: High risk (+30-50%)

        Trả về kết quả dưới dạng JSON với format:
        {
            "estimation": {
                "id": "task_id",
                "estimation_manday": 2.5,
                "confidence_level": 0.8,
                "breakdown": {
                    "development": 2.0,
                    "testing": 0.3,
                    "documentation": 0.2
                },
                "risk_factors": ["dependency on external API", "new technology"],
                "assumptions": ["team has basic React knowledge", "APIs are well documented"]
            }
        }
        """

    def get_validation_worker_prompt(self) -> str:
        return """
        Bạn là một Project Manager với chuyên môn sâu về quality assurance và risk management.

        Nhiệm vụ của bạn:
        1. Validate các estimations từ Estimation Worker
        2. Cross-check logic và consistency
        3. Áp dụng buffer cho risk mitigation
        4. Đảm bảo total effort hợp lý

        Validation criteria:
        - Consistency check: So sánh với các task tương tự
        - Dependency validation: Đảm bảo dependencies được tính đúng
        - Risk assessment: Đánh giá và apply buffer cho high-risk tasks
        - Team capacity: Xem xét realistic capacity của team
        - Buffer calculation: 10-20% cho các task có risk

        Adjustment rules:
        - Low complexity, low risk: Không adjust
        - Medium complexity/risk: +10% buffer
        - High complexity/risk: +20% buffer
        - Critical path tasks: +15% buffer
        - New technology/framework: +25% buffer

        Trả về kết quả dưới dạng JSON với format:
        {
            "validation": {
                "id": "task_id",
                "original_estimation": 2.5,
                "validated_estimation": 2.8,
                "adjustment_reason": "Added 15% buffer for dependency risk",
                "confidence_level": 0.85,
                "validation_notes": "Estimation appears reasonable, added buffer for external dependencies",
                "risk_mitigation": ["parallel development of dependent tasks", "early API integration testing"]
            }
        }
        """

# ========================
# Enhanced Orchestrator Node
# ========================

def enhanced_orchestrator_node(state: EnhancedOrchestratorState) -> Dict[str, Any]:
    """
    Enhanced Orchestrator với GraphRAG integration
    """
    print(f"🎯 Enhanced Orchestrator đang phân tích task: {state['original_task']}")

    llm_handler = EnhancedEstimationLLM()

    # Sử dụng pre-fetched GraphRAG insights từ state
    graphrag_insights = state.get('graphrag_insights', [])
    if graphrag_insights:
        print(f"📊 Đang sử dụng {len(graphrag_insights)} GraphRAG insights có sẵn...")
    else:
        print("⚠️ Không có GraphRAG insights, sử dụng analysis cơ bản")

    # Tạo context từ GraphRAG insights
    graphrag_context = ""
    if graphrag_insights:
        graphrag_context = "\n\nContext từ GraphRAG:\n"
        for insight in graphrag_insights:
            graphrag_context += f"Q: {insight['query']}\nA: {insight['response']}\n---\n"

    # Tạo prompt cho Orchestrator
    messages = [
        SystemMessage(content=llm_handler.get_orchestrator_prompt()),
        HumanMessage(content=f"""
        Task cần phân tích và estimation:
        {state['original_task']}

        {graphrag_context}

        Dựa trên task và context từ GraphRAG, hãy phân tích và đưa ra chiến lược breakdown.
        """)
    ]

    try:
        response = llm_handler.llm.invoke(messages)

        # Parse JSON response
        import re
        json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())

            categories = result.get('categories', [])

            print(f"✅ Orchestrator đã phân tích: {len(categories)} categories")
            print(f"📈 Complexity: {result.get('complexity_assessment', 'Unknown')}")

            return {
                'main_categories': categories,
                'graphrag_insights': graphrag_insights,
                'workflow_status': 'orchestrator_completed'
            }
        else:
            raise ValueError("Không thể parse JSON response từ Orchestrator")

    except Exception as e:
        print(f"❌ Lỗi trong Enhanced Orchestrator: {e}")
        return {
            'main_categories': [],
            'graphrag_insights': graphrag_insights,
            'workflow_status': 'orchestrator_failed'
        }

# ========================
# Worker 1: Task Breakdown với GraphRAG
# ========================

def task_breakdown_worker(worker_input) -> Dict[str, Any]:
    """
    Worker 1: Chuyên break down task với GraphRAG integration
    Receives data via Send() mechanism
    """
    # Extract data from worker input
    category_focus = worker_input.get('category_focus', 'General')
    original_task = worker_input.get('original_task', '')

    print(f"👷‍♂️ Worker 1 (Task Breakdown) đang xử lý category: {category_focus}")

    llm_handler = EnhancedEstimationLLM()

    # Note: GraphRAG insights are already available in the orchestrator state
    # and used for overall project understanding. No additional GraphRAG calls needed here.
    category_context = f"\nCategory focus: {category_focus}\n"

    messages = [
        SystemMessage(content=llm_handler.get_breakdown_worker_prompt()),
        HumanMessage(content=f"""
        Original Task: {original_task}
        Category Focus: {category_focus}

        {category_context}

        Hãy break down category '{category_focus}' thành các task cụ thể với description chi tiết.
        """)
    ]

    try:
        response = llm_handler.llm.invoke(messages)

        # Parse JSON response
        import re
        json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            breakdown_tasks = result.get('breakdown', [])

            # Add worker source info
            for task in breakdown_tasks:
                task['worker_source'] = 'task_breakdown_worker'
                task['confidence_level'] = 0.8  # Default confidence từ breakdown

            print(f"✅ Worker 1 completed: {len(breakdown_tasks)} tasks cho {category_focus}")

            return {
                'breakdown_results': breakdown_tasks
            }
        else:
            raise ValueError("Không thể parse JSON response từ Breakdown Worker")

    except Exception as e:
        print(f"❌ Lỗi trong Task Breakdown Worker: {e}")
        return {
            'breakdown_results': []
        }

# ========================
# Worker 2: Estimation Worker
# ========================

def estimation_worker(worker_input) -> Dict[str, Any]:
    """
    Worker 2: Chuyên estimation effort cho các task
    Receives task_breakdown via Send() mechanism
    """
    # Extract task data from worker input
    task_breakdown = worker_input.get('task_breakdown', {})
    task_name = task_breakdown.get('sub_task', 'Unknown Task')

    print(f"👷‍♂️ Worker 2 (Estimation) đang estimate: {task_name}")

    llm_handler = EnhancedEstimationLLM()

    messages = [
        SystemMessage(content=llm_handler.get_estimation_worker_prompt()),
        HumanMessage(content=f"""
        Task cần estimation:
        - Category: {task_breakdown.get('category', '')}
        - Parent Task: {task_breakdown.get('parent_task', '')}
        - Sub Task: {task_breakdown.get('sub_task', '')}
        - Description: {task_breakdown.get('description', '')}
        - Complexity: {task_breakdown.get('complexity', 'Medium')}
        - Dependencies: {task_breakdown.get('dependencies', [])}
        - Priority: {task_breakdown.get('priority', 'Medium')}

        Hãy estimate effort cho middle developer (3 năm kinh nghiệm) với unit manday (7 giờ/ngày).
        """)
    ]

    try:
        response = llm_handler.llm.invoke(messages)

        # Parse JSON response
        import re
        json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            estimation_data = result.get('estimation', {})

            # Merge với original task data
            estimated_task = task_breakdown.copy()
            estimated_task.update({
                'estimation_manday': estimation_data.get('estimation_manday', 0),
                'confidence_level': estimation_data.get('confidence_level', 0.7),
                'estimation_breakdown': estimation_data.get('breakdown', {}),
                'risk_factors': estimation_data.get('risk_factors', []),
                'assumptions': estimation_data.get('assumptions', []),
                'worker_source': 'estimation_worker'
            })

            print(f"✅ Worker 2 estimated: {estimation_data.get('estimation_manday', 0):.1f} mandays")

            return {
                'estimation_results': [estimated_task]
            }
        else:
            raise ValueError("Không thể parse JSON response từ Estimation Worker")

    except Exception as e:
        print(f"❌ Lỗi trong Estimation Worker: {e}")
        # Return task với default estimation
        fallback_task = task_breakdown.copy() if task_breakdown else {}
        fallback_task.update({
            'estimation_manday': 1.0,  # Default fallback
            'confidence_level': 0.5,
            'worker_source': 'estimation_worker_fallback'
        })
        return {
            'estimation_results': [fallback_task]
        }

# ========================
# Worker 3: Effort Calculator & Validator
# ========================

def validation_worker(worker_input) -> Dict[str, Any]:
    """
    Worker 3: Validation và calculation với risk mitigation
    Receives estimation_task via Send() mechanism
    """
    # Extract estimation task from worker input
    estimation_task = worker_input.get('estimation_task', {})
    task_name = estimation_task.get('sub_task', 'Unknown Task')

    print(f"👷‍♂️ Worker 3 (Validation) đang validate: {task_name}")

    llm_handler = EnhancedEstimationLLM()

    messages = [
        SystemMessage(content=llm_handler.get_validation_worker_prompt()),
        HumanMessage(content=f"""
        Task cần validation:
        - ID: {estimation_task.get('id', '')}
        - Category: {estimation_task.get('category', '')}
        - Sub Task: {estimation_task.get('sub_task', '')}
        - Description: {estimation_task.get('description', '')}
        - Original Estimation: {estimation_task.get('estimation_manday', 0)} mandays
        - Complexity: {estimation_task.get('complexity', 'Medium')}
        - Dependencies: {estimation_task.get('dependencies', [])}
        - Risk Factors: {estimation_task.get('risk_factors', [])}
        - Confidence Level: {estimation_task.get('confidence_level', 0.7)}

        Hãy validate estimation này và apply buffer nếu cần thiết.
        """)
    ]

    try:
        response = llm_handler.llm.invoke(messages)

        # Parse JSON response
        import re
        json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            validation_data = result.get('validation', {})

            # Create final validated task
            validated_task = estimation_task.copy()
            validated_task.update({
                'estimation_manday': validation_data.get('validated_estimation', estimation_task.get('estimation_manday', 0)),
                'original_estimation': validation_data.get('original_estimation', estimation_task.get('estimation_manday', 0)),
                'confidence_level': validation_data.get('confidence_level', estimation_task.get('confidence_level', 0.7)),
                'validation_notes': validation_data.get('validation_notes', ''),
                'adjustment_reason': validation_data.get('adjustment_reason', ''),
                'risk_mitigation': validation_data.get('risk_mitigation', []),
                'worker_source': 'validation_worker'
            })

            print(f"✅ Worker 3 validated: {validation_data.get('original_estimation', 0):.1f} → {validation_data.get('validated_estimation', 0):.1f} mandays")

            return {
                'validated_results': [validated_task]
            }
        else:
            raise ValueError("Không thể parse JSON response từ Validation Worker")

    except Exception as e:
        print(f"❌ Lỗi trong Validation Worker: {e}")
        # Return task với minimal validation
        fallback_task = estimation_task.copy() if estimation_task else {}
        fallback_task.update({
            'validation_notes': f'Validation failed, using original estimation: {e}',
            'worker_source': 'validation_worker_fallback'
        })
        return {
            'validated_results': [fallback_task]
        }

# ========================
# Assignment Functions
# ========================

def assign_breakdown_workers(state: EnhancedOrchestratorState) -> List[Send]:
    """
    Phân công breakdown workers cho mỗi category
    """
    categories = state.get('main_categories', [])
    print(f"📋 Đang phân công breakdown workers cho {len(categories)} categories")

    sends = []
    for category in categories:
        send = Send(
            "task_breakdown_worker",
            {
                "category_focus": category,
                "original_task": state['original_task']
            }
        )
        sends.append(send)

    return sends

def assign_estimation_workers(state: EnhancedOrchestratorState) -> List[Send]:
    """
    Phân công estimation workers cho mỗi breakdown task
    """
    breakdown_results = state.get('breakdown_results', [])
    print(f"📋 Đang phân công estimation workers cho {len(breakdown_results)} tasks")

    sends = []
    for task_breakdown in breakdown_results:
        send = Send(
            "estimation_worker",
            {
                "task_breakdown": task_breakdown
            }
        )
        sends.append(send)

    return sends

def assign_validation_workers(state: EnhancedOrchestratorState) -> List[Send]:
    """
    Phân công validation workers cho mỗi estimation task
    """
    estimation_results = state.get('estimation_results', [])
    print(f"📋 Đang phân công validation workers cho {len(estimation_results)} tasks")

    sends = []
    for estimation_task in estimation_results:
        send = Send(
            "validation_worker",
            {
                "estimation_task": estimation_task
            }
        )
        sends.append(send)

    return sends

# ========================
# Enhanced Synthesizer Node
# ========================

def enhanced_synthesizer_node(state: EnhancedOrchestratorState) -> Dict[str, Any]:
    """
    Enhanced Synthesizer với advanced features
    """
    print("🔄 Enhanced Synthesizer đang tổng hợp kết quả...")

    validated_results = state.get('validated_results', [])

    if not validated_results:
        print("⚠️ Không có validated results từ workers")
        return {
            'final_estimation_data': [],
            'total_effort': 0.0,
            'total_confidence': 0.0,
            'validation_summary': {},
            'workflow_status': 'no_results'
        }

    # Tính toán summary statistics
    total_effort = sum(task.get('estimation_manday', 0) for task in validated_results)
    total_confidence = sum(task.get('confidence_level', 0) for task in validated_results) / len(validated_results)

    # Tạo validation summary
    validation_summary = {
        'total_tasks': len(validated_results),
        'total_effort_mandays': total_effort,
        'average_confidence': total_confidence,
        'categories_covered': list(set(task.get('category', 'Unknown') for task in validated_results)),
        'complexity_distribution': {},
        'risk_analysis': {
            'high_risk_tasks': [],
            'medium_risk_tasks': [],
            'low_risk_tasks': []
        },
        'adjustment_summary': {
            'tasks_adjusted': 0,
            'total_adjustment_mandays': 0,
            'adjustment_percentage': 0
        }
    }

    # Analyze complexity distribution
    complexity_counts = {}
    for task in validated_results:
        complexity = task.get('complexity', 'Medium')
        complexity_counts[complexity] = complexity_counts.get(complexity, 0) + 1
    validation_summary['complexity_distribution'] = complexity_counts

    # Analyze risk factors
    for task in validated_results:
        risk_factors = task.get('risk_factors', [])
        confidence = task.get('confidence_level', 0.8)

        if len(risk_factors) > 2 or confidence < 0.6:
            validation_summary['risk_analysis']['high_risk_tasks'].append({
                'task': task.get('sub_task', ''),
                'risks': risk_factors,
                'confidence': confidence
            })
        elif len(risk_factors) > 0 or confidence < 0.8:
            validation_summary['risk_analysis']['medium_risk_tasks'].append({
                'task': task.get('sub_task', ''),
                'risks': risk_factors,
                'confidence': confidence
            })
        else:
            validation_summary['risk_analysis']['low_risk_tasks'].append({
                'task': task.get('sub_task', ''),
                'confidence': confidence
            })

    # Calculate adjustment summary
    adjusted_tasks = 0
    total_adjustment = 0
    for task in validated_results:
        original_est = task.get('original_estimation', task.get('estimation_manday', 0))
        final_est = task.get('estimation_manday', 0)
        if abs(original_est - final_est) > 0.1:
            adjusted_tasks += 1
            total_adjustment += (final_est - original_est)

    validation_summary['adjustment_summary'] = {
        'tasks_adjusted': adjusted_tasks,
        'total_adjustment_mandays': total_adjustment,
        'adjustment_percentage': (total_adjustment / total_effort * 100) if total_effort > 0 else 0
    }

    # Tạo enhanced mermaid diagram
    mermaid_diagram = create_enhanced_mermaid_diagram(validated_results, validation_summary)

    print(f"✅ Enhanced Synthesizer hoàn thành:")
    print(f"   - {len(validated_results)} tasks")
    print(f"   - {total_effort:.1f} mandays total")
    print(f"   - {total_confidence:.2f} average confidence")
    print(f"   - {adjusted_tasks} tasks adjusted")

    return {
        'final_estimation_data': validated_results,
        'total_effort': total_effort,
        'total_confidence': total_confidence,
        'mermaid_diagram': mermaid_diagram,
        'validation_summary': validation_summary,
        'workflow_status': 'completed'
    }

# ========================
# Enhanced Mermaid Diagram Generator
# ========================

def create_enhanced_mermaid_diagram(validated_results: List[Dict[str, Any]], validation_summary: Dict[str, Any]) -> str:
    """
    Tạo enhanced mermaid diagram với dependencies và risk indicators
    """
    # Extract summary info
    total_tasks = validation_summary.get('total_tasks', len(validated_results))
    total_effort = validation_summary.get('total_effort', 0)
    avg_confidence = validation_summary.get('average_confidence', 0)

    mermaid_code = f"""
graph TD
    A[Original Task] --> B[GraphRAG Analysis]
    B --> C[Task Breakdown]
    C --> D[Estimation]
    D --> E[Validation]
    E --> F["Final Results<br/>Tasks: {total_tasks}<br/>Total: {total_effort:.1f} days<br/>Confidence: {avg_confidence:.0%}"]

    %% Categories and Tasks
"""

    # Group by category
    categories = {}
    for task in validated_results:
        category = task.get('category', 'Unknown')
        if category not in categories:
            categories[category] = []
        categories[category].append(task)

    # Add categories and tasks
    for i, (category, tasks) in enumerate(categories.items()):
        cat_id = f"CAT{i}"
        total_effort = sum(task.get('estimation_manday', 0) for task in tasks)
        mermaid_code += f"    C --> {cat_id}[\"{category}<br/>{total_effort:.1f} days\"]\\n"

        # Add tasks for each category
        for j, task in enumerate(tasks):
            task_id = f"T{i}_{j}"
            task_name = task.get('sub_task', 'Unknown Task')
            effort = task.get('estimation_manday', 0)
            confidence = task.get('confidence_level', 0)

            # Style based on risk/confidence
            if confidence < 0.6:
                style_class = "high-risk"
            elif confidence < 0.8:
                style_class = "medium-risk"
            else:
                style_class = "low-risk"

            mermaid_code += f"    {cat_id} --> {task_id}[\\\"{task_name}<br/>{effort:.1f}d ({confidence:.0%})\\\"]\\n"
            mermaid_code += f"    class {task_id} {style_class}\\n"

    # Add dependency arrows if they exist
    mermaid_code += "\n    %% Dependencies\\n"
    task_id_map = {}
    for i, (category, tasks) in enumerate(categories.items()):
        for j, task in enumerate(tasks):
            task_id_map[task.get('id', '')] = f"T{i}_{j}"

    for i, (category, tasks) in enumerate(categories.items()):
        for j, task in enumerate(tasks):
            dependencies = task.get('dependencies', [])
            current_task_id = f"T{i}_{j}"
            for dep_id in dependencies:
                if dep_id in task_id_map:
                    dep_task_id = task_id_map[dep_id]
                    mermaid_code += f"    {dep_task_id} -.-> {current_task_id}\\n"

    # Add styling
    mermaid_code += """

    %% Styling
    classDef high-risk fill:#ffebee,stroke:#f44336,stroke-width:2px
    classDef medium-risk fill:#fff3e0,stroke:#ff9800,stroke-width:2px
    classDef low-risk fill:#e8f5e8,stroke:#4caf50,stroke-width:2px
"""

    return mermaid_code

# ========================
# Enhanced Excel Export Function
# ========================

def export_enhanced_excel(df: pd.DataFrame, validation_summary: Dict[str, Any], filename: str = None) -> str:
    """
    Enhanced Excel export với detailed analysis
    """
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"enhanced_estimation_{timestamp}.xlsx"

    filepath = os.path.join(os.getcwd(), filename)

    try:
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            # Main estimation table với enhanced columns
            estimation_columns = [
                'id', 'category', 'parent_task', 'sub_task', 'description',
                'estimation_manday', 'original_estimation', 'confidence_level',
                'complexity', 'priority', 'worker_source', 'validation_notes',
                'adjustment_reason', 'dependencies', 'risk_factors', 'assumptions'
            ]

            # Filter columns that exist in DataFrame
            existing_columns = [col for col in estimation_columns if col in df.columns]
            df_filtered = df[existing_columns]
            df_filtered.to_excel(writer, sheet_name='Detailed Estimation', index=False)

            # Summary sheet
            summary_data = {
                'Metric': [
                    'Total Tasks',
                    'Total Effort (mandays)',
                    'Average Effort per Task',
                    'Average Confidence Level',
                    'Tasks Adjusted',
                    'Total Adjustment (mandays)',
                    'Adjustment Percentage',
                    'Generated Date'
                ],
                'Value': [
                    validation_summary.get('total_tasks', 0),
                    validation_summary.get('total_effort_mandays', 0),
                    validation_summary.get('total_effort_mandays', 0) / max(validation_summary.get('total_tasks', 1), 1),
                    validation_summary.get('average_confidence', 0),
                    validation_summary.get('adjustment_summary', {}).get('tasks_adjusted', 0),
                    validation_summary.get('adjustment_summary', {}).get('total_adjustment_mandays', 0),
                    f"{validation_summary.get('adjustment_summary', {}).get('adjustment_percentage', 0):.1f}%",
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ]
            }
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Executive Summary', index=False)

            # Category breakdown
            if 'category' in df.columns and 'estimation_manday' in df.columns:
                category_summary = df.groupby('category').agg({
                    'estimation_manday': ['count', 'sum', 'mean'],
                    'confidence_level': 'mean'
                }).round(2)
                category_summary.columns = ['Task Count', 'Total Effort', 'Average Effort', 'Average Confidence']
                category_summary = category_summary.reset_index()
                category_summary.to_excel(writer, sheet_name='Category Analysis', index=False)

            # Risk analysis sheet
            risk_data = []
            for risk_level in ['high_risk_tasks', 'medium_risk_tasks', 'low_risk_tasks']:
                for task in validation_summary.get('risk_analysis', {}).get(risk_level, []):
                    risk_data.append({
                        'Risk Level': risk_level.replace('_tasks', '').replace('_', ' ').title(),
                        'Task Name': task.get('task', ''),
                        'Confidence': task.get('confidence', 0),
                        'Risk Factors': ', '.join(task.get('risks', []))
                    })

            if risk_data:
                risk_df = pd.DataFrame(risk_data)
                risk_df.to_excel(writer, sheet_name='Risk Analysis', index=False)

            # Complexity distribution
            complexity_data = []
            for complexity, count in validation_summary.get('complexity_distribution', {}).items():
                complexity_data.append({
                    'Complexity Level': complexity,
                    'Task Count': count,
                    'Percentage': f"{count / validation_summary.get('total_tasks', 1) * 100:.1f}%"
                })

            if complexity_data:
                complexity_df = pd.DataFrame(complexity_data)
                complexity_df.to_excel(writer, sheet_name='Complexity Distribution', index=False)

        print(f"✅ Enhanced Excel export completed: {filepath}")
        return filepath

    except Exception as e:
        print(f"❌ Lỗi khi export Enhanced Excel: {e}")
        return ""

# ========================
# Enhanced Workflow Builder
# ========================

class EnhancedEstimationWorkflow:
    """
    Enhanced Estimation Workflow với specialized workers
    """

    def __init__(self):
        self.workflow = None
        self.memory = MemorySaver()
        self._build_workflow()

    def _build_workflow(self):
        """Build enhanced LangGraph workflow"""

        # Tạo StateGraph
        builder = StateGraph(EnhancedOrchestratorState)

        # Add nodes
        builder.add_node("enhanced_orchestrator", enhanced_orchestrator_node)
        builder.add_node("task_breakdown_worker", task_breakdown_worker)
        builder.add_node("estimation_worker", estimation_worker)
        builder.add_node("validation_worker", validation_worker)
        builder.add_node("enhanced_synthesizer", enhanced_synthesizer_node)

        # Add edges
        builder.add_edge(START, "enhanced_orchestrator")

        # Orchestrator -> Breakdown Workers
        builder.add_conditional_edges(
            "enhanced_orchestrator",
            assign_breakdown_workers,
            ["task_breakdown_worker"]
        )

        # Breakdown Workers -> Estimation Workers
        builder.add_conditional_edges(
            "task_breakdown_worker",
            assign_estimation_workers,
            ["estimation_worker"]
        )

        # Estimation Workers -> Validation Workers
        builder.add_conditional_edges(
            "estimation_worker",
            assign_validation_workers,
            ["validation_worker"]
        )

        # Validation Workers -> Synthesizer
        builder.add_edge("validation_worker", "enhanced_synthesizer")
        builder.add_edge("enhanced_synthesizer", END)

        # Compile workflow
        self.workflow = builder.compile(checkpointer=self.memory)

        print("✅ Enhanced Estimation Workflow đã được build thành công!")

    def run_estimation(self, task_description: str, graphrag_insights=None, thread_id: str = "enhanced_estimation_thread") -> Dict[str, Any]:
        """
        Chạy enhanced estimation workflow
        """
        print(f"🚀 Bắt đầu Enhanced Estimation Workflow cho task: {task_description}")

        initial_state = {
            "original_task": task_description,
            "graphrag_insights": graphrag_insights or [],
            "main_categories": [],
            "breakdown_results": [],
            "estimation_results": [],
            "validated_results": [],
            "final_estimation_data": [],
            "total_effort": 0.0,
            "total_confidence": 0.0,
            "mermaid_diagram": "",
            "validation_summary": {},
            "workflow_status": "started"
        }

        try:
            # Run workflow
            config = {"configurable": {"thread_id": thread_id}}
            result = self.workflow.invoke(initial_state, config=config)

            print(f"🎉 Enhanced Workflow hoàn thành với status: {result.get('workflow_status', 'unknown')}")

            return result

        except Exception as e:
            print(f"❌ Lỗi khi chạy Enhanced Workflow: {e}")
            return {
                "workflow_status": "failed",
                "error": str(e)
            }

    def export_results(self, result: Dict[str, Any], filename: str = None) -> str:
        """
        Enhanced export kết quả ra Excel
        """
        estimation_data = result.get('final_estimation_data', [])
        if not estimation_data:
            print("⚠️ Không có dữ liệu để export")
            return ""

        df = pd.DataFrame(estimation_data)
        validation_summary = result.get('validation_summary', {})
        return export_enhanced_excel(df, validation_summary, filename)

    def get_mermaid_diagram(self, result: Dict[str, Any]) -> str:
        """
        Lấy enhanced mermaid diagram từ kết quả
        """
        return result.get('mermaid_diagram', '')

    def get_validation_summary(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Lấy validation summary từ kết quả
        """
        return result.get('validation_summary', {})

    def visualize_workflow(self) -> str:
        """
        Tạo visualization của enhanced workflow graph
        """
        try:
            # Get workflow graph
            graph = self.workflow.get_graph()
            mermaid_png = graph.draw_mermaid_png()

            # Save to file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"enhanced_workflow_diagram_{timestamp}.png"

            with open(filename, 'wb') as f:
                f.write(mermaid_png)

            print(f"✅ Đã tạo enhanced workflow diagram: {filename}")
            return filename

        except Exception as e:
            print(f"❌ Lỗi khi tạo enhanced workflow diagram: {e}")
            return ""

# ========================
# Usage Example
# ========================

if __name__ == "__main__":
    # Khởi tạo enhanced workflow
    enhanced_workflow = EnhancedEstimationWorkflow()

    # Example task
    sample_task = """
    Phát triển một ứng dụng web e-commerce hoàn chỉnh với các tính năng:
    - Quản lý sản phẩm (CRUD) với image upload
    - Giỏ hàng và thanh toán với multiple payment methods
    - Quản lý người dùng và authentication với social login
    - Admin dashboard với analytics
    - Responsive design cho mobile và desktop
    - Payment gateway integration (Stripe, PayPal)
    - Email notifications và SMS alerts
    - Advanced search và filtering với Elasticsearch
    - Product recommendations với ML
    - Multi-language support
    - Real-time chat support
    """

    # Chạy estimation (without GraphRAG for this example)
    result = enhanced_workflow.run_estimation(sample_task, graphrag_insights=None)

    # Xuất kết quả
    if result.get('workflow_status') == 'completed':
        excel_file = enhanced_workflow.export_results(result)
        mermaid_diagram = enhanced_workflow.get_mermaid_diagram(result)
        validation_summary = enhanced_workflow.get_validation_summary(result)

        print(f"\n📊 Enhanced Estimation Results:")
        print(f"- Total effort: {result.get('total_effort', 0):.1f} mandays")
        print(f"- Average confidence: {result.get('total_confidence', 0):.2f}")
        print(f"- Tasks processed: {len(result.get('final_estimation_data', []))}")
        print(f"- Excel file: {excel_file}")
        print(f"- Tasks adjusted: {validation_summary.get('adjustment_summary', {}).get('tasks_adjusted', 0)}")

        print(f"\n🎨 Enhanced Mermaid Diagram:\n{mermaid_diagram}")

    # Tạo workflow visualization
    workflow_diagram = enhanced_workflow.visualize_workflow()