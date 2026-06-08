# 部署文档

## 安装 minikube

bash
```bash
minikube start \
    --driver=docker \
    --cpus=12 \
    --memory=7605MB \
    --image-mirror-country=cn \
    --registry-mirror=https://docker.njdldkl666699.dpdns.org \
    --registry-mirror=https://k8s.njdldkl666699.dpdns.org \
    --registry-mirror=https://quay.njdldkl666699.dpdns.org
```

powershell
```powershell
minikube start `
    --driver=docker `
    --cpus=12 `
    --memory=7605MB `
    --image-mirror-country=cn `
    --registry-mirror=https://docker.njdldkl666699.dpdns.org `
    --registry-mirror=https://k8s.njdldkl666699.dpdns.org `
    --registry-mirror=https://quay.njdldkl666699.dpdns.org
```

## 部署项目

### 微服务

```bash
kubectl apply -f ops_test/ops/kubernetes-manifests.yaml
```

### Prometheus + Grafana

```bash
# 如有必要，先删除之前的monitoring命名空间
kubectl delete namespace monitoring
# 使用国内镜像安装kube-prometheus-stack
helm repo add prometheus-community "https://helm-charts.itboon.top/prometheus-community"
helm repo update
helm install prometheus prometheus-community/kube-prometheus-stack --namespace monitoring --create-namespace
```

获取Grafana解密后的admin密码：

bash
```bash
kubectl get secret prometheus-grafana -n monitoring -o jsonpath="{.data.admin-password}" | base64 --decode ; echo
```

```powershell
$secret = kubectl get secret prometheus-grafana -n monitoring -o jsonpath="{.data.admin-password}"
$password = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($secret))
Write-Host "Grafana admin password: $password"
```

在Grafana的登录界面输入用户名admin和刚才获取的密码，就可以访问Grafana了。推荐使用的仪表板：`1860`，可以显示相当完整的Kubernetes集群状态。

> Nearly all default values exported by Prometheus node exporter graphed.

### Elasticsearch + Kibana（可选）

```bash
kubectl apply -f ops_test/ops/manifests-logging/
```

初始化Elasticsearch

```bash
kubectl get pods -n kube-system
# 找到elasticsearch的pod名称，例如elasticsearch-xxxxx
kubectl exec -it elasticsearch-7b7b648484-zv7fr -n kube-system -- /bin/bash
```

进入pod后，执行以下命令：

```bash
cd /usr/share/elasticsearch/
bin/elasticsearch-create-enrollment-token -s kibana
```

复制生成的token，退出pod。使用minikube的端口转发功能启动kibana：

```bash
minikube service kibana -n kube-system
```

在浏览器中粘贴刚才的token。

### Chaos Mesh

```bash
helm repo add chaos-mesh https://charts.chaos-mesh.org 
helm install chaos-mesh chaos-mesh/chaos-mesh --namespace chaos-testing --create-namespace
```

将仓库内的rbac.yaml应用到集群，然后生成Token，配置Chaos Mesh Dashboard的权限：

```bash
kubectl apply -f ops_test/ops/rbac.yaml
kubectl -n default create token account-cluster-manager-rqtnz
minikube service chaos-dashboard -n chaos-testing
```

打开显示隧道的http/2333对应的本地端口，在Web界面输入刚才生成Token的name和值，就可以访问Chaos Mesh的Dashboard了。

## 访问服务

前端：

```bash
minikube service frontend-external
```

Prometheus：

```bash
minikube service prometheus-kube-prometheus-prometheus -n monitoring
```

Grafana：

```bash
minikube service prometheus-grafana -n monitoring
```

Kibana：

```bash
minikube service kibana -n kube-system
```

Chaos Mesh Dashboard：

```bash
minikube service chaos-dashboard -n chaos-testing
```

# 故障注入

使用Chaos Mesh进行了故障注入实验，实验定义见`chaos/`目录，采集的指标总时间约6小时。

1. network-loss: 2026-06-04 17:51:45 PM UTC+8 创建，持续30m
2. stress-test: 2026-06-04 19:55:13 PM UTC+8 创建，持续30m

`metrics/`中存放了Grafana Node Exporter Full这个仪表板（id 1860）的有波动指标的csv数据文件。