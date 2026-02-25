# 项目架构文档 v0.1

> 文案写作助手 - 架构设计说明

---

## 1. 项目整体架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              前端 (Frontend)                                │
│                         React + TypeScript + Vite                          │
│                   端口 3000，代理 /api → 127.0.0.1:8000                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              后端 (Backend)                                │
│                         FastAPI + LangGraph                                 │
│                                                                             │
│  ┌──────────────────────┐    ┌──────────────────────┐                     │
│  │   文案 Agent (v1/v2) │    │      小说 Agent       │                     │
│  │   仿写/分析/聊天      │    │   参考学习 + 章节生成   │                     │
│  └──────────────────────┘    └──────────────────────┘                     │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    LangGraph Workflow Engine                        │  │
│  │                    (状态机 + Checkpoint Memory)                     │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │
│  │ Config      │  │ Logger      │  │ Artifacts   │  │ LLM Clients │      │
│  │ (环境变量)   │  │ (日志系统)   │  │ (产物存储)   │  │ (DashScope) │      │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘      │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Agent 数量与功能

本项目包含 **2 个主要 Agent**，分别处理不同的任务：

### 2.1 文案 Agent (Copywriting Agent)

**文件**: `backend/src/agent/graph.py`

负责口播文案的仿写、分析与创作。采用 **双 Pipeline 设计**：

#### Pipeline v1 (Ten-Move 仿写)

```
intent_analysis → [路由] → 
    ├─ copy_flow: reverse_engineer → move_plan → writing → verify → proofread → END
    ├─ analysis_flow: breakdown → analysis_output → END
    └─ chat_flow: simple_chat → END
```

| 节点 | 功能 |
|------|------|
| `intent_analysis` | 意图分析，判断用户是仿写、分析还是聊天 |
| `reverse_engineer` | 逆向工程：解析参考文案的结构、策略、风格约束 |
| `move_plan` | 动态规划：选择/排序/融合 Move（叙述单元） |
| `writing` | 写作执行：基于 Move 规划生成文案 |
| `verify` | 规则验收：确定性检查（长度、结构） |
| `proofread` | LLM 评测：质量评分 + 迭代控制 |
| `breakdown` | 文案拆解：结构化分析（目标/心理/表达等） |
| `simple_chat` | 闲聊模式：直接 LLM 回复 |

#### Pipeline v2 (Skeleton v2 骨架)

```
intent_analysis → [路由] → v2_preprocess → v2_analyst → v2_normalizer → 
v2_entity_mapper → v2_creator → v2_qc → [QC Gate] → proofread → END
```

| 节点 | 功能 |
|------|------|
| `v2_preprocess` | 确定性预处理：实体抽取、风险词识别、句子分割 |
| `v2_analyst` | LLM 分析：生成 Skeleton v2 骨架 |
| `v2_normalizer` | 规范化：标准化意图和修辞标签 |
| `v2_entity_mapper` | 实体映射：建立源→目标实体映射表 |
| `v2_creator` | 创作者：逐 Move 渲染文案，生成 coverage_map |
| `v2_qc` | **质量审核门禁**：确定性检查 + 反馈 |

---

### 2.2 小说 Agent (Novel Agent)

**文件**: `backend/src/novel/graph.py`

负责基于参考小说生成新故事：

```
load_reference → plan_story → write_chapter → verify_fluency → [路由] → finalize → END
     │                  │              │               │
     │                  │              │               ├─ revise → write_chapter
     │                  │              │               └─ continue → chapter_decision
     │                  │              │                                   │
     │                  │              │                                   ├─ next_chapter → prepare_next_chapter
     │                  │              │                                   └─ finalize
     │                  │              │
     │                  │              └─ 循环：每章重复生成+验证
     │                  │
     └─ 加载小说 + 提取 Move 结构
```

| 节点 | 功能 |
|------|------|
| `load_reference` | 加载参考小说 + **提取 Move Codebook** |
| `plan_story` | 规划故事框架：生成章节结构 |
| `write_chapter` | 逐章生成：参考 Move 叙述方式 |
| `verify_fluency` | 通顺性检查：LLM 评分 |
| `finalize` | 合并章节为最终故事 |

---

