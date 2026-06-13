# 微服务运维智能体 (Microservice Ops Agent)

## 项目简介

微服务运维智能体是一个基于大语言模型 (LLM) 的智能运维平台，旨在帮助运维人员更高效地管理 Kubernetes 集群。该系统能够自动监测集群健康状态、检测异常、进行 AI 根因分析，并生成故障恢复建议。

### 主要功能

| 功能模块 | 描述 |
|---------|------|
| **集群健康监测** | 自动检测 Pod、Deployment、Node 等资源的异常状态，基于规则引擎快速识别问题 |
| **AI 根因分析** | 当检测到异常时，自动触发 LLM 进行深度分析，识别问题根因 |
| **故障恢复建议** | 基于根因分析生成具体、可操作的恢复步骤，包含风险评估 |
| **定时轮询调度** | 支持定时轮询监测集群状态，自动触发异常分析 |
| **智能对话** | 通过自然语言与运维智能体对话，查询集群状态、获取运维建议 |
| **业务性能分析** | 分析集群性能指标，识别性能瓶颈、趋势分析，提供优化建议 |
| **历史记录** | 保存所有监测和分析记录，支持历史追溯和趋势分析 |
| **命令行工具** | 提供完整的 CLI 工具，支持与 GUI 完全同步的运维操作 |

## 项目结构

```
agent/
├── backend/                          # 后端服务
│   ├── agents/                       # 智能体核心模块
│   │   ├── agent.py                  # Agent 核心类，实现 Tool Calling 循环
│   │   ├── engine.py                 # 分析引擎，包含健康监测、异常检测、根因分析
│   │   ├── scheduler.py              # 定时轮询调度器
│   │   ├── anomaly_analyzer.py       # 异常分析器，后台自动执行 AI 分析
│   │   ├── business_analyzer.py      # 业务性能分析引擎
│   │   ├── llm_client.py             # LLM 客户端封装
│   │   ├── history.py                # 轮询历史记录存储
│   │   ├── analysis_store.py         # 分析结果存储
│   │   ├── report_store.py           # 性能报告存储
│   │   ├── schedule_analyzer.py      # 调度分析器
│   │   └── analysis_task_manager.py  # 分析任务管理器
│   ├── api/                          # FastAPI 应用
│   │   ├── app.py                    # FastAPI 应用创建
│   │   ├── exceptions.py             # 异常处理
│   │   ├── schemas.py                # API 数据模型
│   │   └── routes/                   # API 路由
│   │       ├── chat.py               # 对话接口
│   │       ├── monitor.py            # 监测接口
│   │       ├── polling.py            # 轮询调度接口
│   │       ├── anomaly.py            # 异常分析接口
│   │       ├── analysis.py           # 性能分析接口
│   │       └── config.py             # 配置接口
│   ├── cli/                          # 命令行工具
│   │   └── main.py                   # CLI 入口
│   ├── config/                       # 配置管理
│   │   ├── settings.py               # 应用配置（Pydantic Settings）
│   │   └── logging_config.py         # 日志配置
│   ├── tools/                        # 工具模块
│   │   ├── base.py                   # 工具基类和注册表
│   │   ├── k8s_client.py             # Kubernetes 客户端封装
│   │   ├── k8s_tools.py              # K8s 相关工具函数
│   │   ├── prometheus.py             # Prometheus 工具
│   │   ├── logs.py                   # 日志工具
│   │   ├── metrics_collector.py      # 指标采集器
│   │   └── examples.py               # 示例工具
│   ├── memory/                       # 内存存储
│   ├── models/                       # 数据模型
│   ├── tests/                        # 测试代码
│   ├── .env.example                  # 环境变量示例
│   ├── pyproject.toml                # Python 项目配置
│   └── main.py                       # 应用入口
│
├── frontend/                         # 前端应用
│   ├── src/
│   │   ├── api/                      # API 封装
│   │   ├── pages/                    # 页面组件
│   │   │   ├── Dashboard.vue         # 集群概览页面
│   │   │   ├── Chat.vue              # 智能对话页面
│   │   │   ├── History.vue           # 历史记录页面
│   │   │   ├── Settings.vue          # 系统配置页面
│   │   │   ├── PerformanceAnalysis.vue      # 业务性能分析页面
│   │   │   └── PerformanceReportDetail.vue  # 性能报告详情页面
│   │   ├── stores/                   # Pinia 状态管理
│   │   ├── router/                   # 路由配置
│   │   ├── components/               # 通用组件
│   │   ├── composables/              # 组合式函数
│   │   └── types/                    # TypeScript 类型定义
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   └── tailwind.config.js
│
├── .gitignore
└── README.md
```

## 技术栈

### 后端

| 技术 | 版本 | 用途 |
|------|------|------|
| Python | >= 3.10 | 编程语言 |
| FastAPI | >= 0.110.0 | Web 框架 |
| Uvicorn | >= 0.27.0 | ASGI 服务器 |
| Pydantic | >= 2.6.0 | 数据验证和设置管理 |
| Python-dotenv | >= 1.0.0 | 环境变量加载 |
| HTTPX | >= 0.27.0 | HTTP 客户端（调用 LLM API） |
| Kubernetes Python Client | >= 29.0.0 | Kubernetes 集群交互 |
| Elasticsearch Python Client | >= 8.0.0 | 日志存储和查询 |
| APScheduler | >= 3.10.0 | 定时任务调度 |
| Typer | >= 0.12.0 | 命令行界面构建 |
| Rich | >= 13.7.0 | 终端输出美化 |
| Pytest | >= 8.0.0 | 测试框架（开发依赖） |

### 前端

| 技术 | 版本 | 用途 |
|------|------|------|
| Vue | >= 3.4.15 | 前端框架 |
| TypeScript | ~5.3.3 | 类型系统 |
| Vite | >= 5.0.12 | 构建工具 |
| Vue Router | >= 4.2.5 | 路由管理 |
| Pinia | >= 2.1.7 | 状态管理 |
| Element Plus | >= 2.7.0 | UI 组件库 |
| ECharts | >= 5.5.0 | 图表可视化 |
| Axios | >= 1.7.0 | HTTP 客户端 |
| Tailwind CSS | >= 3.4.1 | 样式框架 |
| Marked | >= 18.0.5 | Markdown 解析 |
| DOMPurify | >= 3.4.8 | XSS 防护 |
| Highlight.js | >= 11.11.1 | 代码高亮 |
| Lucide Vue Next | >= 0.511.0 | 图标库 |
| clsx + tailwind-merge | - | CSS 类名工具 |

## 快速开始

### 环境要求

- Python >= 3.10
- Node.js >= 18
- UV (Python 包管理器)
- Kubernetes 集群
- Prometheus (可选，用于监控指标)
- ElasticSearch (可选，用于日志存储)

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

# Agent 最大工具调用次数，默认 10 次
# MAX_TOOL_CALLS=10
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