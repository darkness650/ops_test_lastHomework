# 微服务运维智能体 (Microservice Ops Agent)

## 项目简介

微服务运维智能体是一个基于大语言模型 (LLM) 的智能运维平台，旨在帮助运维人员更高效地管理 Kubernetes 集群。该系统能够自动监控集群状态、检测异常、分析根因，并提供智能的故障恢复建议。

### 主要特性

- **智能对话交互**：通过自然语言与运维Agent进行对话，查询集群状态
- **Kubernetes 集成**：自动发现集群资源（Pod、Deployment、Service、Node等）
- **Prometheus 监控**：实时获取集群指标数据
- **异常检测**：自动检测 Pod 崩溃、资源不足、健康检查失败等异常
- **AI 根因分析**：利用大语言模型进行智能故障根因分析
- **故障恢复建议**：提供可执行的故障恢复步骤和操作指导
- **定时轮询**：定期自动检查集群健康状态
- **可视化仪表盘**：直观展示集群状态和异常告警

## 项目结构

```
agent/
├── backend/                    # 后端服务
│   ├── agents/                # 智能体核心模块
│   │   ├── agent.py           # Agent 核心逻辑
│   │   ├── llm_client.py      # LLM 客户端
│   │   ├── anomaly_analyzer.py # 异常分析器
│   │   ├── scheduler.py       # 任务调度器
│   │   └── ...
│   ├── api/                   # API 接口层
│   │   ├── routes/            # 路由模块
│   │   │   ├── chat.py        # 聊天对话接口
│   │   │   ├── monitor.py     # 监控接口
│   │   │   ├── anomaly.py     # 异常管理接口
│   │   │   ├── polling.py     # 轮询调度接口
│   │   │   └── config.py      # 配置接口
│   │   └── app.py             # FastAPI 应用入口
│   ├── tools/                 # 工具模块
│   │   ├── k8s_tools.py       # Kubernetes 操作工具
│   │   ├── prometheus.py      # Prometheus 查询工具
│   │   └── logs.py            # 日志查询工具
│   ├── config/                # 配置模块
│   │   ├── settings.py        # 应用配置
│   │   └── logging_config.py  # 日志配置
│   ├── cli/                   # 命令行工具
│   ├── tests/                 # 测试用例
│   ├── main.py                # 后端启动入口
│   ├── pyproject.toml         # 项目依赖配置
│   └── .env                   # 环境变量文件
├── frontend/                  # 前端应用
│   ├── src/
│   │   ├── pages/             # 页面组件
│   │   │   ├── Dashboard.vue  # 仪表盘首页
│   │   │   ├── Chat.vue       # 对话页面
│   │   │   ├── History.vue    # 历史记录页面
│   │   │   └── Settings.vue   # 设置页面
│   │   ├── stores/            # Pinia 状态管理
│   │   ├── api/               # API 调用层
│   │   └── App.vue            # 应用根组件
│   ├── package.json           # 前端依赖配置
│   └── vite.config.ts         # Vite 配置
└── README.md                  # 项目说明文档
```

## 技术栈

### 后端

- **Python**: >= 3.10
- **FastAPI**: Web 框架
- **Uvicorn**: ASGI 服务器
- **Pydantic**: 数据验证
- **UV**: Python 包管理器
- **Kubernetes Python Client**: Kubernetes API 客户端
- **APScheduler**: 任务调度器
- **Typer**: 命令行工具

### 前端

- **Vue 3**: 前端框架
- **TypeScript**: 类型安全
- **Vite**: 构建工具
- **Element Plus**: UI 组件库
- **Pinia**: 状态管理
- **Vue Router**: 路由管理
- **Tailwind CSS**: 原子化 CSS
- **ECharts**: 数据可视化
- **Axios**: HTTP 客户端

## 快速开始

### 环境要求

- Python >= 3.10
- Node.js >= 18
- UV (Python 包管理器)
- Kubernetes 集群 (可选，用于完整功能测试)
- Prometheus (可选，用于监控指标)

### 后端部署

1. **进入后端目录**

```bash
cd backend
```

