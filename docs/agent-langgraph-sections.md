# Compass Agent LangGraph Sections

These Mermaid graphs split the Compass agent ecosystem into smaller LangGraph-style views. Shared node names, such as `CompassRouter`, `ApprovalGate`, and `AuditEnd`, indicate connection points between graphs.

## 1. Gateway And Routing

```mermaid
flowchart TD
  START([START<br/>GPT Action / Local UI / Scheduler])
  Intake["CompassIntake<br/>normalize task, user_id, context"]
  ApprovalGate{"ApprovalGate<br/>require_approval?"}
  ApprovalQueue["ApprovalQueue<br/>create approval request"]
  CompassRouter{"CompassRouter<br/>agent_id + task"}
  AuditEnd([AuditEnd<br/>audit + response])

  START --> Intake --> ApprovalGate
  ApprovalGate -- "yes" --> ApprovalQueue --> AuditEnd
  ApprovalGate -- "no" --> CompassRouter

  CompassRouter -- "rules_engine" --> PolicyEntry["PolicyEntry"]
  CompassRouter -- "self_manage / assessment / self_trainer" --> WellbeingEntry["WellbeingEntry"]
  CompassRouter -- "mail_manager / economic_manager" --> FinanceEntry["FinanceEntry"]
  CompassRouter -- "task_commander / administrative" --> OperationsEntry["OperationsEntry"]
  START --> StorageEntry["StorageEntry"]

  classDef compass fill:#e0f2fe,stroke:#0369a1,color:#0f172a;
  classDef terminal fill:#f8fafc,stroke:#334155,stroke-width:2px,color:#0f172a;
  class START,AuditEnd terminal;
  class Intake,ApprovalGate,ApprovalQueue,CompassRouter,PolicyEntry,WellbeingEntry,FinanceEntry,OperationsEntry,StorageEntry compass;
```

## 2. Policy And Approval Loop

```mermaid
flowchart TD
  PolicyEntry["PolicyEntry<br/>from CompassRouter"]
  RulesEngine["rules_engine<br/>evaluate policy / workflow"]
  Decision{"RuleDecision"}
  CompassIntake["CompassIntake<br/>policy JSON back to Compass"]
  ApprovalQueue["ApprovalQueue<br/>proposed action"]
  ApprovalsApi["approvals_api<br/>pending -> approved/rejected"]
  AuditEnd([AuditEnd<br/>audit + response])

  PolicyEntry --> RulesEngine --> Decision
  Decision -- "safe / informational" --> AuditEnd
  Decision -- "needs routing" --> CompassIntake
  Decision -- "needs human approval" --> ApprovalQueue --> ApprovalsApi --> AuditEnd

  classDef policy fill:#fef3c7,stroke:#b45309,color:#0f172a;
  classDef compass fill:#e0f2fe,stroke:#0369a1,color:#0f172a;
  classDef terminal fill:#f8fafc,stroke:#334155,stroke-width:2px,color:#0f172a;
  class PolicyEntry,RulesEngine,Decision policy;
  class CompassIntake,ApprovalQueue,ApprovalsApi compass;
  class AuditEnd terminal;
```

## 3. Wellbeing, Assessment, Training

```mermaid
flowchart TD
  WellbeingEntry["WellbeingEntry<br/>from CompassRouter"]
  LocalStart{"LocalAgentRunning?<br/>ports 8001 / 8002 / 8008"}
  Autostart["AutostartLocalAgent<br/>start dormant service"]
  SelfManage["self_manage<br/>today plan + reminders"]
  Assessment["personal_Assessment<br/>evidence + recommendations"]
  SelfTrainer["self_trainer<br/>sessions + history + progress"]
  AuditEnd([AuditEnd<br/>audit + response])

  WellbeingEntry --> LocalStart
  LocalStart -- "no" --> Autostart --> LocalStart
  LocalStart -- "self_manage ready" --> SelfManage --> AuditEnd
  LocalStart -- "assessment ready" --> Assessment --> AuditEnd
  LocalStart -- "self_trainer ready" --> SelfTrainer --> AuditEnd

  SelfTrainer -- "assessment feedback" --> Assessment
  Assessment -- "recommendations / context" --> SelfManage

  classDef wellbeing fill:#dcfce7,stroke:#15803d,color:#0f172a;
  classDef compass fill:#e0f2fe,stroke:#0369a1,color:#0f172a;
  classDef terminal fill:#f8fafc,stroke:#334155,stroke-width:2px,color:#0f172a;
  class WellbeingEntry,LocalStart,Autostart compass;
  class SelfManage,Assessment,SelfTrainer wellbeing;
  class AuditEnd terminal;
```

