# SQL Test Agent - Architecture Diagrams

## 1. System Architecture Overview

```mermaid
graph TB
    subgraph "Agent Layer"
        Orchestrator[Orchestrator<br/>Main Workflow Controller]
        LLMAnalyzer[LLM Analyzer<br/>Difference Analysis]
        ConfigMgr[Config Manager<br/>Configuration & Credentials]
        ResultComp[Result Comparator<br/>String-level Comparison]
    end
    
    subgraph "MCP Server Layer"
        DBServer[Database MCP Server<br/>Oracle/PostgreSQL/MySQL]
        TransServer[Transformer MCP Server<br/>SQL Transformation Interface]
    end
    
    subgraph "External Tools"
        SQLTrans[SQL Transformation Agent<br/>bin/application wrapper]
    end
    
    subgraph "Data Sources"
        ParamFile[(parameters.properties<br/>Bind Variables)]
        MapperFiles[(MyBatis XML<br/>Mapper Files)]
        OracleDB[(Oracle DB<br/>Source)]
        PostgreDB[(PostgreSQL DB<br/>Target)]
        MySQLDB[(MySQL DB<br/>Target)]
    end
    
    subgraph "External Services"
        LLM[LLM API<br/>Claude/GPT]
    end
    
    Orchestrator --> ConfigMgr
    Orchestrator --> DBServer
    Orchestrator --> LLMAnalyzer
    Orchestrator --> ResultComp
    Orchestrator --> TransServer
    
    ConfigMgr --> ParamFile
    ConfigMgr --> MapperFiles
    
    DBServer --> OracleDB
    DBServer --> PostgreDB
    DBServer --> MySQLDB
    
    LLMAnalyzer --> LLM
    
    TransServer --> SQLTrans
    SQLTrans --> MapperFiles
    
    style Orchestrator fill:#4A90E2
    style LLMAnalyzer fill:#7B68EE
    style DBServer fill:#50C878
    style TransServer fill:#50C878
```

## 2. Main Validation Workflow

```mermaid
flowchart TD
    Start([START]) --> LoadConfig[Load Configuration]
    LoadConfig --> ValidatePrereq{Validate Prerequisites<br/>DB/Files/LLM}
    
    ValidatePrereq -->|Failed| Abort([ABORT])
    ValidatePrereq -->|Success| LoadBindVars[Load & Validate<br/>Bind Variables]
    
    LoadBindVars --> LoadSQL[Load SQL Queries<br/>from MyBatis Mappers]
    
    LoadSQL --> LoopStart{For Each<br/>SQL Query}
    
    LoopStart -->|Next Query| ExecOracle[Execute SQL<br/>on Oracle]
    LoopStart -->|All Done| GenReport[Generate Final Report]
    
    ExecOracle --> ExecTarget[Execute SQL<br/>on PostgreSQL/MySQL]
    
    ExecTarget --> Compare[Compare Results<br/>String-level]
    
    Compare -->|Match| MarkPassed[Mark as PASSED]
    MarkPassed --> LoopStart
    
    Compare -->|Differ| Analyze[Analyze Difference<br/>with LLM]
    
    Analyze --> GenGuidance[Generate<br/>Transformation Guidance]
    
    GenGuidance --> Transform[Invoke SQL Transformer<br/>with Guidance]
    
    Transform --> UpdateMapper[Update Mapper File<br/>with Transformed SQL]
    
    UpdateMapper --> CheckRetry{Retry Count<br/>< Max?}
    
    CheckRetry -->|Yes| ExecOracle
    CheckRetry -->|No| FlagManual[Flag for<br/>Manual Review]
    
    FlagManual --> LoopStart
    
    GenReport --> End([END])
    
    style Start fill:#90EE90
    style End fill:#90EE90
    style Abort fill:#FF6B6B
    style Compare fill:#FFD700
    style Analyze fill:#9370DB
    style Transform fill:#4A90E2
```

## 3. Detailed Validation Loop

