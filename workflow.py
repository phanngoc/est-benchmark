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
from typing import List, Dict, Any, TypedDict, Annotated, Tuple, Optional
import operator
from dataclasses import dataclass, field
import uuid

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send
from langgraph.checkpoint.memory import MemorySaver
from streamlit import form

# Import logging
from utils.logger import get_logger
from config import Config

# Initialize logger
logger = get_logger(__name__)

# ========================
# Enhanced Data Models
# ========================

@dataclass
class TaskBreakdown:
    """Enhanced model cho việc break task với validation"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    category: str = ""  # Business logic category (Authentication, User Management, etc.)
    role: str = ""  # Backend, Frontend, QA, Infra
    parent_task: str = ""
    sub_task: str = ""
    description: str = ""
    estimation_manday: float = 0.0  # Total estimation (sum of role-specific estimations)
    complexity: str = "Medium"  # Low, Medium, High
    priority: str = "Medium"  # Low, Medium, High
    confidence_level: float = 0.8  # 0.0 - 1.0

    # Sun Asterisk-specific fields
    sub_no: str = ""  # Sub.No (e.g., "1.1", "2.3")
    task_type: str = "Implement"  # Task type (Implement, FixBug, Unit Test, Analysis)
    premise: str = ""  # Premise
    remark: str = ""  # 備考 Remark
    note: str = ""  # Note

    # Detailed effort breakdown by task type per role
    backend_implement: float = 0.0
    backend_fixbug: float = 0.0
    backend_unittest: float = 0.0
    frontend_implement: float = 0.0
    frontend_fixbug: float = 0.0
    frontend_unittest: float = 0.0
    responsive_implement: float = 0.0
    testing_implement: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'category': self.category,
            'role': self.role,
            'parent_task': self.parent_task,
            'sub_task': self.sub_task,
            'description': self.description,
            'estimation_manday': self.estimation_manday,
            'complexity': self.complexity,
            'priority': self.priority,
            'confidence_level': self.confidence_level,
            # Sun Asterisk fields
            'sub_no': self.sub_no,
            'task_type': self.task_type,
            'premise': self.premise,
            'remark': self.remark,
            'note': self.note,
            'backend_implement': self.backend_implement,
            'backend_fixbug': self.backend_fixbug,
            'backend_unittest': self.backend_unittest,
            'frontend_implement': self.frontend_implement,
            'frontend_fixbug': self.frontend_fixbug,
            'frontend_unittest': self.frontend_unittest,
            'responsive_implement': self.responsive_implement,
            'testing_implement': self.testing_implement
        }

    def to_sunasterisk_format(self) -> Dict[str, Any]:
        """Convert to Sun Asterisk Excel format."""
        return {
            'category': self.category,
            'parent_task': self.parent_task,
            'sub_task': self.sub_task,
            'sub_no': self.sub_no,
            'task': self.task_type,
            'premise': self.premise,
            'remark': self.remark,
            'backend': {
                'implement': self.backend_implement,
                'fixbug': self.backend_fixbug,
                'unittest': self.backend_unittest
            },
            'frontend': {
                'implement': self.frontend_implement,
                'fixbug': self.frontend_fixbug,
                'unittest': self.frontend_unittest
            },
            'responsive': {
                'implement': self.responsive_implement
            },
            'testing': {
                'implement': self.testing_implement
            },
            'note': self.note
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
    """
    Enhanced state cho Orchestrator với GraphRAG integration
    UPDATED: Keeps validated_results for backward compatibility with Option 3 (conditional validation)
    """
    project_id: str  # Project identifier for project-scoped operations
    original_task: str  # Task gốc từ user
    graphrag_insights: List[Dict[str, Any]]  # Insights từ GraphRAG queries

    # Category planning
    main_categories: List[str]  # Các category chính

    # Worker results với consistent annotations
    breakdown_results: Annotated[List[Dict[str, Any]], operator.add]  # Kết quả từ Worker 1
    estimation_results: Annotated[List[Dict[str, Any]], operator.add]  # Kết quả từ Worker 2 (includes Option 1 buffer)
    validated_results: Annotated[List[Dict[str, Any]], operator.add]  # Kết quả từ Worker 3 (Option 3: conditional only)

    # Final outputs
    final_estimation_data: List[Dict[str, Any]]  # Final serializable data (merged from estimation + validated)
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
        2. Xác định các BUSINESS LOGIC CATEGORIES chính cần cho dự án
        3. Tạo chiến lược để breakdown task một cách toàn diện
        4. Chuẩn bị input cho các workers chuyên biệt

        QUAN TRỌNG: Categories phải là business logic categories (không phải technical roles):
        - Authentication & Authorization
        - User Management
        - Product Management
        - Order Management
        - Payment Processing
        - Reporting & Analytics
        - Notification System
        - Content Management
        - Search & Filtering
        - Admin Dashboard
        - API Integration
        - Security & Compliance
        - Documentation
        v.v...

        Bạn sẽ có thông tin từ GraphRAG để hiểu rõ hơn về context và requirements.

        Trả về kết quả dưới dạng JSON với format:
        {
            "categories": ["Authentication & Authorization", "User Management", "Product Management", "Reporting & Analytics", "Notification System", "Documentation"],
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
        4. XÁC ĐỊNH ROLE CHO TỪNG TASK (Backend, Frontend, QA, Infra)
        5. Xác định dependencies và priority
        6. Tạo sub_no (Sub.No) cho mỗi task theo pattern phân cấp (1.1, 1.2, 2.1, etc.)
        7. Xác định feature/screen name và reference document
        8. 🚨 QUAN TRỌNG: ĐẢM BẢO MỖI TASK <21H (KHÔNG QUÁ 2.5 MANDAYS)

        STRICT TASK SIZE CONSTRAINTS (1 manday = 7 giờ):
        ⚠️ TUYỆT ĐỐI KHÔNG TẠO TASK >2.5 MANDAYS (~17.5 GIỜ)
        - Simple tasks: 0.5-1 manday (3.5-7h) - CRUD đơn giản, UI components cơ bản
        - Medium tasks: 1-2 mandays (7-14h) - Business logic vừa phải, API integration
        - Complex tasks: 2-2.5 mandays (14-17.5h) - Logic phức tạp, nhiều components
        - ❌ NEVER: >2.5 mandays - NẾU TASK LỚN HƠN → PHẢI CHIA NHỎ THÀNH NHIỀU SUB-TASKS

        Task Size Examples (GOOD ✅ vs BAD ❌):
        ✅ GOOD - Right size (<21h each):
          - "Implement JWT token generation logic" (~1-1.5 mandays)
          - "Create login API endpoint with validation" (~1 manday)
          - "Design user database schema with indexes" (~1 manday)
          - "Build login form UI component with validation" (~1-1.5 mandays)
          - "Write unit tests for authentication service" (~0.5-1 manday)

        ❌ BAD - Too large (>21h, must split):
          - "Build entire authentication system" → SPLIT INTO:
            ✅ "Design authentication database schema"
            ✅ "Implement JWT token generation and validation"
            ✅ "Create login/logout API endpoints"
            ✅ "Build login UI components"
            ✅ "Implement password reset flow"
            ✅ "Add authentication middleware"
            ✅ "Write authentication tests"

        Nguyên tắc breakdown:
        - Mỗi sub-task phải có scope RÕ RÀNG, CỤ THỂ, và có thể estimate được
        - Task phải đủ NHỎ để 1 developer hoàn thành trong <3 ngày làm việc
        - Xem xét dependencies giữa các task
        - Ưu tiên các task critical path
        - MỖI TASK CHỈ THUỘC VỀ MỘT ROLE DUY NHẤT (Backend, Frontend, Testing, hoặc Infra)
        - NẾU TASK QUÁ LỚN: Chia thành các bước nhỏ hơn với dependencies rõ ràng
        - VALIDATION: Trước khi trả về, kiểm tra lại TẤT CẢ tasks đều <2.5 mandays

        Role definitions:
        - Backend: API development, business logic, database operations, server-side processing
        - Frontend: UI components, user interactions, client-side logic, responsive design
        - Testing: Testing (unit, integration, E2E), test automation, quality assurance
        - Infra: DevOps, deployment, CI/CD, monitoring, infrastructure setup

        Trả về kết quả dưới dạng JSON với format:
        {
            "breakdown": [
                {
                    "id": "unique_id",
                    "category": "category_name",
                    "sub_no": "1.1",
                    "role": "Backend|Frontend|Testing|Infra",
                    "parent_task": "Parent Task Name",
                    "sub_task": "Specific Sub Task",
                    "feature": "Screen/Feature Name",
                    "reference": "Reference document or spec URL",
                    "description": "Detailed description",
                    "complexity": "Low/Medium/High",
                    "dependencies": ["task_id_1", "task_id_2"],
                    "priority": "Low/Medium/High",
                    "premise": "Assumptions or prerequisites",
                    "remark": "Additional remarks",
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
        5. QUAN TRỌNG: Provide CONSERVATIVE estimates - prefer slightly higher estimates for safety
        6. Consider risks, dependencies, and complexity for realistic estimates

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
        - Complexity: Low (baseline), Medium (+15%), High (+30%)
        - Dependencies: Nhiều dependencies (+15-25%)
        - Risk level: High risk (+20-40%)
        - Unknown technology: Add 20-30% learning buffer
        - External dependencies: Add 15-25% coordination buffer

        CONSERVATIVE ESTIMATION PHILOSOPHY:
        - Prefer realistic/slightly higher estimates over optimistic ones
        - Account for code review, testing, and debugging time
        - Consider integration complexity and potential blockers
        - Include buffer for unexpected issues (built into base estimates)
        - Better to overestimate slightly than underestimate significantly

        QUAN TRỌNG - Role-specific Estimation with Task Type Breakdown:
        - Mỗi task đã được assign một role cụ thể (Backend, Frontend, Testing, hoặc Infra)
        - Bạn cần break down effort theo TASK TYPE cho role tương ứng:
          * Implement: Core development work
          * FixBug: Bug fixing and issue resolution (typically 10-20% of implement)
          * Unit Test: Unit testing effort (typically 20-30% of implement)
        - Các role khác sẽ có estimation = 0
        - Ví dụ: Nếu task có role="Backend" và estimate 2.5 mandays:
          * backend_implement: 1.5 (core development)
          * backend_fixbug: 0.5 (bug fixing)
          * backend_unittest: 0.5 (unit testing)
          * frontend_implement/fixbug/unittest: 0.0
          * responsive_implement: 0.0
          * testing_implement: 0.0

        Trả về kết quả dưới dạng JSON với format:
        {
            "estimation": {
                "id": "task_id",
                "role": "Backend|Frontend|Testing|Infra",
                "estimation_manday": 2.5,
                "backend_implement": 1.5,
                "backend_fixbug": 0.5,
                "backend_unittest": 0.5,
                "frontend_implement": 0.0,
                "frontend_fixbug": 0.0,
                "frontend_unittest": 0.0,
                "responsive_implement": 0.0,
                "testing_implement": 0.0,
                "confidence_level": 0.8,
                "breakdown": {
                    "implement": 1.5,
                    "fixbug": 0.5,
                    "unittest": 0.5
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
    logger.info(f"🎯 Enhanced Orchestrator đang phân tích task: {state['original_task']}")

    llm_handler = EnhancedEstimationLLM()

    # Sử dụng pre-fetched GraphRAG insights từ state
    graphrag_insights = state.get('graphrag_insights', [])
    if graphrag_insights:
        logger.info(f"📊 Đang sử dụng {len(graphrag_insights)} GraphRAG insights có sẵn...")
    else:
        logger.warning("⚠️ Không có GraphRAG insights, sử dụng analysis cơ bản")

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

            logger.info(f"✅ Orchestrator đã phân tích: {len(categories)} categories")
            logger.info(f"📈 Complexity: {result.get('complexity_assessment', 'Unknown')}")

            return {
                'main_categories': categories,
                'graphrag_insights': graphrag_insights,
                'workflow_status': 'orchestrator_completed'
            }
        else:
            raise ValueError("Không thể parse JSON response từ Orchestrator")

    except Exception as e:
        logger.error(f"❌ Lỗi trong Enhanced Orchestrator: {e}")
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

    logger.info(f"👷‍♂️ Worker 1 (Task Breakdown) đang xử lý category: {category_focus}")

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

            # POST-PROCESSING VALIDATION: Check task size constraint <21h
            validated_tasks = []
            oversized_tasks = []

            for task in breakdown_tasks:
                task['worker_source'] = 'task_breakdown_worker'
                task['confidence_level'] = 0.8  # Default confidence từ breakdown

                # Estimate rough complexity to check if task might be >2.5 mandays
                complexity = task.get('complexity', 'Medium')
                description = task.get('description', '')
                sub_task = task.get('sub_task', '')

                # Heuristic check for oversized tasks
                is_potentially_oversized = False

                # Check 1: High complexity with vague/broad scope
                if complexity == 'High' and any(keyword in description.lower() or keyword in sub_task.lower()
                    for keyword in ['entire', 'complete', 'full', 'whole', 'all', 'toàn bộ', 'hoàn chỉnh']):
                    is_potentially_oversized = True

                # Check 2: Description too long (>200 chars suggests complex task)
                if len(description) > 200:
                    is_potentially_oversized = True

                # Check 3: Multiple major components mentioned
                component_keywords = ['database', 'api', 'ui', 'authentication', 'authorization', 'validation', 'testing', 'deployment']
                component_count = sum(1 for keyword in component_keywords if keyword in description.lower())
                if component_count > 3:
                    is_potentially_oversized = True

                if is_potentially_oversized:
                    oversized_tasks.append(task)
                    logger.warning(f"⚠️ Potentially oversized task detected: {task.get('sub_task', 'Unknown')} (complexity: {complexity})")
                else:
                    validated_tasks.append(task)

            # If oversized tasks found, log warning but still include them
            # (Let estimation worker handle the actual effort calculation)
            if oversized_tasks:
                logger.warning(f"⚠️ {len(oversized_tasks)} potentially oversized tasks detected. These may exceed 2.5 mandays.")
                logger.warning(f"   Consider manual review: {[t.get('sub_task', 'Unknown') for t in oversized_tasks]}")
                # Still add them to results for estimation worker to process
                validated_tasks.extend(oversized_tasks)

            logger.info(f"✅ Worker 1 completed: {len(validated_tasks)} tasks cho {category_focus} ({len(oversized_tasks)} may need splitting)")

            return {
                'breakdown_results': validated_tasks
            }
        else:
            raise ValueError("Không thể parse JSON response từ Breakdown Worker")

    except Exception as e:
        logger.error(f"❌ Lỗi trong Task Breakdown Worker: {e}")
        return {
            'breakdown_results': []
        }

# ========================
# Worker 2: Estimation Worker
# ========================

def calculate_smart_buffer(task_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate intelligent buffer based on risk factors, complexity, and dependencies.
    Returns buffer info with percentage and reasoning.
    """
    buffer = 0.0
    reasons = []

    # Complexity-based buffer
    complexity = task_data.get('complexity', 'Medium')
    if complexity == 'High':
        buffer += 0.20
        reasons.append("High complexity (+20%)")
    elif complexity == 'Medium':
        buffer += 0.10
        reasons.append("Medium complexity (+10%)")

    # Risk factors buffer
    risk_factors = task_data.get('risk_factors', [])
    if len(risk_factors) > 2:
        buffer += 0.15
        reasons.append(f"Multiple risk factors ({len(risk_factors)}) (+15%)")
    elif len(risk_factors) > 0:
        buffer += 0.08
        reasons.append(f"Some risk factors ({len(risk_factors)}) (+8%)")

    # Dependencies buffer
    dependencies = task_data.get('dependencies', [])
    if len(dependencies) > 3:
        buffer += 0.12
        reasons.append(f"Many dependencies ({len(dependencies)}) (+12%)")
    elif len(dependencies) > 0:
        buffer += 0.05
        reasons.append(f"Some dependencies ({len(dependencies)}) (+5%)")

    # Priority-based buffer for critical tasks
    priority = task_data.get('priority', 'Medium')
    if priority == 'High':
        buffer += 0.10
        reasons.append("High priority task (+10%)")

    # Cap maximum buffer at 50%
    buffer = min(buffer, 0.50)

    return {
        'buffer_percentage': buffer,
        'buffer_reasons': reasons,
        'adjustment_applied': buffer > 0
    }

