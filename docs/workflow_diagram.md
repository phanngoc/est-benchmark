# Enhanced Estimation Workflow Diagram

## Overview Architecture

```mermaid
graph TB
    START([START]) --> ORCH[Enhanced Orchestrator<br/>🎯 Project Analysis]
    
    ORCH --> |Analyze with GraphRAG| GRAPHRAG[GraphRAG Insights<br/>📊 Context Analysis]
    ORCH --> |Identify Categories| CATS[Main Categories<br/>📋 Business Logic Groups]
    
    CATS --> |Assign Workers| BW1[Task Breakdown Worker 1<br/>👷 Category A]
    CATS --> |Assign Workers| BW2[Task Breakdown Worker 2<br/>👷 Category B]
    CATS --> |Assign Workers| BW3[Task Breakdown Worker N<br/>👷 Category N]
    
    BW1 --> |Breakdown Results| EST1[Estimation Worker 1<br/>💰 Effort Calculation]
    BW2 --> |Breakdown Results| EST2[Estimation Worker 2<br/>💰 Effort Calculation]
    BW3 --> |Breakdown Results| EST3[Estimation Worker N<br/>💰 Effort Calculation]
    
    EST1 --> |With Smart Buffer| VAL1[Validation Worker 1<br/>✅ Risk Assessment]
    EST2 --> |With Smart Buffer| VAL2[Validation Worker 2<br/>✅ Risk Assessment]
    EST3 --> |Conditional| VAL3[Validation Worker N<br/>✅ High-Risk Only]
    
    VAL1 --> |Validated| SYNTH[Enhanced Synthesizer<br/>🔄 Results Aggregation]
    VAL2 --> |Validated| SYNTH
    VAL3 --> |Validated| SYNTH
    
    SYNTH --> |Final Output| RESULTS[Final Results<br/>📊 Excel + Mermaid]
    RESULTS --> END([END])
    
    %% Styling
    classDef orchestrator fill:#e3f2fd,stroke:#1976d2,stroke-width:3px
    classDef worker fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    classDef estimation fill:#e8f5e9,stroke:#388e3c,stroke-width:2px
    classDef validation fill:#fce4ec,stroke:#c2185b,stroke-width:2px
    classDef synthesizer fill:#f3e5f5,stroke:#7b1fa2,stroke-width:3px
    classDef graphrag fill:#e0f2f1,stroke:#00796b,stroke-width:2px
    
    class ORCH orchestrator
    class GRAPHRAG graphrag
    class BW1,BW2,BW3 worker
    class EST1,EST2,EST3 estimation
    class VAL1,VAL2,VAL3 validation
    class SYNTH synthesizer
```

## Detailed Worker Flow

```mermaid
sequenceDiagram
    participant User
    participant Orch as Enhanced Orchestrator
    participant GraphRAG
    participant BW as Breakdown Worker
    participant EW as Estimation Worker
    participant VW as Validation Worker
    participant Synth as Synthesizer
    
    User->>Orch: Submit Task Description
    
    Note over Orch: Initialize Workflow
    Orch->>GraphRAG: Query for Context
    GraphRAG-->>Orch: Return Insights
    
    Note over Orch: Analyze & Plan
    Orch->>Orch: Identify Main Categories
    
    loop For Each Category
        Orch->>BW: Assign Breakdown Task
        Note over BW: Break into Sub-tasks<br/>Assign Roles<br/>Check Size (<21h)
        BW-->>Orch: Return Breakdown Results
    end
    
    loop For Each Sub-task
        Orch->>EW: Assign Estimation
        Note over EW: Search Historical Data<br/>Apply Few-shot Learning<br/>Calculate Effort<br/>Apply Smart Buffer
        EW-->>Orch: Return Estimation + Buffer
    end
    
    loop For High-Risk Tasks Only
        Orch->>VW: Conditional Validation
        Note over VW: Risk Assessment<br/>Cross-check Logic<br/>Apply Additional Buffer
        VW-->>Orch: Return Validated Results
    end
    
    Note over Orch: Apply Rule-based Validation<br/>for Low-risk Tasks
    
    Orch->>Synth: Aggregate All Results
    Note over Synth: Merge Estimations<br/>Calculate Totals<br/>Generate Reports
    Synth-->>User: Final Excel + Mermaid Diagram
```

