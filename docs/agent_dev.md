# 文案写作助手 Agent MVP 开发文档

## 项目概述
创建一个文案写作助手的 Agent MVP 版本，提供口播文案的解析、仿写和质量评测功能。

## 技术栈
- **开发语言**: Python 3.12
- **Agent 框架**: LangGraph
- **API 框架**: FastAPI
- **LLM**: 通义千问 (qwen-plus)，通过 DashScope SDK 调用
- **Memory**: LangGraph 内置 MemorySaver

---

## 工作流设计

```
用户输入 → [解析节点] → [写作节点] → [评测节点] → 输出
              │               ↑              │
              │               │   反馈循环    │
              │               └──────────────┘
              │                    (≤3次)
              v
         结构化分析
```

### 节点说明

| 节点 | Prompt | 功能 |
|------|--------|------|
| 解析节点 (breakdown) | `COPYWRITING_BREAKDOWN_PROMPT` | 检测并拆解用户输入的文案结构 |
| 写作节点 (writing) | `COPYWRITING_PROMPT` | 基于解析结果仿写口播文案 |
| 评测节点 (proofread) | `COPYWRITING_PROOFREADER_PROMPT` | 评测文案质量，给出反馈建议 |

### 迭代逻辑
- 评测节点评分 ≥ 7 分视为通过
- 未通过则携带反馈回到写作节点重新生成
- 最大迭代次数: 3 次
- 达到最大次数后强制输出当前版本

---

## 项目目录结构

```
copywriting-assistant/
├── .venv/                   # uv 创建的虚拟环境 (不提交到 git)
├── logs/                    # 日志文件目录 (由 logger 自动维护)
│   └── app.log
├── src/                     # 源代码根目录
│   ├── __init__.py
│   ├── agent/               # [核心] Agent 业务逻辑
│   │   ├── __init__.py
│   │   ├── graph.py         # 定义 Graph 工作流 (StateGraph)
│   │   ├── nodes.py         # 定义节点执行逻辑
│   │   ├── state.py         # 定义 State 数据结构 (Pydantic V2)
│   │   └── prompts.py       # 管理 Prompt 模版
│   ├── api/                 # [接口] FastAPI 封装层
│   │   ├── __init__.py
│   │   ├── server.py        # FastAPI App 实例与启动配置
│   │   ├── routes.py        # 定义 API 路由 endpoint
│   │   └── schemas.py       # API 请求/响应的 Pydantic 模型 (DTO)
│   └── core/                # [基础] 配置与工具
│       ├── __init__.py
│       ├── config.py        # 环境变量与配置 (Pydantic Settings)
│       └── logger.py        # 日志配置模块
├── tests/                   # 测试用例
│   ├── __init__.py
│   └── test_agent.py
├── .env.example             # 环境变量示例
├── .gitignore
├── pyproject.toml           # 项目配置与依赖管理 (uv)
└── main.py                  # 项目入口文件
```

---

## 环境配置

```bash
# 1. 复制环境变量文件
cp .env.example .env

# 2. 编辑 .env 填入 API Key
DASHSCOPE_API_KEY=your_key_here

# 3. 创建虚拟环境并安装依赖
uv venv
source .venv/bin/activate
uv pip install -e .

# 4. 运行测试
python main.py --test

# 5. 启动 API 服务
python main.py --serve
```

---

## API 接口

### 生成文案
```
POST /api/v1/generate
{
    "user_input": "参考文案或素材",
    "user_instructions": "写作指令（可选）",
    "thread_id": "会话ID（可选）"
}
```

### 分析文案
```
POST /api/v1/analyze
{
    "user_input": "待分析的文案"
}
```

### 健康检查
```
GET /api/v1/health
```

---

## 开发规范

参考项目 `.cursor/rule/` 目录下的规则文件：
- `dev_rules.mdc`: Python 开发标准
- `fast_api.mdc`: FastAPI 最佳实践
- `logg.mdc`: 日志配置规范