def estimation_worker(worker_input) -> Dict[str, Any]:
    """
    Worker 2: Chuyên estimation effort cho các task
    Receives task_breakdown via Send() mechanism
    Enhanced with few-shot prompting from historical data
    NOW INCLUDES: Smart buffer calculation and built-in validation (Option 1)
    """
    # Extract task data from worker input
    task_breakdown = worker_input.get('task_breakdown', {})
    task_name = task_breakdown.get('sub_task', 'Unknown Task')

    logger.info(f"👷‍♂️ Worker 2 (Estimation) đang estimate: {task_name}")

    llm_handler = EnhancedEstimationLLM()

    # NEW: Search for similar historical estimations for few-shot prompting
    from utils.estimation_history_manager import get_history_manager

    # Extract project_id from worker_input (passed from state)
    project_id = worker_input.get('project_id', None)

    few_shot_context = ""
    try:
        # Get project-scoped history manager
        history_manager = get_history_manager(project_id=project_id)

        # Create search query from task data
        search_description = task_breakdown.get('description', '')
        search_category = task_breakdown.get('category')
        search_role = task_breakdown.get('role')
        
        logger.debug(f"   🔍 Searching historical data with:")
        if project_id:
            logger.debug(f"     - Project ID: {project_id}")
        logger.debug(f"     - Description: {search_description[:100]}...")
        logger.debug(f"     - Category: {search_category}")
        logger.debug(f"     - Role: {search_role}")

        # Search for similar tasks
        similar_tasks = history_manager.search_similar(
            description=search_description,
            category=search_category,
            role=search_role,
            top_k=5,
            similarity_threshold=0.6
        )

        if similar_tasks:
            logger.info(f"   📚 Found {len(similar_tasks)} similar historical tasks")
            few_shot_context = history_manager.build_few_shot_prompt(similar_tasks, max_examples=5)
            
            # Log the few-shot context for debugging
            logger.debug(f"   📝 Few-shot context generated ({len(few_shot_context)} chars):")
            logger.debug(f"   {few_shot_context[:500]}..." if len(few_shot_context) > 500 else f"   {few_shot_context}")
        else:
            logger.debug(f"   ℹ️ No similar historical tasks found")
            few_shot_context = "No similar historical tasks found. Please estimate based on your expertise."

    except Exception as e:
        logger.warning(f"   ⚠️ Could not retrieve historical data: {e}")
        few_shot_context = "Historical data unavailable. Please estimate based on your expertise."
    
    # Log the final few-shot context that will be sent to LLM
    logger.debug(f"   🎯 Final few-shot context to be used:")
    if len(few_shot_context) > 200:
        logger.debug(f"   {few_shot_context[:200]}... (truncated, total: {len(few_shot_context)} chars)")
    else:
        logger.debug(f"   {few_shot_context}")

    messages = [
        SystemMessage(content=llm_handler.get_estimation_worker_prompt()),
        HumanMessage(content=f"""
        Task cần estimation:
        - Category: {task_breakdown.get('category', '')}
        - Role: {task_breakdown.get('role', 'Backend')}
        - Parent Task: {task_breakdown.get('parent_task', '')}
        - Sub Task: {task_breakdown.get('sub_task', '')}
        - Description: {task_breakdown.get('description', '')}
        - Complexity: {task_breakdown.get('complexity', 'Medium')}
        - Dependencies: {task_breakdown.get('dependencies', [])}
        - Priority: {task_breakdown.get('priority', 'Medium')}

        QUAN TRỌNG: Task này có role="{task_breakdown.get('role', 'Backend')}"
        Chỉ estimate cho role này, các role khác để 0.

        {few_shot_context}

        Hãy estimate effort cho middle developer (3 năm kinh nghiệm) với unit manday (7 giờ/ngày).
        Sử dụng các historical examples bên trên làm tham khảo để có estimation chính xác hơn.
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

            # Extract detailed task type breakdowns
            backend_impl = estimation_data.get('backend_implement', 0.0)
            backend_fix = estimation_data.get('backend_fixbug', 0.0)
            backend_test = estimation_data.get('backend_unittest', 0.0)
            frontend_impl = estimation_data.get('frontend_implement', 0.0)
            frontend_fix = estimation_data.get('frontend_fixbug', 0.0)
            frontend_test = estimation_data.get('frontend_unittest', 0.0)
            responsive_impl = estimation_data.get('responsive_implement', 0.0)
            testing_impl = estimation_data.get('testing_implement', 0.0)

            # Calculate role totals
            estimation_backend = backend_impl + backend_fix + backend_test
            estimation_frontend = frontend_impl + frontend_fix + frontend_test
            estimation_testing = testing_impl
            estimation_infra = 0.0  # Infra not broken down by task type

            # Calculate total estimation
            total_estimation = estimation_backend + estimation_frontend + estimation_testing + estimation_infra + responsive_impl

            # If LLM didn't provide detailed breakdown, use total and assign to appropriate role
            if total_estimation == 0.0:
                total_estimation = estimation_data.get('estimation_manday', 1.0)
                task_role = task_breakdown.get('role', 'Backend')

                # Distribute effort: 60% implement, 20% fixbug, 20% unittest
                if task_role == 'Backend':
                    backend_impl = total_estimation * 0.6
                    backend_fix = total_estimation * 0.2
                    backend_test = total_estimation * 0.2
                    estimation_backend = total_estimation
                elif task_role == 'Frontend':
                    frontend_impl = total_estimation * 0.6
                    frontend_fix = total_estimation * 0.2
                    frontend_test = total_estimation * 0.2
                    estimation_frontend = total_estimation
                elif task_role == 'Testing':
                    testing_impl = total_estimation
                    estimation_testing = total_estimation
                elif task_role == 'Infra':
                    estimation_infra = total_estimation

            # OPTION 1: Apply smart buffer calculation with built-in validation
            buffer_info = calculate_smart_buffer(task_breakdown)
            buffer_multiplier = 1.0 + buffer_info['buffer_percentage']

            # Apply buffer to all estimations
            buffered_total = total_estimation * buffer_multiplier
            buffered_backend = estimation_backend * buffer_multiplier
            buffered_frontend = estimation_frontend * buffer_multiplier
            buffered_testing = estimation_testing * buffer_multiplier
            buffered_infra = estimation_infra * buffer_multiplier

            # Apply buffer to detailed breakdowns
            buffered_backend_impl = backend_impl * buffer_multiplier
            buffered_backend_fix = backend_fix * buffer_multiplier
            buffered_backend_test = backend_test * buffer_multiplier
            buffered_frontend_impl = frontend_impl * buffer_multiplier
            buffered_frontend_fix = frontend_fix * buffer_multiplier
            buffered_frontend_test = frontend_test * buffer_multiplier
            buffered_responsive_impl = responsive_impl * buffer_multiplier
            buffered_testing_impl = testing_impl * buffer_multiplier

            estimated_task.update({
                'estimation_manday': buffered_total,
                'estimation_backend_manday': buffered_backend,
                'estimation_frontend_manday': buffered_frontend,
                'estimation_testing_manday': buffered_testing,
                'estimation_infra_manday': buffered_infra,
                'original_estimation': total_estimation,  # Keep original before buffer
                'buffer_applied': buffer_info['buffer_percentage'],
                'buffer_reasons': buffer_info['buffer_reasons'],
                'confidence_level': estimation_data.get('confidence_level', 0.7),
                'estimation_breakdown': estimation_data.get('breakdown', {}),
                'risk_factors': estimation_data.get('risk_factors', []),
                'assumptions': estimation_data.get('assumptions', []),
                'worker_source': 'estimation_worker_with_validation',
                'validation_notes': f"Smart buffer applied: {buffer_info['buffer_percentage']*100:.0f}% - " + ", ".join(buffer_info['buffer_reasons']) if buffer_info['adjustment_applied'] else "No buffer needed",
                # Sun Asterisk detailed breakdown (with buffer)
                'backend_implement': buffered_backend_impl,
                'backend_fixbug': buffered_backend_fix,
                'backend_unittest': buffered_backend_test,
                'frontend_implement': buffered_frontend_impl,
                'frontend_fixbug': buffered_frontend_fix,
                'frontend_unittest': buffered_frontend_test,
                'responsive_implement': buffered_responsive_impl,
                'testing_implement': buffered_testing_impl
            })

            logger.info(f"✅ Worker 2 estimated: {total_estimation:.1f} → {buffered_total:.1f} mandays (Buffer: {buffer_info['buffer_percentage']*100:.0f}%, Role: {task_breakdown.get('role', 'Unknown')})")

            return {
                'estimation_results': [estimated_task]
            }
        else:
            raise ValueError("Không thể parse JSON response từ Estimation Worker")

    except Exception as e:
        logger.error(f"❌ Lỗi trong Estimation Worker: {e}")
        # Return task với default estimation
        fallback_task = task_breakdown.copy() if task_breakdown else {}
        task_role = fallback_task.get('role', 'Backend')
        
        # Assign 1.0 manday to appropriate role
        backend_est = 1.0 if task_role == 'Backend' else 0.0
        frontend_est = 1.0 if task_role == 'Frontend' else 0.0
        testing_est = 1.0 if task_role == 'Testing' else 0.0
        infra_est = 1.0 if task_role == 'Infra' else 0.0

        fallback_task.update({
            'estimation_manday': 1.0,  # Default fallback
            'estimation_backend_manday': backend_est,
            'estimation_frontend_manday': frontend_est,
            'estimation_testing_manday': testing_est,
            'estimation_infra_manday': infra_est,
            'original_estimation': 1.0,
            'confidence_level': 0.5,
            'worker_source': 'estimation_worker_fallback'
        })
        return {
            'estimation_results': [fallback_task]
        }

# ========================
# OPTION 2: Rule-based Validation (Deterministic)
# ========================

def apply_validation_rules(estimation_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Apply deterministic validation rules to estimation results.
    This is a post-processing step without LLM calls (Option 2).

    Returns updated estimation results with additional validation metadata.
    """
    validated_results = []

    for task in estimation_results:
        # Skip if already has buffer applied (from Option 1)
        if task.get('buffer_applied', 0) > 0:
            validated_results.append(task)
            continue

        # Calculate buffer for tasks without it
        buffer_info = calculate_smart_buffer(task)
        buffer_multiplier = 1.0 + buffer_info['buffer_percentage']

        # Apply buffer to estimation
        original_estimation = task.get('estimation_manday', 0)
        validated_task = task.copy()

        validated_task.update({
            'estimation_manday': original_estimation * buffer_multiplier,
            'original_estimation': original_estimation,
            'buffer_applied': buffer_info['buffer_percentage'],
            'buffer_reasons': buffer_info['buffer_reasons'],
            'validation_notes': f"Rule-based buffer: {buffer_info['buffer_percentage']*100:.0f}% - " + ", ".join(buffer_info['buffer_reasons']) if buffer_info['adjustment_applied'] else "No buffer needed",
            'validation_method': 'deterministic_rules'
        })

        validated_results.append(validated_task)

    return validated_results

# ========================
# OPTION 3: Conditional Validation Filter
# ========================

def should_validate(task: Dict[str, Any]) -> bool:
    """
    Determine if a task needs LLM-based validation (Option 3).
    Only validate high-risk, low-confidence, or critical path tasks.

    Returns True if task requires validation, False otherwise.
    """
    # High-risk tasks (>2 risk factors)
    risk_factors = task.get('risk_factors', [])
    if len(risk_factors) > 2:
        return True

    # Low confidence tasks (<0.6)
    confidence = task.get('confidence_level', 1.0)
    if confidence < 0.6:
        return True

    # Critical path tasks (high priority + many dependencies)
    priority = task.get('priority', 'Medium')
    dependencies = task.get('dependencies', [])
    if priority == 'High' and len(dependencies) > 2:
        return True

    # High complexity with low confidence
    complexity = task.get('complexity', 'Medium')
    if complexity == 'High' and confidence < 0.75:
        return True

    return False

# ========================
# Worker 3: Conditional Validation Worker (Option 3)
# ========================

def validation_worker(worker_input) -> Dict[str, Any]:
    """
    Worker 3: Validation và calculation với risk mitigation
    Receives estimation_task via Send() mechanism
    """
    # Extract estimation task from worker input
    estimation_task = worker_input.get('estimation_task', {})
    task_name = estimation_task.get('sub_task', 'Unknown Task')

    logger.info(f"👷‍♂️ Worker 3 (Validation) đang validate: {task_name}")

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
            
            # Get validated estimation (total)
            validated_estimation = validation_data.get('validated_estimation', estimation_task.get('estimation_manday', 0))
            original_estimation = validation_data.get('original_estimation', estimation_task.get('estimation_manday', 0))
            
            # Calculate adjustment ratio if validation changed the estimation
            adjustment_ratio = 1.0
            if original_estimation > 0:
                adjustment_ratio = validated_estimation / original_estimation
            
            # Apply adjustment ratio to role-specific estimations
            original_backend = estimation_task.get('estimation_backend_manday', 0.0)
            original_frontend = estimation_task.get('estimation_frontend_manday', 0.0)
            original_testing = estimation_task.get('estimation_testing_manday', 0.0)
            original_infra = estimation_task.get('estimation_infra_manday', 0.0)

            validated_task.update({
                'estimation_manday': validated_estimation,
                'estimation_backend_manday': original_backend * adjustment_ratio,
                'estimation_frontend_manday': original_frontend * adjustment_ratio,
                'estimation_testing_manday': original_testing * adjustment_ratio,
                'estimation_infra_manday': original_infra * adjustment_ratio,
                'original_estimation': original_estimation,
                'confidence_level': validation_data.get('confidence_level', estimation_task.get('confidence_level', 0.7)),
                'validation_notes': validation_data.get('validation_notes', ''),
                'adjustment_reason': validation_data.get('adjustment_reason', ''),
                'risk_mitigation': validation_data.get('risk_mitigation', []),
                'worker_source': 'validation_worker'
            })

            logger.info(f"✅ Worker 3 validated: {original_estimation:.1f} → {validated_estimation:.1f} mandays")

            return {
                'validated_results': [validated_task]
            }
        else:
            raise ValueError("Không thể parse JSON response từ Validation Worker")

    except Exception as e:
        logger.error(f"❌ Lỗi trong Validation Worker: {e}")
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
    project_id = state.get('project_id', None)
    logger.info(f"📋 Đang phân công breakdown workers cho {len(categories)} categories")

    sends = []
    for category in categories:
        send = Send(
            "task_breakdown_worker",
            {
                "category_focus": category,
                "original_task": state['original_task'],
                "project_id": project_id  # Pass project_id to worker
            }
        )
        sends.append(send)

    return sends

def assign_estimation_workers(state: EnhancedOrchestratorState) -> List[Send]:
    """
    Phân công estimation workers cho mỗi breakdown task
    """
    breakdown_results = state.get('breakdown_results', [])
    project_id = state.get('project_id', None)
    logger.info(f"📋 Đang phân công estimation workers cho {len(breakdown_results)} tasks")

    sends = []
    for task_breakdown in breakdown_results:
        send = Send(
            "estimation_worker",
            {
                "task_breakdown": task_breakdown,
                "project_id": project_id  # Pass project_id to worker
            }
        )
        sends.append(send)

    return sends

def assign_validation_workers(state: EnhancedOrchestratorState) -> List[Send]:
    """
    OPTION 3: Conditional validation - only validate high-risk tasks
    Phân công validation workers CHỈ cho tasks cần validation
    """
    estimation_results = state.get('estimation_results', [])
    project_id = state.get('project_id', None)

    # Filter tasks that need validation
    tasks_needing_validation = [task for task in estimation_results if should_validate(task)]
    tasks_skipped = len(estimation_results) - len(tasks_needing_validation)

    logger.info(f"📋 Conditional validation: {len(tasks_needing_validation)} tasks need validation, {tasks_skipped} tasks skip validation")

    sends = []
    for estimation_task in tasks_needing_validation:
        send = Send(
            "validation_worker",
            {
                "estimation_task": estimation_task,
                "project_id": project_id  # Pass project_id to worker
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
    NOW INCLUDES: Option 2 rule-based validation for tasks that skipped LLM validation
    """
    logger.info("🔄 Enhanced Synthesizer đang tổng hợp kết quả...")

    # Get results from both estimation and validation workers
    estimation_results = state.get('estimation_results', [])
    validated_results = state.get('validated_results', [])

    if not estimation_results and not validated_results:
        logger.warning("⚠️ Không có results từ workers")
        return {
            'final_estimation_data': [],
            'total_effort': 0.0,
            'total_confidence': 0.0,
            'validation_summary': {},
            'workflow_status': 'no_results'
        }

    # Create validated task ID set
    validated_task_ids = {task.get('id') for task in validated_results}

    # Find tasks that skipped validation
    tasks_skipped_validation = [
        task for task in estimation_results
        if task.get('id') not in validated_task_ids
    ]

    # OPTION 2: Apply rule-based validation to tasks that skipped LLM validation
    if tasks_skipped_validation:
        logger.info(f"📋 Applying rule-based validation to {len(tasks_skipped_validation)} tasks that skipped LLM validation")
        rule_validated = apply_validation_rules(tasks_skipped_validation)
        validated_results.extend(rule_validated)

    if not validated_results:
        logger.warning("⚠️ No final validated results")
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

    logger.info(f"✅ Enhanced Synthesizer hoàn thành:")
    logger.info(f"   - {len(validated_results)} tasks")
    logger.info(f"   - {total_effort:.1f} mandays total")
    logger.info(f"   - {total_confidence:.2f} average confidence")
    logger.info(f"   - {adjusted_tasks} tasks adjusted")

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

def export_enhanced_excel(
    df: pd.DataFrame,
    validation_summary: Dict[str, Any],
    estimation_id: str = None,
    filename: str = None,
    format: str = "enhanced",
    no: str = "001",
    version: str = "1.0",
    issue_date: str = None,
    md_per_mm: int = 20,
    project_id: str = None
) -> Tuple[str, str]:
    """
    Enhanced Excel export với detailed analysis.

    Args:
        df: DataFrame with estimation data
        validation_summary: Summary of validation results
        estimation_id: Unique estimation identifier (auto-generated if None)
        filename: Output filename (auto-generated if None)
        format: Export format - "enhanced" (default) or "sunasterisk"
        no: Document number (for Sun Asterisk format)
        version: Document version (for Sun Asterisk format)
        issue_date: Issue date (for Sun Asterisk format)
        md_per_mm: Man-days per man-month (for Sun Asterisk format)
        project_id: Project identifier for project-scoped storage

    Returns:
        Tuple[str, str]: (Path to exported Excel file, estimation_id)
    """
    from config import Config

    # Generate estimation_id if not provided
    if estimation_id is None:
        estimation_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Handle Sun Asterisk format
    if format == "sunasterisk":
        from utils.sunasterisk_excel_exporter import export_sunasterisk_excel

        # Convert DataFrame to Sun Asterisk format
        data = []
        for _, row in df.iterrows():
            task_dict = row.to_dict()

            # Convert to Sun Asterisk format
            sunasterisk_task = {
                'category': task_dict.get('category', ''),
                'parent_task': task_dict.get('parent_task', ''),
                'sub_task': task_dict.get('sub_task', ''),
                'sub_no': task_dict.get('sub_no', ''),
                'task': task_dict.get('task_type', 'Implement'),
                'premise': task_dict.get('premise', ''),
                'remark': task_dict.get('remark', ''),
                'backend': {
                    'implement': task_dict.get('backend_implement', 0) or 0,
                    'fixbug': task_dict.get('backend_fixbug', 0) or 0,
                    'unittest': task_dict.get('backend_unittest', 0) or 0
                },
                'frontend': {
                    'implement': task_dict.get('frontend_implement', 0) or 0,
                    'fixbug': task_dict.get('frontend_fixbug', 0) or 0,
                    'unittest': task_dict.get('frontend_unittest', 0) or 0
                },
                'responsive': {
                    'implement': task_dict.get('responsive_implement', 0) or 0
                },
                'testing': {
                    'implement': task_dict.get('testing_implement', 0) or 0
                },
                'note': task_dict.get('note', '')
            }
            data.append(sunasterisk_task)

        # Export using Sun Asterisk exporter (with project_id support)
        sunasterisk_filepath = export_sunasterisk_excel(
            data=data,
            filename=filename,
            no=no,
            version=version,
            issue_date=issue_date,
            md_per_mm=md_per_mm,
            project_id=project_id
        )
        return sunasterisk_filepath, estimation_id

    # Original enhanced format
    # Auto-generate filename with new format if not provided
    if filename is None:
        filename = f"estimation_result_{estimation_id}.xlsx"

    # Determine result directory (project-scoped or default)
    if project_id:
        result_dir = Config.get_project_result_dir(project_id)
        logger.info(f"Using project-scoped result directory: {result_dir}")
    else:
        result_dir = Config.RESULT_EST_DIR
    
    # Ensure result_est directory exists
    os.makedirs(result_dir, exist_ok=True)

    # Save to result_est directory
    filepath = os.path.join(result_dir, filename)

    try:
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            # Main estimation table với enhanced columns including role-specific estimations
            estimation_columns = [
                'id', 'category', 'role', 'parent_task', 'sub_task', 'description',
                'estimation_manday',
                'confidence_level', 'complexity', 'priority',
                # Sun Asterisk detailed breakdown
                'sub_no', 'feature', 'reference', 'task_type', 'premise',
                'task_jp', 'assumption_jp', 'remark', 'note',
                'backend_implement', 'backend_fixbug', 'backend_unittest',
                'frontend_implement', 'frontend_fixbug', 'frontend_unittest',
                'responsive_implement', 'testing_implement'
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

            # Role breakdown - NEW SHEET
            if 'role' in df.columns:
                # Calculate totals for each role
                role_summary_data = []
                for role in ['Backend', 'Frontend', 'QA', 'Infra']:
                    role_column = f'estimation_{role.lower()}_manday'
                    if role_column in df.columns:
                        total_effort = df[role_column].sum()
                        task_count = df[df['role'] == role].shape[0]
                        avg_effort = total_effort / task_count if task_count > 0 else 0
                        role_summary_data.append({
                            'Role': role,
                            'Task Count': task_count,
                            'Total Effort (mandays)': round(total_effort, 2),
                            'Average Effort (mandays)': round(avg_effort, 2),
                            'Percentage': f"{(total_effort / df['estimation_manday'].sum() * 100):.1f}%" if df['estimation_manday'].sum() > 0 else "0%"
                        })
                
                if role_summary_data:
                    role_summary_df = pd.DataFrame(role_summary_data)
                    role_summary_df.to_excel(writer, sheet_name='Role Breakdown', index=False)

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

        logger.info(f"✅ Enhanced Excel export completed: {filepath} (ID: {estimation_id})")
        return filepath, estimation_id

    except Exception as e:
        logger.error(f"❌ Lỗi khi export Enhanced Excel: {e}")
        return "", estimation_id

# ========================
# Enhanced Workflow Builder
# ========================

class EnhancedEstimationWorkflow:
    """
    Enhanced Estimation Workflow với specialized workers
    """

    def __init__(self, project_id: Optional[str] = None):
        """
        Initialize Enhanced Estimation Workflow
        
        Args:
            project_id: Optional project identifier for project-scoped operations.
                       When provided, all history and tracking will be project-specific.
        """
        self.project_id = project_id
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

        logger.info("✅ Enhanced Estimation Workflow đã được build thành công!")

    def run_estimation(self, task_description: str, graphrag_insights=None, thread_id: str = None, project_id: str = None) -> Dict[str, Any]:
        """
        Chạy enhanced estimation workflow với auto-generated estimation_id

        Args:
            task_description: Project description to estimate
            graphrag_insights: Optional GraphRAG insights
            thread_id: Optional custom thread ID (auto-generated if None)
            project_id: Optional project identifier for project-scoped operations.
                       If not provided, uses the instance's project_id.

        Returns:
            Dict with estimation results including estimation_id
        """
        # Use provided project_id or fall back to instance project_id
        effective_project_id = project_id or self.project_id
        
        # Generate estimation_id (timestamp-based)
        estimation_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Auto-generate thread_id if not provided
        if thread_id is None:
            thread_id = f"estimation_{estimation_id}"

        logger.info(f"🚀 Bắt đầu Enhanced Estimation Workflow (ID: {estimation_id})")
        if effective_project_id:
            logger.info(f"   Project ID: {effective_project_id}")
        logger.info(f"   Task: {task_description[:100]}...")

        initial_state = {
            "project_id": effective_project_id or "",  # Add project_id to state
            "estimation_id": estimation_id,  # NEW: Add estimation_id to state
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

            # Ensure estimation_id and project_id are in result
            result['estimation_id'] = estimation_id
            result['project_id'] = effective_project_id or ""

            logger.info(f"🎉 Enhanced Workflow hoàn thành (ID: {estimation_id})")
            logger.info(f"   Status: {result.get('workflow_status', 'unknown')}")
            logger.info(f"   Total Effort: {result.get('total_effort', 0):.1f} mandays")

            return result

        except Exception as e:
            logger.error(f"❌ Lỗi khi chạy Enhanced Workflow (ID: {estimation_id}): {e}")
            return {
                "estimation_id": estimation_id,
                "project_id": effective_project_id or "",
                "workflow_status": "failed",
                "error": str(e)
            }

    def export_results(
        self,
        result: Dict[str, Any],
        filename: str = None,
        format: str = "sunasterisk",
        no: str = "001",
        version: str = "1.0",
        issue_date: str = None,
        md_per_mm: int = 20,
        project_id: str = None
    ) -> Tuple[str, str]:
        """
        Enhanced export kết quả ra Excel với SQLite tracking.

        Args:
            result: Workflow result dictionary
            filename: Output filename (auto-generated if None)
            format: Export format - "enhanced" (default) or "sunasterisk"
            no: Document number (for Sun Asterisk format)
            version: Document version (for Sun Asterisk format)
            issue_date: Issue date (for Sun Asterisk format)
            md_per_mm: Man-days per man-month (for Sun Asterisk format)
            project_id: Project identifier for project-scoped storage.
                       If not provided, uses result's project_id or instance's project_id.

        Returns:
            Tuple[str, str]: (Path to exported Excel file, estimation_id)
        """
        estimation_data = result.get('final_estimation_data', [])
        estimation_id = result.get('estimation_id', '')
        
        # Use provided project_id, or fall back to result's project_id, or instance's project_id
        effective_project_id = project_id or result.get('project_id') or self.project_id

        if not estimation_data:
            logger.warning("⚠️ Không có dữ liệu để export")
            return "", estimation_id

        df = pd.DataFrame(estimation_data)
        validation_summary = result.get('validation_summary', {})

        # Export to Excel with project-scoped file path
        filepath, estimation_id = export_enhanced_excel(
            df=df,
            validation_summary=validation_summary,
            estimation_id=estimation_id,
            filename=filename,
            format=format,
            no=no,
            version=version,
            issue_date=issue_date,
            md_per_mm=md_per_mm,
            project_id=effective_project_id
        )

        # Save to SQLite tracker with project_id
        if filepath and estimation_id:
            try:
                from utils.estimation_result_tracker import get_result_tracker

                tracker = get_result_tracker()

                # Create estimation run entry with project_id
                tracker.create_estimation_run(
                    estimation_id=estimation_id,
                    file_path=filepath,
                    summary_data={
                        'total_effort': result.get('total_effort', 0.0),
                        'total_tasks': len(estimation_data),
                        'average_confidence': result.get('total_confidence', 0.0),
                        'workflow_status': result.get('workflow_status', 'completed'),
                        'project_description': result.get('original_task', '')
                    },
                    project_id=effective_project_id
                )

                # Save task details with project_id
                saved_count = tracker.save_estimation_tasks(
                    estimation_id=estimation_id,
                    tasks_data=estimation_data,
                    project_id=effective_project_id
                )

                if effective_project_id:
                    logger.info(f"✅ Estimation {estimation_id} tracked in SQLite database for project {effective_project_id} ({saved_count} tasks)")
                else:
                    logger.info(f"✅ Estimation {estimation_id} tracked in SQLite database ({saved_count} tasks)")

            except Exception as e:
                logger.error(f"❌ Failed to save to SQLite tracker: {e}")
                # Continue even if tracking fails - Excel export is still successful

        return filepath, estimation_id

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

            logger.info(f"✅ Đã tạo enhanced workflow diagram: {filename}")
            return filename

        except Exception as e:
            logger.error(f"❌ Lỗi khi tạo enhanced workflow diagram: {e}")
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
        excel_file = enhanced_workflow.export_results(result, format="sunasterisk")
        mermaid_diagram = enhanced_workflow.get_mermaid_diagram(result)
        validation_summary = enhanced_workflow.get_validation_summary(result)

        logger.info(f"\n📊 Enhanced Estimation Results:")
        logger.info(f"- Total effort: {result.get('total_effort', 0):.1f} mandays")
        logger.info(f"- Average confidence: {result.get('total_confidence', 0):.2f}")
        logger.info(f"- Tasks processed: {len(result.get('final_estimation_data', []))}")
        logger.info(f"- Excel file: {excel_file}")
        logger.info(f"- Tasks adjusted: {validation_summary.get('adjustment_summary', {}).get('tasks_adjusted', 0)}")

        logger.info(f"\n🎨 Enhanced Mermaid Diagram:\n{mermaid_diagram}")

    # Tạo workflow visualization
    workflow_diagram = enhanced_workflow.visualize_workflow()