## Data Flow Architecture

```mermaid
flowchart LR
    subgraph Input
        TASK[Task Description]
        CONTEXT[GraphRAG Context]
    end
    
    subgraph "Orchestrator State"
        STATE[EnhancedOrchestratorState]
        STATE --> OS1[original_task]
        STATE --> OS2[graphrag_insights]
        STATE --> OS3[main_categories]
        STATE --> OS4[breakdown_results]
        STATE --> OS5[estimation_results]
        STATE --> OS6[validated_results]
        STATE --> OS7[final_estimation_data]
    end
    
    subgraph "Worker 1: Breakdown"
        W1[Task Breakdown Worker]
        W1 --> W1R[breakdown_results]
        W1R --> BR1[category]
        W1R --> BR2[role]
        W1R --> BR3[parent_task]
        W1R --> BR4[sub_task]
        W1R --> BR5[complexity]
    end
    
    subgraph "Worker 2: Estimation"
        W2[Estimation Worker]
        W2 --> W2R[estimation_results]
        W2R --> ER1[estimation_manday]
        W2R --> ER2[backend_implement]
        W2R --> ER3[frontend_implement]
        W2R --> ER4[buffer_applied]
        W2R --> ER5[confidence_level]
    end
    
    subgraph "Worker 3: Validation"
        W3[Validation Worker]
        W3 --> W3R[validated_results]
        W3R --> VR1[validated_estimation]
        W3R --> VR2[adjustment_reason]
        W3R --> VR3[risk_mitigation]
    end
    
    subgraph Output
        EXCEL[Excel Report]
        MERMAID[Mermaid Diagram]
        SUMMARY[Validation Summary]
    end
    
    TASK --> STATE
    CONTEXT --> STATE
    STATE --> W1
    W1 --> STATE
    STATE --> W2
    W2 --> STATE
    STATE --> W3
    W3 --> STATE
    STATE --> EXCEL
    STATE --> MERMAID
    STATE --> SUMMARY
    
    style STATE fill:#e1bee7,stroke:#8e24aa
    style W1 fill:#fff9c4,stroke:#f9a825
    style W2 fill:#c8e6c9,stroke:#43a047
    style W3 fill:#ffccbc,stroke:#ff5722
```

## Buffer & Validation Strategy

```mermaid
graph TD
    EST[Estimation Result] --> CHECK{Check Risk Level}
    
    CHECK --> |Low Risk<br/>Few Dependencies| OPTION1[Option 1: Smart Buffer<br/>Built-in Estimation]
    CHECK --> |Medium Risk<br/>Some Complexity| OPTION2[Option 2: Rule-based<br/>Deterministic Validation]
    CHECK --> |High Risk<br/>Low Confidence| OPTION3[Option 3: LLM Validation<br/>Conditional Only]
    
    OPTION1 --> |Apply Buffer| CALC1[Calculate Buffer<br/>Complexity: +10-20%<br/>Dependencies: +5-12%<br/>Priority: +10%]
    OPTION2 --> |Apply Rules| CALC2[Apply Rules<br/>Consistency Check<br/>Dependency Validation<br/>Risk Assessment]
    OPTION3 --> |LLM Review| CALC3[LLM Validation<br/>Deep Analysis<br/>Risk Mitigation<br/>Expert Adjustment]
    
    CALC1 --> FINAL[Final Estimation<br/>with Buffer]
    CALC2 --> FINAL
    CALC3 --> FINAL
    
    FINAL --> EXPORT[Export to Excel<br/>+ SQLite Tracking]
    
    style CHECK fill:#fff3e0,stroke:#f57c00
    style OPTION1 fill:#e8f5e9,stroke:#388e3c
    style OPTION2 fill:#e3f2fd,stroke:#1976d2
    style OPTION3 fill:#fce4ec,stroke:#c2185b
    style FINAL fill:#f3e5f5,stroke:#7b1fa2
```

