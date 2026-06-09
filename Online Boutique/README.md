# Online Boutique 库存与进货微服务扩展

本项目基于 Google Cloud 的
[Online Boutique](https://github.com/GoogleCloudPlatform/microservices-demo)
微服务示例进行扩展，用于软件测试与维护课程大作业。

在原有电商系统基础上，项目新增了两个可以独立构建、部署和监控的
Python 微服务：

- `inventoryservice`：库存服务。
- `restockservice`：进货服务。

同时修改了 Go 前端，使商品购买、购物车和管理员进货操作能够与库存状态联动。

## 新增功能

### 库存服务

`inventoryservice` 负责统一维护商品库存，主要功能包括：

- 查询商品剩余库存和所属仓库。
- 加入购物车时预留库存。
- 清空购物车时释放已预留库存。
- 拒绝超过剩余库存的购买数量。
- 接收进货操作并增加库存。
- 提供 Kubernetes 健康检查接口。
- 提供 Prometheus 监控指标。

主要接口：

```text
GET  /inventory/{product_id}
POST /inventory/{product_id}/reserve
POST /inventory/{product_id}/release
POST /inventory/{product_id}/restock
GET  /_healthz
GET  /metrics
```

### 进货服务

`restockservice` 是独立于消费者购买流程的进货微服务，主要功能包括：

- 接收管理员提交的进货请求。
- 校验前端传入的内部 API Token。
- 调用 `inventoryservice` 增加对应商品库存。
- 提供 Kubernetes 健康检查接口。
- 提供 Prometheus 请求计数指标。

主要接口：

```text
POST /restock/{product_id}
GET  /_healthz
GET  /metrics
```

### 前端功能

Go 前端新增了以下功能：

- 商品详情页显示剩余库存和仓库位置。
- 商品数量选择上限不超过当前库存。
- 库存为零时禁止加入购物车。
- 加入购物车成功后扣减可用库存。
- 清空购物车后自动回滚库存。
- 独立的管理员进货页面：`/admin/restock`。
- 进货页面需要管理员账号和密码。
- 进货成功后显示提示弹窗，点击确认后刷新页面。

## 服务调用关系

```text
消费者
  |
  v
frontend ------> inventoryservice
  |               查询、预留和释放库存
  |
  +------> cartservice

管理员
  |
  v
frontend ------> restockservice ------> inventoryservice
管理员登录         API Token 校验          增加库存
```

## 主要目录

```text
src/inventoryservice/               库存微服务源码与测试
src/restockservice/                 进货微服务源码与测试
src/frontend/                       修改后的 Go 前端
kubernetes-manifests/               Kubernetes 部署清单
helm-chart/                         Helm 部署模板
docs/inventory-service-development.md
skaffold.yaml                       本地构建和部署配置
```

## 本地部署

以下步骤适用于 Windows PowerShell 和 Minikube。

### 环境要求

请提前安装：

- Git
- Docker Desktop
- Minikube
- `kubectl`
- Skaffold

启动 Minikube 前必须先启动 Docker Desktop。建议为 Docker 和 Minikube
预留至少 4 个 CPU 和 8 GB 内存。

### 1. 克隆项目

```powershell
git clone <你的GitHub仓库地址>
cd microservices-demo
```

### 2. 启动 Minikube

```powershell
minikube start --driver=docker --cpus=4 --memory=8192
kubectl config use-context minikube
```

如果电脑可用内存不足，可以将 `--memory` 调整为 `6144`。

检查 Minikube 状态：

```powershell
minikube status
kubectl get nodes
```

### 3. 配置 Minikube Docker 环境

让 Skaffold 构建的镜像可以直接被 Minikube 使用：

```powershell
& minikube -p minikube docker-env --shell powershell | Invoke-Expression
```

该命令只对当前 PowerShell 窗口有效。关闭窗口后重新部署时，需要再次执行。

### 4. 构建并部署

在项目根目录执行：

```powershell
skaffold run
```

第一次执行需要下载依赖并构建多个服务镜像，可能需要几分钟。

### 5. 检查 Pod

```powershell
kubectl get pods
kubectl get services
```

等待主要 Pod 进入 `Running` 状态，并且 `READY` 显示为 `1/1`。

重点确认以下三个服务正常运行：

```text
frontend
inventoryservice
restockservice
```

`loadgenerator` 仅用于自动产生访问流量，不影响手动测试商城功能。

### 6. 打开前端

```powershell
minikube service frontend-external
```

Minikube 会生成访问地址并尝试使用默认浏览器打开商城。执行该命令的
PowerShell 窗口需要保持运行。

进入任意商品详情页，即可查看库存数量和仓库信息。

### 7. 打开管理员进货页面

在商城地址后添加 `/admin/restock`：

```text
<商城访问地址>/admin/restock
```

例如：

```text
http://127.0.0.1:xxxxx/admin/restock
```

本地演示默认账号：

```text
用户名：admin
密码：admin123
```

登录后选择商品并填写进货数量。进货成功后，页面会显示成功提示弹窗；
点击确认后页面刷新，并显示更新后的库存。

## 修改代码后重新部署

一次性重新构建和部署：

```powershell
skaffold run
kubectl get pods
```

持续监听源码变化并自动重新部署：

```powershell
skaffold dev
```

按 `Ctrl+C` 停止 `skaffold dev`。

只修改配置时，也可以重启指定 Deployment：

```powershell
kubectl rollout restart deployment/frontend
kubectl rollout status deployment/frontend
```

## 本地运行微服务测试

### 库存服务测试

```powershell
cd src/inventoryservice
python -m unittest
```

### 进货服务测试

```powershell
cd src/restockservice
python -m unittest
```

返回项目根目录：

```powershell
cd ../..
```

## 监控接口

两个新增微服务都在 `8080` 容器端口提供 `/metrics` 接口，并在
Kubernetes 清单中配置了 Prometheus 抓取注解。

主要指标：

```text
inventory_requests_total
inventory_product_quantity
restock_requests_total
```

可以临时转发服务端口进行查看：

```powershell
kubectl port-forward service/inventoryservice 8081:80
```

然后访问：

```text
http://127.0.0.1:8081/metrics
```

查看进货服务指标：

```powershell
kubectl port-forward service/restockservice 8082:80
```

然后访问：

```text
http://127.0.0.1:8082/metrics
```

## 常用排错命令

查看 Pod 和事件：

```powershell
kubectl get pods
kubectl get events --sort-by=.metadata.creationTimestamp
```

查看新增服务日志：

```powershell
kubectl logs deployment/inventoryservice
kubectl logs deployment/restockservice
kubectl logs deployment/frontend
```

查看某个 Pod 的详细状态：

```powershell
kubectl describe pod <Pod名称>
```

删除本地集群：

```powershell
minikube delete
```

## 配置说明

管理员和进货服务使用以下环境变量：

| 环境变量 | 作用 |
| --- | --- |
| `ADMIN_USERNAME` | 管理员用户名 |
| `ADMIN_PASSWORD` | 管理员密码 |
| `ADMIN_SESSION_TOKEN` | 管理员登录会话标识 |
| `RESTOCK_API_TOKEN` | 前端调用进货服务时使用的内部令牌 |
| `INVENTORY_SERVICE_URL` | 库存服务地址 |
| `RESTOCK_SERVICE_URL` | 进货服务地址 |

仓库中的固定账号和令牌仅用于本地课程演示，不是生产环境凭据。

## 上传 GitHub 前的安全注意事项

不要上传以下内容：

- `.env` 文件。
- 真实账号、密码、Token 或 API Key。
- Kubernetes Secret 导出文件。
- 私有 Helm values 文件。
- `kubeconfig` 文件。
- 云平台服务账号 JSON 文件。
- Docker 镜像仓库登录凭据。
- `*.key`、`*.pem`、`*.pfx` 等私钥或证书。
- `outputs/`、日志、缓存和本地生成文件。
- PPT 制作过程中的临时文件。

项目的 `.gitignore` 已排除常见的本地文件，但提交前仍应检查：

```powershell
git status
git diff --cached
```

不要把清单中的演示密码替换为真实密码后提交。共享或公开部署时，应使用
Kubernetes Secret 或私有配置文件注入敏感信息。

## 上传 GitHub

```powershell
git add .
git status
git commit -m "添加库存与进货微服务"
git branch -M main
git remote add origin <你的GitHub仓库地址>
git push -u origin main
```

如果已经配置过 `origin`，无需再次执行 `git remote add origin`。可以使用：

```powershell
git remote -v
```

查看当前远程仓库。

## 项目来源与许可证

本项目基于 Google Cloud Platform 的 Online Boutique 示例项目开发。
原项目与本项目代码遵循仓库中的 [Apache License 2.0](LICENSE)。