```mermaid
sequenceDiagram
    participant O as Orchestrator
    participant DB as Database MCP Server
    participant RC as Result Comparator
    participant LA as LLM Analyzer
    participant TS as Transformer Server
    participant ST as SQL Transformer
    
    O->>DB: execute_query(Oracle, SQL, bind_vars)
    DB->>O: oracle_result
    
    O->>DB: execute_query(PostgreSQL, SQL, bind_vars)
    DB->>O: postgres_result
    
    O->>RC: compare_results(oracle_result, postgres_result)
    RC->>RC: Normalize data types & formats
    RC->>RC: String-level comparison
    RC->>O: comparison_result
    
    alt Results Match
        O->>O: Mark query as PASSED
    else Results Differ
        O->>LA: analyze_difference(SQL, comparison_result)
        LA->>LA: Identify root cause
        LA->>O: analysis + transformation_guidance
        
        O->>TS: transform_sql(SQL, guidance, mapper_path)
        TS->>ST: Invoke transformation
        ST->>TS: transformed_sql
        TS->>O: transformation_result
        
        O->>O: Update mapper file
        O->>O: Increment retry count
        
        alt Retry < Max
            O->>DB: Re-execute with new SQL
        else Max Retries Reached
            O->>O: Flag for manual review
        end
    end
```

## 4. Component Interaction Diagram

```mermaid
graph LR
    subgraph "Orchestrator Responsibilities"
        O1[Workflow Control]
        O2[Retry Logic]
        O3[Report Generation]
    end
    
    subgraph "Database MCP Server"
        D1[Connection Pool]
        D2[Query Execution]
        D3[Result Storage]
        D4[Metadata Access]
    end
    
    subgraph "Result Comparator"
        R1[Data Normalization]
        R2[String Comparison]
        R3[Difference Categorization]
    end
    
    subgraph "LLM Analyzer"
        L1[Root Cause Analysis]
        L2[Guidance Generation]
        L3[Confidence Scoring]
    end
    
    subgraph "Transformer Server"
        T1[Transformer Invocation]
        T2[Mapper File Update]
        T3[History Tracking]
    end
    
    O1 --> D2
    O1 --> R2
    O1 --> L2
    O1 --> T1
    O2 --> L3
    
    D2 --> D1
    D2 --> D3
    
    R2 --> R1
    R2 --> R3
    
    L2 --> L1
    L2 --> L3
    
    T1 --> T2
    T1 --> T3
    
    style O1 fill:#4A90E2
    style D2 fill:#50C878
    style R2 fill:#FFD700
    style L2 fill:#9370DB
    style T1 fill:#FF6B6B
```

## 5. Data Flow Diagram

```mermaid
flowchart LR
    subgraph Input
        Params[parameters.properties]
        Mappers[MyBatis XML Files]
        Config[agent_config.properties]
    end
    
    subgraph Processing
        Load[Load & Validate]
        Execute[Execute Queries]
        Compare[Compare Results]
        Analyze[Analyze Differences]
        Transform[Transform SQL]
    end
    
    subgraph Output
        Reports[Validation Reports]
        Updated[Updated Mappers]
        Logs[Execution Logs]
        Metrics[Performance Metrics]
    end
    
    Params --> Load
    Mappers --> Load
    Config --> Load
    
    Load --> Execute
    Execute --> Compare
    Compare --> Analyze
    Analyze --> Transform
    Transform --> Execute
    
    Compare --> Reports
    Transform --> Updated
    Execute --> Logs
    Execute --> Metrics
    
    style Load fill:#90EE90
    style Compare fill:#FFD700
    style Analyze fill:#9370DB
    style Transform fill:#4A90E2
```

## 6. Retry Strategy Decision Tree

```mermaid
graph TD
    Start{New Difference<br/>Detected}
    
    Start --> CheckIter{Iteration Count<br/>< Max Retries?}
    
    CheckIter -->|No| FlagManual[Flag for<br/>Manual Review]
    CheckIter -->|Yes| CheckDup{Duplicate<br/>Transformation?}
    
    CheckDup -->|Yes| FlagManual
    CheckDup -->|No| CheckConf{Confidence Score<br/>>= Threshold?}
    
    CheckConf -->|No| TryAlt{Alternative<br/>Approach Available?}
    CheckConf -->|Yes| CheckDiv{Results<br/>Diverging?}
    
    TryAlt -->|Yes| UseAlt[Use Alternative<br/>Approach]
    TryAlt -->|No| FlagManual
    
    CheckDiv -->|Yes| FlagManual
    CheckDiv -->|No| Retry[Retry with<br/>New Transformation]
    
    UseAlt --> Retry
    Retry --> End([Continue Loop])
    FlagManual --> End
    
    style Start fill:#FFD700
    style Retry fill:#90EE90
    style FlagManual fill:#FF6B6B
    style End fill:#87CEEB
```

## 7. Error Handling Flow

