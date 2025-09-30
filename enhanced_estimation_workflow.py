"""
Enhanced Estimation Workflow using LangGraph Orchestrator-Worker Pattern
=======================================================================

New architecture with 3 specialized workers:
1. Worker 1: Task Breakdown with GraphRAG integration
2. Worker 2: Estimation Worker for effort calculation
3. Worker 3: Effort Calculator & Validator with validation logic

Integrated with GraphRAG handler from app.py for smarter analysis.

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
    """Enhanced model for task breakdown with validation"""
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
    """Model to store insights from GraphRAG"""
    query: str
    response: str
    references: List[str]
    timestamp: str
    confidence: float = 0.8

# ========================
# Enhanced State Definitions
# ========================

class EnhancedOrchestratorState(TypedDict):
    """Enhanced state for Orchestrator with GraphRAG integration"""
    original_task: str  # Original task from user
    graphrag_insights: List[Dict[str, Any]]  # Insights from GraphRAG queries

    # Category planning
    main_categories: List[str]  # Main categories

    # Worker results with consistent annotations
    breakdown_results: Annotated[List[Dict[str, Any]], operator.add]  # Results from Worker 1
    estimation_results: Annotated[List[Dict[str, Any]], operator.add]  # Results from Worker 2
    validated_results: Annotated[List[Dict[str, Any]], operator.add]  # Results from Worker 3

    # Final outputs
    final_estimation_data: List[Dict[str, Any]]  # Final serializable data
    total_effort: float  # Total effort (manday)
    total_confidence: float  # Average confidence score
    mermaid_diagram: str  # Mermaid code for visualization
    validation_summary: Dict[str, Any]  # Summary of validation process
    workflow_status: str  # Workflow status

# ========================
# Enhanced LLM Configuration
# ========================

class EnhancedEstimationLLM:
    """Enhanced LLM wrapper with specialized prompts for each worker"""

    def __init__(self, model_name: str = "gpt-4o-mini"):
        self.llm = ChatOpenAI(
            model=model_name,
            temperature=0.1,
            max_tokens=3000
        )

    def get_orchestrator_prompt(self) -> str:
        return """
        You are a Senior Project Manager with 15 years of experience in analyzing and breaking down complex software projects.

        Your tasks:
        1. Analyze the provided task with context from GraphRAG
        2. Identify the main categories needed for the project
        3. Create a strategy to break down the task comprehensively
        4. Prepare input for specialized workers

        You will have information from GraphRAG to better understand the context and requirements.

        Return results in JSON format:
        {
            "categories": ["Frontend", "Backend", "Database", "DevOps", "Testing", "Documentation"],
            "analysis_strategy": "Overall analysis strategy",
            "complexity_assessment": "Low/Medium/High",
            "estimated_timeline": "Overall time estimate"
        }
        """

    def get_breakdown_worker_prompt(self) -> str:
        return """
        You are a Technical Lead expert in breaking down technical requirements into specific tasks.

        Your tasks:
        1. Use information from GraphRAG to deeply understand requirements
        2. Break down the assigned category into parent tasks and sub tasks
        3. Create detailed descriptions for each task
        4. Identify dependencies and priority

        Breakdown principles:
        - Each sub-task must have clear scope and be estimatable
        - Ideal task size: 0.5-3 mandays for middle developer
        - Consider dependencies between tasks
        - Prioritize critical path tasks

        Return results in JSON format:
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
        You are a Senior Developer with 8 years of experience, expert in effort estimation for software projects.

        Your tasks:
        1. Analyze each provided sub-task
        2. Estimate effort based on middle developer (3 years experience)
        3. Calculate effort with unit as manday (7 hours/day)
        4. Assess confidence level of estimation

        Estimation standards for middle developer (3 years experience):
        - Simple CRUD operations: 0.5-1 manday
        - Complex business logic: 1-3 manday
        - API integration (simple): 0.5-1.5 manday
        - API integration (complex): 1.5-3 manday
        - UI components (basic): 0.5-1 manday
        - UI components (complex/responsive): 1-2.5 manday
        - Database design/migration: 0.5-2 manday
        - Authentication/Authorization: 1-2 manday
        - Unit testing: 20-30% of development effort
        - Integration testing: 10-20% of development effort
        - Documentation: 10-15% of development effort

        Factors affecting estimation:
        - Complexity: Low (-20%), Medium (baseline), High (+50%)
        - Dependencies: Many dependencies (+20-30%)
        - Risk level: High risk (+30-50%)

        Return results in JSON format:
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
        You are a Project Manager with deep expertise in quality assurance and risk management.

        Your tasks:
        1. Validate estimations from Estimation Worker
        2. Cross-check logic and consistency
        3. Apply buffer for risk mitigation
        4. Ensure total effort is reasonable

        Validation criteria:
        - Consistency check: Compare with similar tasks
        - Dependency validation: Ensure dependencies are calculated correctly
        - Risk assessment: Evaluate and apply buffer for high-risk tasks
        - Team capacity: Consider realistic team capacity
        - Buffer calculation: 10-20% for risky tasks

        Adjustment rules:
        - Low complexity, low risk: No adjustment
        - Medium complexity/risk: +10% buffer
        - High complexity/risk: +20% buffer
        - Critical path tasks: +15% buffer
        - New technology/framework: +25% buffer

        Return results in JSON format:
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
    Enhanced Orchestrator with GraphRAG integration
    """
    print(f"🎯 Enhanced Orchestrator analyzing task: {state['original_task']}")

    llm_handler = EnhancedEstimationLLM()

    # Use pre-fetched GraphRAG insights from state
    graphrag_insights = state.get('graphrag_insights', [])
    if graphrag_insights:
        print(f"📊 Using {len(graphrag_insights)} available GraphRAG insights...")
    else:
        print("⚠️ No GraphRAG insights available, using basic analysis")

    # Create context from GraphRAG insights
    graphrag_context = ""
    if graphrag_insights:
        graphrag_context = "\n\nContext from GraphRAG:\n"
        for insight in graphrag_insights:
            graphrag_context += f"Q: {insight['query']}\nA: {insight['response']}\n---\n"

    # Create prompt for Orchestrator
    messages = [
        SystemMessage(content=llm_handler.get_orchestrator_prompt()),
        HumanMessage(content=f"""
        Task to analyze and estimate:
        {state['original_task']}

        {graphrag_context}

        Based on the task and context from GraphRAG, please analyze and provide a breakdown strategy.
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

            print(f"✅ Orchestrator analyzed: {len(categories)} categories")
            print(f"📈 Complexity: {result.get('complexity_assessment', 'Unknown')}")

            return {
                'main_categories': categories,
                'graphrag_insights': graphrag_insights,
                'workflow_status': 'orchestrator_completed'
            }
        else:
            raise ValueError("Cannot parse JSON response from Orchestrator")

    except Exception as e:
        print(f"❌ Error in Enhanced Orchestrator: {e}")
        return {
            'main_categories': [],
            'graphrag_insights': graphrag_insights,
            'workflow_status': 'orchestrator_failed'
        }

