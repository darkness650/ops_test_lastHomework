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
kubectl apply -f ops_test/ops/manifests-monitoring/
```

Dashboard Id: 12633
Prometheus Server URL: http://prometheus:9090

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
minikube service prometheus -n monitoring
```

Grafana：

```bash
minikube service grafana -n monitoring
```

Kibana：

```bash
minikube service kibana -n kube-system
```

Chaos Mesh Dashboard：

```bash
minikube service chaos-dashboard -n chaos-testing
```