```mermaid
flowchart TD
    Error([Error Occurred]) --> Classify{Classify<br/>Error Type}
    
    Classify -->|Configuration| Fatal[Log Error<br/>ABORT Execution]
    Classify -->|Connection| CheckConn{Retry Count<br/>< Max?}
    Classify -->|Execution| LogSkip[Log Error<br/>Skip Query]
    Classify -->|Transformation| CheckAlt{Alternative<br/>Available?}
    Classify -->|System| Fatal
    Classify -->|Unknown| Fatal
    
    CheckConn -->|Yes| Backoff[Wait with<br/>Exponential Backoff]
    CheckConn -->|No| Fatal
    
    Backoff --> RetryConn[Retry Connection]
    RetryConn --> Continue([Continue])
    
    CheckAlt -->|Yes| TryAlt[Try Alternative<br/>Approach]
    CheckAlt -->|No| FlagReview[Flag for<br/>Manual Review]
    
    TryAlt --> Continue
    FlagReview --> Continue
    LogSkip --> Continue
    
    Fatal --> End([END])
    
    style Error fill:#FF6B6B
    style Fatal fill:#8B0000
    style Continue fill:#90EE90
    style End fill:#696969
```

## 8. Security Architecture

```mermaid
graph TB
    subgraph "Credential Sources"
        EnvVars[Environment Variables]
        EncFile[Encrypted Config File]
    end
    
    subgraph "Credential Manager"
        Loader[Credential Loader]
        Decrypt[Decryption Module]
        Validator[Credential Validator]
    end
    
    subgraph "Secure Storage"
        Memory[In-Memory Only<br/>No Disk Write]
        Sanitizer[Log Sanitizer]
    end
    
    subgraph "Database Connections"
        SSL[SSL/TLS Enabled]
        Pool[Connection Pool<br/>with Timeout]
    end
    
    EnvVars --> Loader
    EncFile --> Decrypt
    Decrypt --> Loader
    
    Loader --> Validator
    Validator --> Memory
    
    Memory --> SSL
    Memory --> Sanitizer
    
    SSL --> Pool
    
    style Decrypt fill:#FFD700
    style Memory fill:#90EE90
    style SSL fill:#4A90E2
    style Sanitizer fill:#FF6B6B
```

## 9. Performance Optimization Strategy

```mermaid
graph LR
    subgraph "Optimization Techniques"
        CP[Connection Pooling]
        BE[Batch Execution]
        PP[Parallel Processing]
        RC[Result Caching]
        LL[Lazy Loading]
        SR[Streaming Results]
    end
    
    subgraph "Performance Gains"
        RT[Reduced<br/>Connection Time]
        TP[Higher<br/>Throughput]
        LM[Lower<br/>Memory Usage]
        FE[Faster<br/>Execution]
    end
    
    CP --> RT
    BE --> TP
    PP --> FE
    RC --> FE
    LL --> LM
    SR --> LM
    
    RT --> Overall[Overall Performance<br/>Improvement]
    TP --> Overall
    LM --> Overall
    FE --> Overall
    
    style CP fill:#4A90E2
    style BE fill:#50C878
    style PP fill:#FFD700
    style Overall fill:#90EE90
```

## 10. Deployment Architecture

```mermaid
graph TB
    subgraph "Development Environment"
        DevAgent[SQL Test Agent]
        DevDB[(Dev Databases)]
    end
    
    subgraph "Testing Environment"
        TestAgent[SQL Test Agent]
        TestDB[(Test Databases)]
        CI[CI/CD Pipeline]
    end
    
    subgraph "Production Environment"
        ProdAgent[SQL Test Agent]
        ProdOracle[(Oracle Production)]
        ProdPostgres[(PostgreSQL Production)]
        Monitor[Monitoring & Alerting]
    end
    
    subgraph "External Services"
        LLMService[LLM API Service]
        LogAgg[Log Aggregation]
    end
    
    DevAgent --> TestAgent
    TestAgent --> CI
    CI --> ProdAgent
    
    DevAgent --> DevDB
    TestAgent --> TestDB
    ProdAgent --> ProdOracle
    ProdAgent --> ProdPostgres
    
    DevAgent --> LLMService
    TestAgent --> LLMService
    ProdAgent --> LLMService
    
    ProdAgent --> Monitor
    ProdAgent --> LogAgg
    
    style ProdAgent fill:#4A90E2
    style Monitor fill:#FF6B6B
    style LLMService fill:#9370DB
```