2. **安装依赖**

```bash
# 使用 UV 安装依赖
uv sync
```

3. **配置环境变量**

复制并编辑 `.env` 文件：

```bash
# LLM 配置（必需）
BASE_URL=https://api.openai.com/v1
API_KEY=your-api-key
MODEL=gpt-4

# Kubernetes 配置（可选）
KUBECONFIG_PATH=/path/to/kubeconfig

# Prometheus 配置（可选）
PROMETHEUS_URL=http://localhost:9090

# ElasticSearch 配置（可选）
ES_URL=http://localhost:9200
ES_INDEX=logs

# 轮询配置
POLLING_INTERVAL_MINUTES=5

# 日志级别
LOG_LEVEL=INFO
```

4. **启动后端服务**

```bash
# 开发模式
uv run python main.py

# 或使用 uvicorn 直接启动
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

后端服务启动后，访问以下地址：
- API 文档: http://localhost:8000/docs
- ReDoc 文档: http://localhost:8000/redoc

### 前端部署

1. **进入前端目录**

```bash
cd frontend
```

2. **安装依赖**

```bash
npm install
```

3. **启动开发服务器**

```bash
npm run dev
```

前端默认运行在 http://localhost:5173

4. **构建生产版本**

```bash
npm run build
```

## 功能说明

### 1. 仪表盘 (Dashboard)

仪表盘提供集群状态的概览：

- **集群状态**：显示当前集群的健康状态（正常/警告/严重/异常）
- **异常数量**：统计当前检测到的异常总数
- **轮询状态**：显示自动轮询是否运行中
- **轮询间隔**：显示定时检查的时间间隔
- **异常列表**：展示所有检测到的异常，点击可查看 AI 分析及修复建议

### 2. 智能对话 (Chat)

通过自然语言与运维 Agent 进行交互：

- 查询 Pod 状态：`查看 default 命名空间下的所有 Pod`
- 检查服务健康：`检查 my-service 服务是否正常`
- 获取日志：`查看 my-pod 的最近 100 条日志`
- 查询监控指标：`获取最近 5 分钟的 CPU 使用率`

### 3. 异常检测与分析

系统会自动检测以下异常类型：

- **Pod CrashLoopBackOff**：Pod 反复崩溃重启
- **Pending Pods**：Pod 无法调度
- **Failed Pods**：Pod 运行失败
- **ImagePullBackOff**：镜像拉取失败
- **Failed Scheduling**：调度失败
- **Resources Exhausted**：资源不足
- **Container Not Ready**：容器未就绪
- **Probe Failures**：探针检查失败
- **ReplicaSet Mismatch**：副本集不匹配

检测到异常后，可以触发 AI 根因分析，系统会：
1. 收集相关证据（Pod 状态、事件、日志等）
2. 使用 LLM 进行智能分析
3. 提供根因分析和置信度
4. 给出可执行的恢复步骤和风险评估

### 4. 定时轮询

系统支持定期自动检查集群状态：

- 可配置轮询间隔（默认 5 分钟）
- 自动记录历史检查结果
- 发现异常自动记录和告警

## API 接口

### 主要接口

| 接口路径 | 方法 | 描述 |
|---------|------|------|
| `/api/v1/chat` | POST | 与 Agent 对话 |
| `/api/v1/monitor/health` | GET | 健康检查 |
| `/api/v1/monitor/check` | POST | 执行健康检查 |
| `/api/v1/monitor/anomalies` | GET | 获取异常列表 |
| `/api/v1/anomaly/{id}` | GET | 获取异常详情 |
| `/api/v1/anomaly/{id}/analyze` | POST | 触发异常分析 |
| `/api/v1/polling/status` | GET | 获取轮询状态 |
| `/api/v1/polling/start` | POST | 启动轮询 |
| `/api/v1/polling/stop` | POST | 停止轮询 |
| `/api/v1/config` | GET | 获取当前配置 |

### API 示例

#### 与 Agent 对话

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "查看所有 Pod 状态",
    "context_id": "optional-session-id"
  }'
```

#### 执行健康检查