## Task Breakdown Process

```mermaid
stateDiagram-v2
    [*] --> ReceiveCategory
    
    ReceiveCategory --> AnalyzeContext: GraphRAG Insights
    AnalyzeContext --> IdentifyTasks: Break into Tasks
    
    IdentifyTasks --> CheckSize: Validate Size
    CheckSize --> SizeOK: Size < 21h
    CheckSize --> SplitTask: Size > 21h
    
    SplitTask --> IdentifyTasks: Create Sub-tasks
    
    SizeOK --> AssignRole: Backend/Frontend/Testing/Infra
    AssignRole --> SetComplexity: Low/Medium/High
    SetComplexity --> DefineDependencies: Task Dependencies
    DefineDependencies --> CreateSubNo: Generate Sub.No
    CreateSubNo --> AddMetadata: Premise, Remark, Notes
    
    AddMetadata --> [*]: Return Breakdown Results
```

## Role-specific Estimation Breakdown

```mermaid
graph LR
    subgraph "Task with Role=Backend"
        TASK[Backend Task<br/>2.5 mandays]
        TASK --> IMPL[Implement<br/>1.5 days<br/>60%]
        TASK --> FIX[FixBug<br/>0.5 days<br/>20%]
        TASK --> TEST[UnitTest<br/>0.5 days<br/>20%]
    end
    
    subgraph "Task with Role=Frontend"
        TASK2[Frontend Task<br/>2.0 mandays]
        TASK2 --> IMPL2[Implement<br/>1.2 days<br/>60%]
        TASK2 --> FIX2[FixBug<br/>0.4 days<br/>20%]
        TASK2 --> TEST2[UnitTest<br/>0.4 days<br/>20%]
    end
    
    subgraph "Task with Role=Testing"
        TASK3[Testing Task<br/>1.5 mandays]
        TASK3 --> IMPL3[Testing<br/>1.5 days<br/>100%]
    end
    
    subgraph "Excel Output"
        EXCEL[Sun Asterisk Format]
        EXCEL --> COL1[Backend: 2.5<br/>Implement: 1.5<br/>FixBug: 0.5<br/>UnitTest: 0.5]
        EXCEL --> COL2[Frontend: 2.0<br/>Implement: 1.2<br/>FixBug: 0.4<br/>UnitTest: 0.4]
        EXCEL --> COL3[Testing: 1.5<br/>Implement: 1.5]
    end
    
    IMPL --> EXCEL
    FIX --> EXCEL
    TEST --> EXCEL
    IMPL2 --> EXCEL
    FIX2 --> EXCEL
    TEST2 --> EXCEL
    IMPL3 --> EXCEL
    
    style TASK fill:#c8e6c9,stroke:#43a047
    style TASK2 fill:#bbdefb,stroke:#1976d2
    style TASK3 fill:#fff9c4,stroke:#f9a825
    style EXCEL fill:#f3e5f5,stroke:#7b1fa2
```

## Historical Data Integration

```mermaid
flowchart TB
    subgraph "Estimation with Few-shot Learning"
        NEW[New Task to Estimate]
        NEW --> SEARCH[Search Historical DB]
        
        SEARCH --> EMBED[Embedding Similarity]
        EMBED --> FILTER[Filter by Category + Role]
        FILTER --> RANK[Rank by Similarity]
        RANK --> TOP[Top 5 Similar Tasks]
        
        TOP --> PROMPT[Build Few-shot Prompt]
        PROMPT --> LLM[LLM Estimation]
        
        LLM --> EST[Estimated Result]
        EST --> SAVE[Save to History DB]
        SAVE --> LEARN[Continuous Learning]
    end
    
    subgraph "ChromaDB Storage"
        CHROMA[(estimation_history_db)]
        CHROMA --> COL1[task_description]
        CHROMA --> COL2[category]
        CHROMA --> COL3[role]
        CHROMA --> COL4[estimation_manday]
        CHROMA --> COL5[complexity]
        CHROMA --> COL6[metadata]
    end
    
    SEARCH -.->|Query| CHROMA
    SAVE -.->|Store| CHROMA
    
    style NEW fill:#e8f5e9,stroke:#388e3c
    style LLM fill:#fff3e0,stroke:#f57c00
    style EST fill:#e3f2fd,stroke:#1976d2
    style CHROMA fill:#fce4ec,stroke:#c2185b
```

