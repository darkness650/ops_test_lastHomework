# ops_test_lastHomework

本项目包含运维与测试任务、JMeter 性能测试、智能体开发以及异常检测等相关内容。

## 目录结构

### `ops/` — 运维部署

运维与测试任务的核心文件，包括 Kubernetes 部署配置、混沌工程实验和监控指标收集等。

**部署说明**：详见 [ops/README.md](ops/README.md)

```
ops/
├── kubernetes-manifests.yaml   # Kubernetes 资源清单（RBAC 等）
├── rbac.yaml                   # RBAC 权限配置
├── README.md                   # 部署文档（minikube 安装、Helm 安装 Prometheus）
├── chaos/                      # 混沌工程实验配置
│   ├── network-loss.yaml       # 网络丢包实验
│   └── stress-test.yaml        # 压力测试实验
├── manifests-logging/          # 日志采集与可视化（Fluentd + Kibana）
│   ├── fluentd-*.yaml          # Fluentd DaemonSet / CR / RBAC / SA
│   └── kibana.yml              # Kibana 配置
└── metrics/                    # Prometheus 指标收集数据
    ├── CPU Memory Net Disk/
    ├── Memory Meminfo/
    ├── Memory Vmstat/
    ├── Network Netstat/
    ├── Network Sockstat/
    ├── Network Traffic/
    ├── Node Exporter/
    ├── Storage Disk/
    ├── System Misc/
    └── System Processes/
```

### `test/` — JMeter 性能测试

使用 JMeter 进行的各类性能测试场景，涵盖 HTTP 接口、gRPC 服务及在线精品店（Online Boutique）等。

```
test/
├── jmeter-all-apis/            # 全量 API 测试
├── jmeter-grpc-backend/        # gRPC 后端测试
├── jmeter-grpc-extreme/        # gRPC 极限压测
├── jmeter-online-boutique/     # Online Boutique 微服务测试
├── jmeter-product-stress/      # 商品服务压力测试
├── jmeter-rec-email/           # 推荐服务 & 邮件服务测试
├── test-cart-check/            # 购物车接口测试
├── test-http-all-easyerror/    # HTTP 全量易错接口测试
├── test-http-infinity/         # HTTP 无限循环测试
└── test5/                      # 其他测试用例
```

### `agent/` — 微服务运维智能体

基于 LLM 的微服务运维智能体平台，帮助运维人员高效管理 Kubernetes 集群。

**详细介绍**：详见 [agent/README.md](agent/README.md)

```
agent/
├── backend/                    # Python 后端（FastAPI + uv）
│   ├── agents/                 # Agent 核心模块
│   ├── api/                    # API 层
│   ├── cli/                    # 命令行工具
│   ├── config/                 # 配置管理
│   ├── memory/                 # 记忆模块
│   ├── models/                 # 数据模型
│   ├── tests/                  # 单元测试
│   └── tools/                  # 工具集
└── frontend/                   # Vue 3 + TypeScript + Vite + Tailwind CSS 前端
    ├── src/
    ├── public/
    └── package.json
```

### `FluxEV/` — 时间序列异常检测

论文 ["FluxEV: A Fast and Effective Unsupervised Framework for Time-Series Anomaly Detection"](https://dl.acm.org/doi/10.1145/3437963.3441823)（WSDM 2021）的重构版实现。Flux 表示波动，EV 表示极值。

**详细介绍**：详见 [FluxEV/README.md](FluxEV/README.md)

```
FluxEV/
├── main.py                     # 本地启动脚本
├── pyproject.toml              # 依赖管理（uv）
├── data/                       # 数据集目录（AIOps、OPS、Yahoo）
└── fluxev/                     # 核心包
    ├── cli.py                  # 命令行入口
    ├── detector.py             # 特征提取与流式检测
    ├── spot.py                 # SPOT 检测器与 GPD 参数估计
    ├── datasets.py             # 数据集运行流程
    ├── preprocessing.py        # KPI 预处理
    ├── ops_preprocessing.py    # OPS 预处理
    ├── evaluation.py           # 评估策略
    └── plotting.py             # 绘图函数
```

### `lightlog/` — 日志分析

包含 LightLog 日志分析框架及 LogRobust 训练与检查脚本。

```
lightlog/
└── LogRobust/
    ├── check_checkpoint.py     # 检查点验证
    ├── check_data.py           # 数据检查
    ├── dataset.py              # 数据集处理
    ├── model.py                # 模型定义
    └── train.py                # 训练脚本
```

### `Online Boutique/` — 在线精品店微服务示例

Google Cloud 的 [Online Boutique](https://github.com/JoinFyc/Online-Boutique) 示例项目扩展，新增库存管理（`inventoryservice`）和管理员进货（`restockservice`）功能。

**详细介绍**：详见 [Online Boutique/README.md](Online%20Boutique/README.md)

```
Online Boutique/
├── skaffold.yaml               # Skaffold 构建配置
├── docs/                       # 文档（开发指南、部署教程等）
├── helm-chart/                 # Helm Chart 配置
├── istio-manifests/            # Istio 流量管理配置
├── kubernetes-manifests/       # Kubernetes 资源清单
├── kustomize/                  # Kustomize 配置
├── protos/                     # gRPC 协议定义
└── src/                        # 微服务源码
    ├── frontend/               # 前端（含库存显示与进货页面）
    ├── inventoryservice/       # 新增：库存查询与管理
    └── restockservice/         # 新增：管理员进货服务
```