```bash
curl -X POST http://localhost:8000/api/v1/monitor/check
```

## 配置说明

### LLM 配置

项目支持兼容 OpenAI API 格式的大语言模型服务：

```env
BASE_URL=https://api.openai.com/v1
API_KEY=sk-xxxxxxxxxxxxxxxxxxxx
MODEL=gpt-4
```

### Kubernetes 配置

如果需要连接远程 Kubernetes 集群：

```env
KUBECONFIG_PATH=/path/to/your/kubeconfig
```

如果不配置，将使用默认的 Kubernetes 配置路径（如 `~/.kube/config`）或集群内配置。

### Prometheus 配置

```env
PROMETHEUS_URL=http://localhost:9090
```

### ElasticSearch 配置（用于日志查询）

```env
ES_URL=http://localhost:9200
ES_INDEX=application-logs
```

## 命令行工具 (CLI)

项目提供了功能丰富的命令行工具，支持与 GUI 完全同步的运维操作。

### 运行方式

在 `backend` 目录下执行以下命令：

```bash
cd backend

# 查看帮助
uv run python -m cli.main --help
```

### 可用命令概览

| 命令 | 描述 |
|------|------|
| `python -m cli.main chat` | 与运维智能体进行交互式对话 |
| `python -m cli.main monitor` | 立即执行一次健康监测 |
| `python -m cli.main status` | 查看轮询调度器状态 |
| `python -m cli.main polling-start` | 启动定时轮询 |
| `python -m cli.main polling-stop` | 停止定时轮询 |
| `python -m cli.main polling-run-once` | 立即执行一次轮询 |
| `python -m cli.main history` | 查看轮询历史记录 |
| `python -m cli.main version` | 显示版本信息 |
| `python -m cli.main anomaly list` | 查看当前异常列表 |
| `python -m cli.main anomaly analyze` | 查看异常分析详情 |
| `python -m cli.main anomaly trigger` | 手动触发异常分析 |
| `python -m cli.main anomaly status` | 查看异常分析状态 |
| `python -m cli.main health status` | 查看健康分析器状态 |
| `python -m cli.main health list` | 查看异常分析记录列表 |

### 详细使用说明

#### 1. 对话命令 (chat)

与运维智能体进行对话，支持单次消息和交互式两种模式。

```bash
cd backend

# 启动交互式对话
uv run python -m cli.main chat

# 发送单次消息后退出
uv run python -m cli.main chat -m "查看集群状态"

# 指定命名空间
uv run python -m cli.main chat -n default
```

**交互式模式可用命令：**
- `help` - 显示帮助信息
- `quit` / `exit` / `q` - 退出对话

**示例问题：**
- "集群状态如何？"
- "查看 default 命名空间的 Pod"
- "获取 nginx Pod 的最近日志"
- "检查服务的 CPU 使用率"

#### 2. 健康监测命令 (monitor)

立即执行一次集群健康检查。

```bash
cd backend

# 检查所有命名空间
uv run python -m cli.main monitor

# 检查指定命名空间
uv run python -m cli.main monitor -n default

# 执行深度分析
uv run python -m cli.main monitor -n default -d
```

#### 3. 轮询调度命令

**查看轮询状态：**
```bash
cd backend
uv run python -m cli.main status
```

**启动定时轮询：**
```bash
cd backend

# 每 5 分钟轮询一次（默认）
uv run python -m cli.main polling-start

# 每 10 分钟轮询一次
uv run python -m cli.main polling-start -i 10

# 只检查指定命名空间
uv run python -m cli.main polling-start -n default

# 启用深度分析
uv run python -m cli.main polling-start -d
```

**停止轮询：**
```bash
cd backend
uv run python -m cli.main polling-stop
```

**立即执行一次轮询：**
```bash
cd backend

uv run python -m cli.main polling-run-once

# 指定命名空间和深度分析
uv run python -m cli.main polling-run-once -n default -d
```

#### 4. 历史记录命令 (history)

查看轮询历史记录。