## Export & Tracking System

```mermaid
graph TB
    RESULT[Estimation Results] --> FORMAT{Select Format}
    
    FORMAT --> |Enhanced| ENH[Enhanced Format<br/>Detailed Analysis]
    FORMAT --> |Sun Asterisk| SUN[Sun Asterisk Format<br/>Standard Template]
    
    ENH --> EXCEL1[Excel File<br/>Multiple Sheets]
    SUN --> EXCEL2[Excel File<br/>Sun Asterisk Layout]
    
    EXCEL1 --> SAVE[Save to result_est/]
    EXCEL2 --> SAVE
    
    SAVE --> TRACK[SQLite Tracker<br/>estimation_tracker.db]
    
    TRACK --> META[Store Metadata]
    META --> M1[estimation_id]
    META --> M2[timestamp]
    META --> M3[total_effort]
    META --> M4[file_path]
    META --> M5[format_type]
    
    TRACK --> HISTORY[Historical Reference]
    HISTORY --> QUERY[Query Past Estimations]
    QUERY --> ANALYZE[Comparative Analysis]
    
    style RESULT fill:#e8f5e9,stroke:#388e3c
    style EXCEL1 fill:#e3f2fd,stroke:#1976d2
    style EXCEL2 fill:#fff3e0,stroke:#f57c00
    style TRACK fill:#f3e5f5,stroke:#7b1fa2
```

## State Management Flow

```mermaid
stateDiagram-v2
    [*] --> started: Initialize State
    
    started --> orchestrator_running: Orchestrator Start
    orchestrator_running --> orchestrator_completed: Analysis Done
    
    orchestrator_completed --> breakdown_running: Assign Workers
    breakdown_running --> breakdown_completed: All Categories Done
    
    breakdown_completed --> estimation_running: Assign Estimators
    estimation_running --> estimation_completed: All Tasks Estimated
    
    estimation_completed --> validation_running: Conditional Validation
    validation_running --> validation_completed: High-risk Tasks Validated
    
    validation_completed --> synthesis_running: Aggregate Results
    synthesis_running --> completed: Final Results Ready
    
    completed --> [*]: Export Excel
    
    orchestrator_running --> orchestrator_failed: Error
    breakdown_running --> no_results: Error
    estimation_running --> no_results: Error
    validation_running --> no_results: Error
    
    orchestrator_failed --> [*]
    no_results --> [*]
```

## Key Features Summary

```mermaid
mindmap
  root((Enhanced<br/>Estimation<br/>Workflow))
    GraphRAG Integration
      Context Analysis
      Smart Insights
      Reference Documents
    Specialized Workers
      Task Breakdown
      Effort Estimation
      Risk Validation
    Smart Buffer System
      Complexity-based
      Risk-based
      Dependency-based
      Conditional Validation
    Historical Learning
      ChromaDB Storage
      Embedding Search
      Few-shot Prompting
    Multi-format Export
      Enhanced Format
      Sun Asterisk Format
      SQLite Tracking
    Quality Assurance
      Size Constraints
      Role Validation
      Confidence Scoring
      Risk Mitigation
```

---

## Notes

- **Orchestrator**: Phân tích task gốc và chia thành categories
- **Worker 1**: Break down mỗi category thành các sub-tasks cụ thể (<21h)
- **Worker 2**: Estimate effort với few-shot learning và smart buffer
- **Worker 3**: Validate conditional cho high-risk tasks only
- **Synthesizer**: Tổng hợp kết quả và tạo reports

**Buffer Strategy**:
- Option 1: Built-in smart buffer (all tasks)
- Option 2: Rule-based validation (low-risk tasks)
- Option 3: LLM validation (high-risk tasks only)

**Export Formats**:
- Enhanced: Detailed analysis với multiple sheets
- Sun Asterisk: Standard template theo quy định