# ========================
# Worker 1: Task Breakdown with GraphRAG
# ========================

def task_breakdown_worker(worker_input) -> Dict[str, Any]:
    """
    Worker 1: Specialized in breaking down tasks with GraphRAG integration
    Receives data via Send() mechanism
    """
    # Extract data from worker input
    category_focus = worker_input.get('category_focus', 'General')
    original_task = worker_input.get('original_task', '')

    print(f"👷‍♂️ Worker 1 (Task Breakdown) processing category: {category_focus}")

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

        Please break down category '{category_focus}' into specific tasks with detailed descriptions.
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
                task['confidence_level'] = 0.8  # Default confidence from breakdown

            print(f"✅ Worker 1 completed: {len(breakdown_tasks)} tasks for {category_focus}")

            return {
                'breakdown_results': breakdown_tasks
            }
        else:
            raise ValueError("Cannot parse JSON response from Breakdown Worker")

    except Exception as e:
        print(f"❌ Error in Task Breakdown Worker: {e}")
        return {
            'breakdown_results': []
        }

# ========================
# Worker 2: Estimation Worker
# ========================

def estimation_worker(worker_input) -> Dict[str, Any]:
    """
    Worker 2: Specialized in effort estimation for tasks
    Receives task_breakdown via Send() mechanism
    """
    # Extract task data from worker input
    task_breakdown = worker_input.get('task_breakdown', {})
    task_name = task_breakdown.get('sub_task', 'Unknown Task')

    print(f"👷‍♂️ Worker 2 (Estimation) estimating: {task_name}")

    llm_handler = EnhancedEstimationLLM()

    messages = [
        SystemMessage(content=llm_handler.get_estimation_worker_prompt()),
        HumanMessage(content=f"""
        Task to estimate:
        - Category: {task_breakdown.get('category', '')}
        - Parent Task: {task_breakdown.get('parent_task', '')}
        - Sub Task: {task_breakdown.get('sub_task', '')}
        - Description: {task_breakdown.get('description', '')}
        - Complexity: {task_breakdown.get('complexity', 'Medium')}
        - Dependencies: {task_breakdown.get('dependencies', [])}
        - Priority: {task_breakdown.get('priority', 'Medium')}

        Please estimate effort for middle developer (3 years experience) with unit manday (7 hours/day).
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

            # Merge with original task data
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
            raise ValueError("Cannot parse JSON response from Estimation Worker")

    except Exception as e:
        print(f"❌ Error in Estimation Worker: {e}")
        # Return task with default estimation
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
    Worker 3: Validation and calculation with risk mitigation
    Receives estimation_task via Send() mechanism
    """
    # Extract estimation task from worker input
    estimation_task = worker_input.get('estimation_task', {})
    task_name = estimation_task.get('sub_task', 'Unknown Task')

    print(f"👷‍♂️ Worker 3 (Validation) validating: {task_name}")

    llm_handler = EnhancedEstimationLLM()

    messages = [
        SystemMessage(content=llm_handler.get_validation_worker_prompt()),
        HumanMessage(content=f"""
        Task to validate:
        - ID: {estimation_task.get('id', '')}
        - Category: {estimation_task.get('category', '')}
        - Sub Task: {estimation_task.get('sub_task', '')}
        - Description: {estimation_task.get('description', '')}
        - Original Estimation: {estimation_task.get('estimation_manday', 0)} mandays
        - Complexity: {estimation_task.get('complexity', 'Medium')}
        - Dependencies: {estimation_task.get('dependencies', [])}
        - Risk Factors: {estimation_task.get('risk_factors', [])}
        - Confidence Level: {estimation_task.get('confidence_level', 0.7)}

        Please validate this estimation and apply buffer if necessary.
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
            raise ValueError("Cannot parse JSON response from Validation Worker")

    except Exception as e:
        print(f"❌ Error in Validation Worker: {e}")
        # Return task with minimal validation
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
    Assign breakdown workers for each category
    """
    categories = state.get('main_categories', [])
    print(f"📋 Assigning breakdown workers for {len(categories)} categories")

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
    Assign estimation workers for each breakdown task
    """
    breakdown_results = state.get('breakdown_results', [])
    print(f"📋 Assigning estimation workers for {len(breakdown_results)} tasks")

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
    Assign validation workers for each estimation task
    """
    estimation_results = state.get('estimation_results', [])
    print(f"📋 Assigning validation workers for {len(estimation_results)} tasks")

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
    Enhanced Synthesizer with advanced features
    """
    print("🔄 Enhanced Synthesizer synthesizing results...")

    validated_results = state.get('validated_results', [])

    if not validated_results:
        print("⚠️ No validated results from workers")
        return {
            'final_estimation_data': [],
            'total_effort': 0.0,
            'total_confidence': 0.0,
            'validation_summary': {},
            'workflow_status': 'no_results'
        }

    # Calculate summary statistics
    total_effort = sum(task.get('estimation_manday', 0) for task in validated_results)
    total_confidence = sum(task.get('confidence_level', 0) for task in validated_results) / len(validated_results)

    # Create validation summary
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

    # Create enhanced mermaid diagram
    mermaid_diagram = create_enhanced_mermaid_diagram(validated_results, validation_summary)

    print(f"✅ Enhanced Synthesizer completed:")
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
    Create enhanced mermaid diagram with dependencies and risk indicators
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
    Enhanced Excel export with detailed analysis
    """
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"enhanced_estimation_{timestamp}.xlsx"

    filepath = os.path.join(os.getcwd(), filename)

    try:
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            # Main estimation table with enhanced columns
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
        print(f"❌ Error exporting Enhanced Excel: {e}")
        return ""

# ========================
# Enhanced Workflow Builder
# ========================

class EnhancedEstimationWorkflow:
    """
    Enhanced Estimation Workflow with specialized workers
    """

    def __init__(self):
        self.workflow = None
        self.memory = MemorySaver()
        self._build_workflow()

    def _build_workflow(self):
        """Build enhanced LangGraph workflow"""

        # Create StateGraph
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

        print("✅ Enhanced Estimation Workflow built successfully!")

    def run_estimation(self, task_description: str, graphrag_insights=None, thread_id: str = "enhanced_estimation_thread") -> Dict[str, Any]:
        """
        Run enhanced estimation workflow
        """
        print(f"🚀 Starting Enhanced Estimation Workflow for task: {task_description}")

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

            print(f"🎉 Enhanced Workflow completed with status: {result.get('workflow_status', 'unknown')}")

            return result

        except Exception as e:
            print(f"❌ Error running Enhanced Workflow: {e}")
            return {
                "workflow_status": "failed",
                "error": str(e)
            }

    def export_results(self, result: Dict[str, Any], filename: str = None) -> str:
        """
        Enhanced export results to Excel
        """
        estimation_data = result.get('final_estimation_data', [])
        if not estimation_data:
            print("⚠️ No data to export")
            return ""

        df = pd.DataFrame(estimation_data)
        validation_summary = result.get('validation_summary', {})
        return export_enhanced_excel(df, validation_summary, filename)

    def get_mermaid_diagram(self, result: Dict[str, Any]) -> str:
        """
        Get enhanced mermaid diagram from results
        """
        return result.get('mermaid_diagram', '')

    def get_validation_summary(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get validation summary from results
        """
        return result.get('validation_summary', {})

    def visualize_workflow(self) -> str:
        """
        Create visualization of enhanced workflow graph
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

            print(f"✅ Created enhanced workflow diagram: {filename}")
            return filename

        except Exception as e:
            print(f"❌ Error creating enhanced workflow diagram: {e}")
            return ""

# ========================
# Usage Example
# ========================

if __name__ == "__main__":
    # Initialize enhanced workflow
    enhanced_workflow = EnhancedEstimationWorkflow()

    # Example task
    sample_task = """
    Develop a complete web e-commerce application with features:
    - Product management (CRUD) with image upload
    - Shopping cart and payment with multiple payment methods
    - User management and authentication with social login
    - Admin dashboard with analytics
    - Responsive design for mobile and desktop
    - Payment gateway integration (Stripe, PayPal)
    - Email notifications and SMS alerts
    - Advanced search and filtering with Elasticsearch
    - Product recommendations with ML
    - Multi-language support
    - Real-time chat support
    """

    # Run estimation (without GraphRAG for this example)
    result = enhanced_workflow.run_estimation(sample_task, graphrag_insights=None)

    # Export results
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

    # Create workflow visualization
    workflow_diagram = enhanced_workflow.visualize_workflow()