## 3. 记忆系统 (Memory)

### 3.1 架构

项目使用 **LangGraph Checkpoint Memory** 实现状态持久化：

```python
# backend/src/agent/graph.py:195-197
if with_memory:
    memory = MemorySaver()
    graph = workflow.compile(checkpointer=memory)
```

```python
# backend/src/novel/graph.py:121-123
if with_memory:
    memory = MemorySaver()
    graph = workflow.compile(checkpointer=memory)
```

### 3.2 工作原理

1. **基于 Thread ID**: 每个会话使用唯一的 `thread_id` 作为记忆键
2. **状态快照**: 每次节点执行完成后，完整状态被序列化存储
3. **跨请求恢复**: 相同 `thread_id` 的请求会加载历史状态继续执行

### 3.3 使用方式

```python
# API 调用时传入 thread_id
config = {
    "configurable": {"thread_id": "user_123_session"},
    "recursion_limit": 100,
}
final_state = graph.invoke(initial_state, config)
```

---

## 4. Move Codebook 系统

### 4.1 概念

**Move** 是故事/文案中的最小叙事单元，代表一个微观修辞意图（如"建立氛围"、"引入冲突"等）。

### 4.2 提取流程

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  参考小说文本    │───▶│ Move Extractor  │───▶│  Move Codebook  │
│ (诡秘之主等)     │    │   (LLM 调用)     │    │  (结构化 JSON)   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### 4.3 Codebook 结构

```json
{
    "moves": [
        {
            "move_id": 1,
            "name": "setup",
            "description": "建立故事的世界和氛围",
            "chapters": [1],
            "core_idea": "在一个疲惫的清晨，主角开始了新的一天",
            "estimated_words": {"min": 300, "max": 500},
            "emotional_beats": ["calm", "quiet", "introspection"]
        },
        {
            "move_id": 2,
            "name": "introduce_character",
            "description": "引入一个改变故事的人物",
            ...
        }
    ],
    "story_framework": "三幕结构：日常 → 相遇与冲突 → 变化与成长",
    "pacing": {
        "setup": 0.15,
        "rising_action": 0.50,
        "climax": 0.20,
        "resolution": 0.15
    }
}
```

### 4.4 应用方式

1. **小说生成**: 规划章节时选择对应 Move，确保叙事结构合理
2. **文案仿写**: 类似地，将参考文案分解为 Move 序列，学习其结构

---

## 5. 中间表示 (IR)

### 5.1 Story IR (故事规划)

小说 Agent 的中间表示：

```json
{
    "story_title": "青苔信箱",
    "story_concept": "关于失去和重新开始的故事",
    "chapters": [
        {
            "chapter_id": 1,
            "title": "雨声比记忆先回来",
            "core_idea": "主角在雨中醒来，失去记忆",
            "target_word_count": 400,
            "reference_moves": ["setup"],
            "notes": ""
        }
    ]
}
```

### 5.2 Skeleton v2 (文案骨架)

文案 Agent v2 的中间表示：

```json
{
    "move_sequence": [
        {"move_id": 1, "primary_intent": "hook", "micro_rhetoric": {"tag": "question"}},
        {"move_id": 4, "primary_intent": "value_prop", "micro_rhetoric": {"tag": "contrast"}},
        {"move_id": 9, "primary_intent": "cta", "micro_rhetoric": {"tag": "direct"}}
    ],
    "must_cover_points": [
        {
            "point_id": "p1",
            "content": "产品原价 199 元",
            "importance": "p0",
            "verification": "hard",
            "source_fact": "199元",
            "mention_hints": ["199", "一百九十九"]
        }
    ]
}
```

---

## 6. 审核系统 (QC)

### 6.1 v2 QC 节点 (`qc_v2_node`)

位置: `backend/src/agent/nodes_v2.py:637-836`

#### 检查项

| 检查项 | 类型 | 说明 |
|--------|------|------|
| **泄漏检查** | 确定性 | transfer 模式下检查是否泄漏源品牌/价格 |
| **Specs 锚定** | 确定性 | 检查数值是否来自 specs 事实 |
| **合规检查** | 确定性 | 检查绝对化用语（第一、100%、根治等） |
| **必选 Move** | 确定性 | 检查 move 1/4/9 是否有内容 |
| **覆盖检查** | 确定性 | 检查 p0-hard 信息点是否覆盖 |

