# Online Boutique 库存与进货微服务扩展

本项目基于 Google Cloud 的
[Online Boutique]示例项目扩展，新增库存管理和管理员进货功能。

新增或修改的服务：

- `inventoryservice`：查询、预留、释放和补充商品库存。
- `restockservice`：验证内部 Token，并调用库存服务完成进货。
- `frontend`：显示商品库存，并提供管理员进货页面。

本 README 介绍已在 Windows PowerShell、Docker Desktop 和 Minikube 环境中
验证通过的部署流程。

## 服务关系

```text
用户
  |
  v
frontend ------> inventoryservice
  |
  +------------> cartservice ------> redis-cart

管理员
  |
  v
frontend ------> restockservice ------> inventoryservice
```

## 环境要求

请提前安装：

- Docker Desktop
- Minikube
- `kubectl`
- Python 3（仅在本机运行单元测试时需要）

建议为 Minikube 分配至少 6 个 CPU 和 8 GB 内存。

开始前先启动 Docker Desktop，并确认 Docker Engine 正常：

```powershell
docker version
```

输出中应同时包含 Client 和 Server 信息。

## 1. 启动 Minikube

在 PowerShell 中执行：

```powershell
minikube start --driver=docker --cpus=6 --memory=8192
kubectl config use-context minikube
kubectl get nodes
```

如果已经存在正常运行的 Minikube 集群，不需要重新创建。

## 2. 切换到 Minikube Docker 环境

在项目根目录执行：

```powershell
& minikube -p minikube docker-env --shell powershell | Invoke-Expression
```

此命令只对当前 PowerShell 窗口有效。后面的 `docker pull`、`docker build`
和部署命令都应在同一个窗口执行。

## 3. 下载官方服务镜像

以下服务没有在本项目中修改，直接使用 Google 发布的 `v0.10.4` 镜像：

```powershell
$services = @(
  "adservice",
  "cartservice",
  "checkoutservice",
  "currencyservice",
  "emailservice",
  "paymentservice",
  "productcatalogservice",
  "recommendationservice",
  "shippingservice"
)

foreach ($service in $services) {
  docker pull "us-central1-docker.pkg.dev/google-samples/microservices-demo/${service}:v0.10.4"
}
```

Kustomize 已在 `kubernetes-manifests/kustomization.yaml` 中将这些服务映射到
对应的完整镜像地址，因此不需要手动添加 `latest` 标签。

## 4. 构建本项目镜像

构建修改过的三个服务：

```powershell
docker build -t frontend:latest .\src\frontend
docker build -t inventoryservice:latest .\src\inventoryservice
docker build -t restockservice:latest .\src\restockservice
```

这些 Dockerfile 的基础镜像使用 `mirror.gcr.io`，以减少 Docker Hub
认证服务连接失败对构建的影响。

检查镜像是否存在：

```powershell
docker images
```

应能看到：

```text
frontend:latest
inventoryservice:latest
restockservice:latest
```

## 5. 部署到 Kubernetes

执行：

```powershell
kubectl apply -k .\kubernetes-manifests
kubectl get pods -w
```

首次部署或更新镜像时，可能会短暂同时看到新旧两组 Pod。等待旧 Pod 被替换，
直到所有服务均显示：

```text
READY   STATUS
1/1     Running
```

按 `Ctrl+C` 停止持续观察，然后再次确认：

```powershell
kubectl get pods
kubectl get services
```

## 6. 访问应用

推荐使用 Minikube Service 命令：

```powershell
minikube service frontend-external
```

该命令会输出访问地址并尝试打开浏览器。使用 Docker 驱动时，需要保持这个
PowerShell 窗口运行。

也可以使用端口转发：

```powershell
kubectl port-forward service/frontend 8080:80
```

然后访问：

```text
http://127.0.0.1:8080
```

## 7. 管理员进货页面

在商城地址后添加 `/admin/restock`，例如：

```text
http://127.0.0.1:xxxxx/admin/restock
```

本地演示默认账号：

```text
用户名：admin
密码：admin123
```

这些凭据只用于课程演示，不应直接用于生产环境。

## 修改代码后重新部署

重新构建被修改的镜像。例如修改了前端：

```powershell
docker build -t frontend:latest .\src\frontend
kubectl rollout restart deployment/frontend
kubectl rollout status deployment/frontend
```

库存服务和进货服务分别使用：

```powershell
docker build -t inventoryservice:latest .\src\inventoryservice
kubectl rollout restart deployment/inventoryservice

docker build -t restockservice:latest .\src\restockservice
kubectl rollout restart deployment/restockservice
```

## 本地测试

以下测试不影响 Kubernetes 部署，只在需要验证 Python 服务源码时运行。请先确认：

```powershell
python --version
```

库存服务：

```powershell
python -m unittest discover -s .\src\inventoryservice -p "test_*.py"
```

进货服务：

```powershell
python -m unittest discover -s .\src\restockservice -p "test_*.py"
```

## 监控接口

库存服务指标：

```powershell
kubectl port-forward service/inventoryservice 8081:80
```

访问 `http://127.0.0.1:8081/metrics`。

进货服务指标：

```powershell
kubectl port-forward service/restockservice 8082:80
```

访问 `http://127.0.0.1:8082/metrics`。

## 常见问题

### ImagePullBackOff

先查看 Pod 实际使用的镜像：

```powershell
kubectl describe pod <Pod名称>
```

确认已经在当前 PowerShell 中执行过：

```powershell
& minikube -p minikube docker-env --shell powershell | Invoke-Expression
```

然后重新拉取或构建缺失的镜像，再部署：

```powershell
kubectl apply -k .\kubernetes-manifests
```

### Docker Hub 连接超时

如果出现以下错误：

```text
failed to fetch oauth token
TLS handshake timeout
```

表示 Docker Engine 无法连接镜像仓库，不是应用代码错误。本项目自定义服务的
Dockerfile 已使用 `mirror.gcr.io` 基础镜像；其余服务使用 Google Artifact
Registry 公共镜像。

### 页面暂时返回 HTTP 500

如果错误中包含：

```text
could not retrieve cart
connect: connection refused
```

通常是 `cartservice` 正在启动。检查：

```powershell
kubectl get pods
kubectl get endpoints cartservice
```

等待 `cartservice` 和 `redis-cart` 均为 `1/1 Running` 后刷新页面。

### 查看日志

```powershell
kubectl logs deployment/frontend
kubectl logs deployment/inventoryservice
kubectl logs deployment/restockservice
kubectl logs deployment/cartservice
```

## 停止和清理

停止集群：

```powershell
minikube stop
```

删除集群及其中的镜像和资源：

```powershell
minikube delete
```

## 主要环境变量

| 环境变量 | 作用 |
| --- | --- |
| `ADMIN_USERNAME` | 管理员用户名 |
| `ADMIN_PASSWORD` | 管理员密码 |
| `ADMIN_SESSION_TOKEN` | 管理员会话标识 |
| `RESTOCK_API_TOKEN` | 前端调用进货服务时使用的内部令牌 |
| `INVENTORY_SERVICE_URL` | 库存服务地址 |
| `RESTOCK_SERVICE_URL` | 进货服务地址 |

生产环境应使用 Kubernetes Secret 管理密码和 Token，不要直接把真实凭据写入
清单或提交到代码仓库。

## 项目来源

本项目基于 Google Cloud Platform 的 Online Boutique 示例开发，代码遵循仓库
中的 [Apache License 2.0](LICENSE)。