## 4. Finance And Mail Pipeline

```mermaid
flowchart TD
  FinanceEntry["FinanceEntry<br/>from CompassRouter"]
  LocalStart{"LocalAgentRunning?<br/>economic_manager port 8005"}
  Autostart["AutostartLocalAgent<br/>start economic_manager"]
  EconomicManager["economic_manager<br/>finance memory + imports + reports"]
  MailManager["mail_manager<br/>Gmail ingest + financial items"]
  Gmail[(Gmail)]
  StatementCsv[(Statement CSV)]
  AuditEnd([AuditEnd<br/>audit + response])

  FinanceEntry -- "economic_manager" --> LocalStart
  LocalStart -- "no" --> Autostart --> LocalStart
  LocalStart -- "ready" --> EconomicManager --> AuditEnd

  FinanceEntry -- "mail_manager" --> MailManager --> AuditEnd
  EconomicManager -- "sync_mail_financial_items" --> MailManager
  MailManager -- "financial_items" --> EconomicManager
  MailManager -- "ingest" --> Gmail
  EconomicManager -- "import_csv / sources" --> StatementCsv

  classDef finance fill:#ffe4e6,stroke:#be123c,color:#0f172a;
  classDef compass fill:#e0f2fe,stroke:#0369a1,color:#0f172a;
  classDef external fill:#f1f5f9,stroke:#64748b,stroke-dasharray:4 3,color:#0f172a;
  classDef terminal fill:#f8fafc,stroke:#334155,stroke-width:2px,color:#0f172a;
  class FinanceEntry,LocalStart,Autostart compass;
  class EconomicManager,MailManager finance;
  class Gmail,StatementCsv external;
  class AuditEnd terminal;
```

## 5. Operations And Conversation

```mermaid
flowchart TD
  OperationsEntry["OperationsEntry<br/>from CompassRouter"]
  TaskCommander["TaskCommander<br/>tasks + recurrences + instances"]
  Administrative["administrative_agent<br/>obligations + cases + documents"]
  Anchor["anchor<br/>voice/chat check-ins"]
  Calendar[(Calendar)]
  Government[(Government portal)]
  AuditEnd([AuditEnd<br/>audit + response])

  OperationsEntry -- "task_commander" --> TaskCommander --> AuditEnd
  OperationsEntry -- "administrative" --> Administrative --> AuditEnd

  TaskCommander -- "calendar sync / reminders" --> Calendar
  Anchor -- "reminder JSON" --> Calendar
  Administrative -- "forms / case docs" --> Government

  classDef ops fill:#ede9fe,stroke:#6d28d9,color:#0f172a;
  classDef conversation fill:#fce7f3,stroke:#be185d,color:#0f172a;
  classDef external fill:#f1f5f9,stroke:#64748b,stroke-dasharray:4 3,color:#0f172a;
  classDef terminal fill:#f8fafc,stroke:#334155,stroke-width:2px,color:#0f172a;
  class OperationsEntry,TaskCommander,Administrative ops;
  class Anchor conversation;
  class Calendar,Government external;
  class AuditEnd terminal;
```

## 6. Compass Local State And Ecosystem Hub

```mermaid
flowchart TD
  StorageEntry["StorageEntry<br/>from START / local UI"]
  ContextService["context_service<br/>morning context"]
  Conversations["conversation events<br/>summaries"]
  DailyPlan["daily_plan<br/>saved plan"]
  LocalTasks["local task proposals<br/>mentioned / proposed / approved"]
  EcosystemHub["ecosystem_hub<br/>meta graph state"]
  GraphSeed["ecosystem-hub.seed.json<br/>nodes + edges"]
  Exports["app/exports<br/>latest + revisions"]
  AuditEnd([AuditEnd<br/>stored state / response])

  StorageEntry --> ContextService --> AuditEnd
  StorageEntry --> Conversations --> AuditEnd
  StorageEntry --> DailyPlan --> AuditEnd
  StorageEntry --> LocalTasks --> AuditEnd
  StorageEntry --> EcosystemHub --> AuditEnd

  GraphSeed --> EcosystemHub
  EcosystemHub --> Exports

  classDef storage fill:#f0fdfa,stroke:#0f766e,color:#0f172a;
  classDef terminal fill:#f8fafc,stroke:#334155,stroke-width:2px,color:#0f172a;
  class StorageEntry,ContextService,Conversations,DailyPlan,LocalTasks,EcosystemHub,GraphSeed,Exports storage;
  class AuditEnd terminal;
```