#### 覆盖检查逻辑

```
p0-hard 点:
  ✓ phrase (原文证据) 必须出现在最终文案
  ✓ audit_token (事实词) 必须出现在最终文案

p0-soft 点:
  ⚠ 只警告，不阻断
```

#### 决策流程

```
QC 结果
    │
    ├─ issues > 0 ──→ failed_move_ids > 0 ──→ "revise" → 重写指定 Move
    │                     │
    │                     └─ 0 ──→ "proceed" → 继续 proofread
    │
    └─ issues = 0 ──→ draft_len >= 30 ──→ "proceed" → 继续 proofread
                        │
                        └─ < 30 ──→ "revise" → 重写
```

### 6.2 通顺性检查 (小说)

位置: `backend/src/novel/nodes.py:325-357`

- 基于 LLM 评分 (1-10 分)
- 检查语法、表述、逻辑、衔接
- 迭代控制：最多重写 2 次

---

## 7. 日志系统

### 7.1 架构

位置: `backend/src/core/logger.py`

```
┌────────────────────────────────────────────────────────────┐
│                    Python logging 模块                      │
├────────────────────────────────────────────────────────────┤
│  ┌──────────────────┐        ┌──────────────────┐         │
│  │ Console Handler  │        │  File Handler   │         │
│  │ (INFO 及以上)     │        │  (DEBUG 及以上)  │         │
│  ├──────────────────┤        ├──────────────────┤         │
│  │ 格式化: 简洁      │        │ 格式化: 完整      │         │
│  │ 屏蔽堆栈信息      │        │ 保留堆栈信息      │         │
│  └──────────────────┘        └──────────────────┘         │
└────────────────────────────────────────────────────────────┘
```

### 7.2 Handler 配置

| Handler | 级别 | 格式化 | 用途 |
|---------|------|--------|------|
| Console | INFO | 简洁格式 | 生产环境/控制台 |
| File | DEBUG | 完整格式（含堆栈） | `logs/app.log` |

### 7.3 日志文件轮转

- 单文件大小: 10MB
- 保留备份: 5 个
- 编码: UTF-8

### 7.4 现行日志示例

```
2026-02-21 20:05:44 | INFO     | 文案写作助手 API 服务启动
2026-02-21 20:05:44 | INFO     | 模型: qwen-plus
2026-02-21 20:06:15 | INFO     | 收到小说生成请求: concept=关于失去和重新开始的故事...
2026-02-21 20:06:15 | INFO     | ✅ 工作流创建完成 (with memory)
2026-02-21 20:06:15 | INFO     | 加载参考小说: 诡秘之主
2026-02-21 20:06:41 | INFO     | ✅ 成功提取 5 个 Move
2026-02-21 20:06:41 | INFO     | ✅ Move Codebook 已准备: 5 个 Move
2026-02-21 20:07:07 | INFO     | ✅ 故事规划完成: 5 章
2026-02-21 20:07:26 | INFO     | ✅ 章节生成完成，字数: 1032
2026-02-21 20:07:29 | INFO     | ✅ 通顺性检查完成: 得分 9.2
```

### 7.5 建议增强

当前日志可进一步细化，增加：

1. **Move Codebook 内容**: 记录提取到的 move 名称、描述
2. **IR 结构**: 记录生成的 story_ir / skeleton_v2 JSON
3. **LLM 调用详情**: 
   - prompt token 数量
   - response token 数量
   - 耗时
4. **QC 详细报告**:
   - coverage 覆盖率
   - 具体失败点
5. **写入产物路径**: 生成文件保存位置

---

## 8. 环境配置

### 8.1 文件结构

```
writer/
├── backend/
│   ├── .env              # 后端配置
│   ├── .env.example      # 配置模板
│   └── src/
│       ├── core/          # 公共模块
│       ├── agent/         # 文案 Agent
│       └── novel/         # 小说 Agent
└── frontend/             # 前端 (无独立 env)
```

### 8.2 核心配置项

