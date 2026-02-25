# 小说写作助手 - 基于 LangGraph 的多章节故事生成系统

一个强大的 AI 小说生成系统，支持自动提取参考小说的叙述结构（Move Codebook），规划故事框架，逐章生成内容，并验证流畅性。

## ✨ 核心功能

### 🎯 故事生成工作流

```
加载参考小说
    ↓
提取 Move 结构（叙述模式）
    ↓
规划故事框架（章节规划）
    ↓
逐章生成内容（带迭代）
    ↓
验证语句流畅性
    ↓
最终合并完整故事
```

### 🚀 主要特性

- **参考学习**：从参考小说自动提取 Move Codebook（5 种叙述模式）
- **智能规划**：基于 Move 结构规划新故事的章节框架
- **逐章生成**：支持并行和迭代的章节文本生成
- **质量检查**：自动验证每章的语句流畅性
- **多模式API**：支持同步和流式两种执行方式
- **优雅降级**：无 API Key 时使用智能默认值，保证流程可运行
- **会话管理**：基于 LangGraph 的记忆功能，支持会话持久化

## 📦 安装

### 前置条件

- Python 3.10+
- uv（包管理工具）

### 快速开始

```bash
# 1. 进入项目目录
cd /Users/sumoer/Desktop/playbook/copywriter

# 2. 安装依赖（使用 uv）
uv sync

# 3. 激活虚拟环境
source .venv/bin/activate

# 4. 运行测试验证安装
python test_phase2.py      # 测试核心功能
python test_phase3_api.py  # 测试 API 接口
```

## 🔧 配置

### 环境变量 (.env)

```env
# DashScope LLM 配置
DASHSCOPE_API_KEY=your_api_key_here
MODEL_NAME=qwen-plus

# 服务配置
API_HOST=0.0.0.0
API_PORT=8000

# 日志配置
LOG_LEVEL=INFO
```

**注意**：如果没有 DASHSCOPE_API_KEY，系统会自动使用优质的默认值继续执行。

### 数据库

项目从 SQLite 数据库加载参考小说：

```
/Users/sumoer/Desktop/playbook/qidian-spider/novels.db
```

**数据库表结构：**
- `books`: 图书信息（id, name, author）
- `chapters`: 章节内容（book_id, chapter_num, chapter_name, content）

## 💻 使用方法

### 方法 1：API 接口（推荐）

#### 启动服务器

```bash
source .venv/bin/activate
uvicorn src.api.server:app --reload --host 0.0.0.0 --port 8000
```

#### 访问文档

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

#### 同步 API 调用

```bash
curl -X POST http://localhost:8000/api/v1/novel/generate \
  -H "Content-Type: application/json" \
  -d '{
    "user_input": "关于失去和重新开始的故事",
    "reference_novel_title": "诡秘之主",
    "user_style": "温暖、治愈",
    "target_chapters": 5
  }'
```

**响应示例：**
```json
{
  "success": true,
  "story_title": "关于失去和重新开始的故事",
  "final_story": "# 关于失去和重新开始的故事\n\n## 概念\n...",
  "chapters_count": 5,
  "iterations": 15,
  "error": null
}
```

#### 流式 API 调用

```bash
curl -X POST http://localhost:8000/api/v1/novel/generate/stream \
  -H "Content-Type: application/json" \
  -d '{
    "user_input": "关于冒险和发现的故事",
    "reference_novel_title": "诡秘之主",
    "target_chapters": 3
  }' \
  -N
```

**流式事件类型：**
- `node_start` - 节点开始执行
- `node_end` - 节点完成
- `progress` - 章节生成进度
- `token` - LLM 输出的 token
- `done` - 生成完成
- `error` - 发生错误

### 方法 2：Python 代码调用

```python
import asyncio
from src.novel.graph import run_novel_agent, run_novel_agent_stream

# 同步执行
result = asyncio.run(run_novel_agent(
    user_input="关于失去和重新开始的故事",
    reference_novel_title="诡秘之主",
    user_style="温暖、治愈",
    target_chapters=5,
    thread_id="my_story_001"
))

print(f"生成成功: {result['success']}")
print(f"故事标题: {result['story_title']}")
print(f"字数: {len(result['final_story'])}")

# 流式执行
async for event in run_novel_agent_stream(
    user_input="关于冒险的故事",
    reference_novel_title="诡秘之主",
    target_chapters=3
):
    if event['type'] == 'node_start':
        print(f"开始: {event['node']}")
    elif event['type'] == 'progress':
        print(f"第 {event['chapter']} 章: {event['text_snippet'][:50]}...")
    elif event['type'] == 'done':
        print("完成！")
```

## 📁 项目结构

