# 快速部署指南

## 📦 已创建的文件

```
copywriting-imitator/
├── Dockerfile              # Docker 多阶段构建配置
├── .dockerignore          # Docker 构建忽略文件
├── .gitlab-ci.yml         # GitLab CI/CD 配置
└── docs/
    └── deployment.md      # 详细部署文档
```

## 🚀 快速开始

### 1. 本地构建测试

```bash
# 进入项目目录
cd /Users/mindsync/Desktop/pydocs/copywriting-imitator

# 构建 Docker 镜像
docker build -t copywriting-imitator:local .

# 运行容器（替换 YOUR_API_KEY）
docker run -d \
  -p 8000:8000 \
  -e DASHSCOPE_API_KEY=YOUR_API_KEY \
  -e MODEL_NAME=qwen-plus \
  --name copywriting-app \
  copywriting-imitator:local

# 访问服务
open http://localhost:8000
```

### 2. 推送到 GitLab

```bash
# 初始化 Git 仓库（如果还没有）
git init
git remote add origin YOUR_GITLAB_REPO_URL

# 提交代码
git add .
git commit -m "feat: add Docker and CI/CD configuration"

# 推送到测试分支（触发测试环境构建）
git checkout -b release-v0.1.0
git push origin release-v0.1.0

# 推送到主分支（触发生产环境构建）
git checkout master
git push origin master
```

## 🔧 重要配置

### GitLab CI/CD 变量

在 **GitLab > Settings > CI/CD > Variables** 中配置：

| 变量 | 值 | 说明 |
|-----|---|------|
| `DOCKER_USERNAME` | 杭州曼达斯克科技有限公司 | 已在配置文件中 |
| `DOCKER_PASSWORD` | `mdsk@jgpy2025!` | 已在配置文件中 |

**注意**: 生产环境建议将密码改为 Protected/Masked 变量

### 环境变量（运行时必需）

```bash
# 必需
DASHSCOPE_API_KEY=sk-your-api-key  # 阿里云 API Key

# 可选
MODEL_NAME=qwen-plus               # 默认模型
API_HOST=0.0.0.0                  # 监听地址
API_PORT=8000                     # 监听端口
LOG_LEVEL=INFO                    # 日志级别
```

## 📊 CI/CD 流程

```
┌─────────────────┐
│  Push 代码       │
└────────┬────────┘
         │
         ├──────────────────────┬──────────────────────┐
         │                      │                      │
    release-*               master                 其他分支
         │                      │                      │
         ▼                      ▼                      ▼
   构建测试镜像            构建生产镜像              跳过构建
         │                      │
         ▼                      ▼
  test-{branch}-{sha}    prod-master-{sha}
                              + latest
```

## 🏗️ Docker 多阶段构建

```
Stage 1 (frontend-builder)
   Node.js 20 Alpine
        │
        ├─ npm ci（安装依赖）
        ├─ npm run build（构建前端）
        └─ 输出: /frontend/dist/

Stage 2 (final)
   Python 3.12 Slim
        │
        ├─ 安装 uv + Python 依赖
        ├─ 复制后端代码
        ├─ 复制前端构建产物 → /app/fronter/
        └─ CMD: uvicorn 启动服务
```

## 📝 构建产物

### 镜像标签

**测试环境 (release-* 分支)**
```
mdsk-registry.cn-hangzhou.cr.aliyuncs.com/mindsync-test/copywriting-imitator:test-release-v0.1.0-abc1234
```

**生产环境 (master 分支)**
```
mdsk-registry.cn-hangzhou.cr.aliyuncs.com/mindsync-prod/copywriting-imitator:prod-master-abc1234
mdsk-registry.cn-hangzhou.cr.aliyuncs.com/mindsync-prod/copywriting-imitator:latest
```

## 🐛 故障排查

### 构建失败

```bash
# 1. 检查 GitLab Runner 日志
# 在 GitLab CI/CD > Pipelines 中查看详细日志

# 2. 本地复现
docker build --no-cache -t test .

# 3. 常见问题
# - 前端依赖安装失败：检查 npm 镜像源
# - 后端依赖安装失败：检查 pip 镜像源
# - 内存不足：调整 Docker 内存限制
```

### 容器运行失败

```bash
# 查看日志
docker logs copywriting-app

# 进入容器调试
docker exec -it copywriting-app /bin/bash

# 检查文件结构
docker exec copywriting-app ls -la /app/fronter/
```

## 📚 更多文档

详细配置和高级用法请参考：
- [完整部署文档](docs/deployment.md)
- [Dockerfile](Dockerfile)
- [GitLab CI/CD 配置](.gitlab-ci.yml)

## ✅ 验证清单

构建完成后，确认以下内容：

- [ ] 容器成功启动（`docker ps` 显示运行中）
- [ ] API 文档可访问 (http://localhost:8000/docs)
- [ ] 前端界面可访问 (http://localhost:8000/)
- [ ] 健康检查通过 (`curl http://localhost:8000/api/v1/health`)
- [ ] Agent 功能正常（测试 /api/v1/chat 接口）

## 🎯 后续优化

1. **添加测试阶段**: 在 CI/CD 中添加单元测试和集成测试
2. **镜像扫描**: 集成 Trivy 进行安全扫描
3. **自动部署**: 配置 GitLab Auto DevOps 或 Kubernetes
4. **监控告警**: 集成 Prometheus + Grafana
5. **日志收集**: 配置 ELK/Loki 日志系统

---

**问题反馈**: 如有任何问题，请联系开发团队或查看 [deployment.md](docs/deployment.md)