| 变量 | 说明 | 必填 |
|------|------|------|
| `LLM_PROVIDER` | dashscope / openai | ✅ |
| `DASHSCOPE_API_KEY` | 通义千问密钥 | ✅ |
| `MODEL_NAME` | 模型名称 | ✅ |
| `MODEL_TEMPERATURE` | 温度参数 | - |
| `LOG_LEVEL` | 日志级别 | - |
| `LOG_FILE_PATH` | 日志文件 | - |
| `API_HOST` / `API_PORT` | 服务地址 | - |
| `MAX_ITERATIONS` | 最大迭代次数 | - |

---

## 9. 数据流总结

### 9.1 小说生成流程

```
用户请求
    │
    ▼
load_reference
    │  ┌──────────────────────────────┐
    ├──▶ 加载小说文本                  │
    │  └──────────────────────────────┘
    │  ┌──────────────────────────────┐
    └──▶ extract_moves_from_novel     │
        │ (LLM 提取 Move 结构)         │
        │ 输出: Move Codebook          │
        └──────────────────────────────┘
    │
    ▼
plan_story
    │ 输入: user_input + Move Codebook
    │ 输出: Story IR (章节规划)
    │
    ▼
[循环: 每章]
    │
    ├─ write_chapter
    │   │ 输入: 章节规划 + 前文上下文
    │   │ 输出: 章节文本
    │   │
    │   ▼
    │ verify_fluency
    │   │ 输入: 章节文本
    │   │ 输出: 通顺性得分 (LLM 评测)
    │   │
    │   ▼
    │ [迭代控制: 不通过则重写, 最多2次]
    │
    ▼
finalize
    合并所有章节 → 最终故事
    │
    ▼
返回结果
```

### 9.2 文案生成流程 (v2)

```
用户请求
    │
    ▼
v2_preprocess
    │ 确定性处理: 实体/风险词/分句
    │ 输出: preprocess_result
    │
    ▼
v2_analyst
    │ LLM 分析: 生成 Skeleton v2
    │ 输出: skeleton_v2
    │
    ▼
v2_normalizer
    │ 规范化: 意图/修辞标签
    │
    ▼
v2_entity_mapper
    │ 实体映射: source → target
    │ 输出: entity_mapping
    │
    ▼
v2_creator
    │ LLM 渲染: 逐 Move 生成
    │ 输出: draft_copy + coverage_map
    │
    ▼
v2_qc
    │ 确定性检查: 泄漏/锚定/合规/覆盖
    │ 输出: qc_report
    │
    ▼
[QC Gate]
    ├─ 通过 → proofread (LLM 评测)
    └─ 失败 → revise → 重写指定 Move
              │
              └─ 迭代控制: 最多 MAX_ITERATIONS 次
    │
    ▼
返回最终文案
```

---

## 10. 附录

### 10.1 目录结构

```
backend/src/
├── agent/
│   ├── graph.py           # 文案 Agent 主入口
│   ├── nodes.py           # v1 节点实现
│   ├── nodes_v2.py        # v2 节点实现
│   ├── state.py           # Agent 状态定义
│   ├── prompts.py         # v1 Prompt 模板
│   ├── skeleton_v2.py     # v2 骨架结构
│   ├── codebooks_v0.py    # v2 Codebook 定义
│   ├── ten_move.py        # Ten-Move 逻辑
│   └── ...
├── novel/
│   ├── graph.py           # 小说 Agent 主入口
│   ├── nodes.py           # 节点实现
│   ├── state.py           # 状态定义
│   ├── prompts.py         # Prompt 模板
│   ├── move_extractor.py  # Move 提取器
│   ├── loader.py          # 小说加载器
│   └── ...
├── api/
│   ├── server.py          # FastAPI 应用
│   ├── routes.py          # API 路由
│   └── schemas.py         # 请求/响应模型
└── core/
    ├── config.py          # 配置管理
    ├── logger.py          # 日志系统
    └── artifacts.py       # 产物管理
```

### 10.2 依赖项

- **LangGraph**: 工作流引擎 + Checkpoint Memory
- **LangChain Community**: LLM 客户端 (ChatTongyi, ChatOpenAI)
- **FastAPI**: Web 框架
- **Pydantic**: 数据验证
- **Python logging**: 日志基础设施