```
copywriter/
├── backend/
│   └── src/
│       ├── novel/                 # 小说生成模块（NEW）
│       │   ├── state.py           # 状态定义（17个字段）
│       │   ├── loader.py          # SQLite 数据加载
│       │   ├── prompts.py         # LLM Prompt 模板
│       │   ├── move_extractor.py  # Move 结构提取
│       │   ├── nodes.py           # 工作流节点（5个）
│       │   └── graph.py           # LangGraph 工作流
│       │
│       ├── api/
│       │   ├── server.py          # FastAPI 应用
│       │   ├── routes.py          # API 路由（已扩展）
│       │   └── schemas.py         # Pydantic 模型（已扩展）
│       │
│       ├── agent/                 # 原有文案生成模块
│       ├── core/                  # 配置和日志
│       └── __init__.py
│
├── test_phase2.py                 # Phase 2 测试（工作流）
├── test_phase3_api.py             # Phase 3 测试（API）
├── pyproject.toml                 # 项目配置
├── .env                           # 环境变量
└── README.md                      # 本文件
```

## 🏗️ 实现阶段

### ✅ Phase 1: 数据层和状态定义

- [x] SQLite 数据加载（loader.py）
- [x] 状态定义（state.py）- 17 个字段
- [x] Prompt 模板（prompts.py）- 4 个 LLM Prompt
- [x] Move 提取器（move_extractor.py）
- [x] 测试套件（test_phase1.py）

**关键文件：**
- `backend/src/novel/loader.py` - 从数据库加载参考小说
- `backend/src/novel/state.py` - NovelAgentState TypedDict
- `backend/src/novel/prompts.py` - 4 个 Prompt 模板

### ✅ Phase 2: 工作流图和节点实现

- [x] 5 个工作流节点
  - `load_reference_node` - 加载参考小说
  - `plan_story_node` - 规划故事框架
  - `write_chapter_node` - 生成章节
  - `verify_fluency_node` - 验证流畅性
  - `finalize_node` - 合并章节
- [x] LangGraph 状态图
- [x] 条件路由和循环控制
- [x] 记忆管理（MemorySaver）
- [x] 测试套件（test_phase2.py）

**关键文件：**
- `backend/src/novel/nodes.py` - 5 个异步节点函数
- `backend/src/novel/graph.py` - 完整工作流

### ✅ Phase 3: API 集成

- [x] 请求/响应数据模型
- [x] 同步 API 端点（/novel/generate）
- [x] 流式 API 端点（/novel/generate/stream）
- [x] 请求验证
- [x] 错误处理
- [x] API 文档（Swagger/ReDoc）
- [x] 测试套件（test_phase3_api.py）

**关键文件：**
- `backend/src/api/schemas.py` - Pydantic 模型
- `backend/src/api/routes.py` - API 路由

## 🧪 测试

### 运行测试

```bash
# 进入虚拟环境
source .venv/bin/activate

# Phase 2: 工作流测试（7-8 分钟）
python test_phase2.py

# Phase 3: API 测试（8-10 分钟）
python test_phase3_api.py
```

### 测试覆盖

| 阶段 | 测试项 | 状态 |
|------|--------|------|
| Phase 2 | 节点导入 | ✅ |
| Phase 2 | 图创建 | ✅ |
| Phase 2 | 图可视化 | ✅ |
| Phase 2 | 同步执行 | ✅ |
| Phase 2 | 流式执行 | ✅ |
| Phase 3 | 健康检查 | ✅ |
| Phase 3 | 同步 API | ✅ |
| Phase 3 | 流式 API | ✅ |
| Phase 3 | 请求验证 | ✅ |
| Phase 3 | API 文档 | ✅ |

## 📊 工作流示例

### 执行流程

1. **加载参考小说** (`load_reference_node`)
   - 从数据库加载"诡秘之主"
   - 提取 Move Codebook（5 种叙述模式）
   - 如果 API 不可用，使用默认的 Move 结构

2. **规划故事** (`plan_story_node`)
   - 基于用户概念和 Move 规划 5 章
   - 每章设定标题、核心思想、字数目标
   - 如果 LLM 不可用，使用模板规划

3. **生成章节** (`write_chapter_node`)
   - 逐章生成文本（可迭代）
   - 每章参考相关的 Move 模式
   - 纳入前文上下文

4. **验证流畅性** (`verify_fluency_node`)
   - 检查句子通顺度
   - 评分 0-10
   - 如果不及格且迭代 < 2 次，重新生成

5. **决策循环**
   - 判断是否继续下一章
   - 或完成并进入最终化

6. **合并故事** (`finalize_node`)
   - 将所有章节合并为完整故事
   - 添加标题和概念说明

### 示例输出

```
# 关于失去和重新开始的故事

## 概念
关于失去和重新开始的故事

---

## 第1章 开篇

【开篇】

介绍主角和故事背景

[章节内容...]

## 第2章 相遇

【相遇】

出现一个改变故事的人物或事件

[章节内容...]

[... 更多章节 ...]
```