```bash
cd backend

# 显示最近 10 条记录
uv run python -m cli.main history

# 显示最近 20 条记录
uv run python -m cli.main history -l 20

# 清空历史记录
uv run python -m cli.main history --clear
```

#### 5. 异常分析命令 (anomaly)

**查看异常列表：**
```bash
cd backend

# 查看所有命名空间的异常
uv run python -m cli.main anomaly list

# 查看指定命名空间的异常
uv run python -m cli.main anomaly list -n default
```

**查看异常分析详情：**
```bash
cd backend

# 通过异常 ID 查看
uv run python -m cli.main anomaly analyze -i <异常ID>

# 通过索引查看（第 1 个异常）
uv run python -m cli.main anomaly analyze -n 1 -ns default

# 等待分析完成后显示结果
uv run python -m cli.main anomaly analyze -i <异常ID> -w

# 设置等待超时（秒）
uv run python -m cli.main anomaly analyze -i <异常ID> -w -t 300
```

**触发异常分析：**
```bash
cd backend

# 通过异常 ID 触发
uv run python -m cli.main anomaly trigger -i <异常ID>

# 通过索引触发
uv run python -m cli.main anomaly trigger -n 1 -ns default

# 触发并等待完成
uv run python -m cli.main anomaly trigger -i <异常ID> -w
```

**查看分析状态：**
```bash
cd backend

# 查看指定异常的分析状态
uv run python -m cli.main anomaly status -i <异常ID>

# 持续监视状态变化
uv run python -m cli.main anomaly status -i <异常ID> -w
```

#### 6. 健康分析器命令 (health)

**查看健康分析器状态：**
```bash
cd backend
uv run python -m cli.main health status
```

**查看分析记录列表：**
```bash
cd backend

# 查看最近 20 条记录
uv run python -m cli.main health list

# 查看最近 50 条记录
uv run python -m cli.main health list -l 50

# 只查看已完成的分析
uv run python -m cli.main health list -s completed

# 只查看失败的分析
uv run python -m cli.main health list -s failed
```

### CLI 与 GUI 功能对应关系

| CLI 命令 | GUI 功能位置 |
|---------|-------------|
| `python -m cli.main chat` | Chat 页面 |
| `python -m cli.main monitor` | Dashboard "深度检查"按钮 |
| `python -m cli.main anomaly list` | Dashboard 异常列表 |
| `python -m cli.main anomaly analyze` | Dashboard 异常详情弹窗 |
| `python -m cli.main anomaly trigger` | Dashboard "触发分析"按钮 |
| `python -m cli.main polling-start` | Settings 页面启动轮询 |
| `python -m cli.main history` | History 页面 |
| `python -m cli.main health list` | History 页面分析记录 |

## 开发指南

### 后端开发

```bash
cd backend

# 安装依赖
uv sync

# 运行测试
uv run pytest

# 启动开发服务器（热重载）
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 前端开发

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 类型检查
npm run check

# 构建生产版本
npm run build
```

## 测试

项目包含验证测试用例，位于 `backend/tests/` 目录：

```bash
cd backend

# 运行所有测试
uv run pytest
```

## 常见问题

### 1. 无法连接到 Kubernetes

**问题**：后端启动时提示无法连接 Kubernetes

**解决**：
- 确保 `kubectl` 可以正常访问集群
- 检查 `KUBECONFIG_PATH` 配置是否正确
- 如果在集群内部署，确保 ServiceAccount 有足够权限

### 2. LLM 调用失败

**问题**：对话功能返回 AI 服务不可用

**解决**：
- 检查 `.env` 中的 `BASE_URL` 和 `API_KEY` 是否正确
- 确保网络可以访问 LLM 服务
- 验证模型名称是否正确

### 3. 前端无法连接后端

**问题**：前端页面显示连接错误

**解决**：
- 确保后端服务正在运行（默认端口 8000）
- 检查前端 `src/api/request.ts` 中的 API 基础地址配置
- 检查 CORS 配置（后端默认允许所有来源）

## License

本项目仅供学习和内部使用。

---

## 贡献

欢迎提交 Issue 和 Pull Request 来改进这个项目！