## 🔑 核心概念

### Move Codebook

从参考小说提取的叙述结构，包含 5 种基本模式：

| Move | 描述 | 情感 | 字数 |
|------|------|------|------|
| setup | 建立故事的世界和氛围 | calm, quiet | 300-500 |
| introduce_character | 引入重要人物 | intrigue, surprise | 400-600 |
| create_conflict | 制造冲突和张力 | tension, shock | 500-800 |
| escalate | 升级冲突 | urgency, determination | 400-600 |
| resolution | 解决和收尾 | relief, acceptance | 300-500 |

### 智能降级

系统设计有多层降级机制：

```python
# Level 1: 使用真实 LLM
move_codebook = await extract_moves_from_novel(novel_data)

# Level 2: LLM 失败 → 使用默认 Move Codebook
if not move_codebook:
    move_codebook = get_default_move_codebook()

# Level 3: 生成故事
story_ir = await call_llm_safe(prompt, parse_json=True)

# Level 4: LLM 失败 → 使用模板规划
if not story_ir:
    story_ir = generate_default_story_plan(...)
```

## 🚦 常见问题

### Q: 需要 API Key 吗？

**A**: 可选。有 DASHSCOPE_API_KEY 会使用真实 LLM，没有的话使用智能默认值，流程完全可运行。

### Q: 支持哪些参考小说？

**A**: 任何在 SQLite 数据库中的小说都可以。当前数据库包含"诡秘之主"及其他作品。

### Q: 生成速度如何？

**A**: 5 章故事约 8-10 分钟（包括 LLM API 调用延迟）。使用默认值时更快（2-3 分钟）。

### Q: 支持自定义 Move 吗？

**A**: 支持。可以修改 `nodes.py` 中的 `get_default_move_codebook()` 函数。

### Q: 可以并行生成多个故事吗？

**A**: 可以，使用不同的 `thread_id` 在同一服务器上并行执行。

## 📚 文件说明

### 核心文件

| 文件 | 说明 | 行数 |
|------|------|------|
| `backend/src/novel/state.py` | 状态定义 | 50 |
| `backend/src/novel/loader.py` | 数据加载 | 120 |
| `backend/src/novel/prompts.py` | Prompt 模板 | 200+ |
| `backend/src/novel/move_extractor.py` | Move 提取 | 190 |
| `backend/src/novel/nodes.py` | 工作流节点 | 480+ |
| `backend/src/novel/graph.py` | LangGraph 工作流 | 360 |
| `backend/src/api/routes.py` | API 路由 | 350+ |
| `backend/src/api/schemas.py` | 数据模型 | 200+ |

### 测试文件

| 文件 | 测试内容 | 耗时 |
|------|----------|------|
| `test_phase2.py` | 工作流+节点 | 7-8 分钟 |
| `test_phase3_api.py` | API 接口 | 8-10 分钟 |

## 🛠️ 开发指南

### 修改 Prompt

编辑 `backend/src/novel/prompts.py` 中的对应 Prompt 变量：

- `MOVE_EXTRACTION_PROMPT` - Move 提取
- `STORY_PLAN_PROMPT` - 故事规划
- `CHAPTER_WRITING_PROMPT` - 章节写作
- `FLUENCY_CHECK_PROMPT` - 流畅性检查

### 修改默认值

编辑 `backend/src/novel/nodes.py` 中的函数：

- `get_default_move_codebook()` - 修改默认 Move 结构
- `generate_default_story_plan()` - 修改默认故事规划
- `generate_default_chapter()` - 修改默认章节模板

### 添加新节点

在 `backend/src/novel/graph.py` 中：

1. 在 `nodes.py` 中定义新的 async 函数
2. 在 `create_novel_graph()` 中使用 `workflow.add_node()` 添加
3. 使用 `workflow.add_edge()` 或 `workflow.add_conditional_edges()` 连接

## 📖 相关资源

- **LangGraph 文档**: https://langchain-ai.github.io/langgraph/
- **FastAPI 文档**: https://fastapi.tiangolo.com/
- **Pydantic 文档**: https://docs.pydantic.dev/

## ✅ 检查清单

- [x] Phase 1: 数据层完成
- [x] Phase 2: 工作流完成
- [x] Phase 3: API 完成
- [x] 测试套件完成
- [x] 文档完成

## 📝 许可证

本项目是学习和研究项目。

## 🙏 致谢

- 基于 LangGraph 框架
- 使用阿里云通义千问 LLM
- 数据来自起点中文网爬虫项目

---

**最后更新**: 2026-02-21

**项目状态**: ✅ 完成（Phase 1-3）

如有问题，请查看测试文件或日志输出。
