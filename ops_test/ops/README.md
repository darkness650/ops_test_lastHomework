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

部署微服务：

```bash
kubectl apply -f ops_test/ops/kubernetes-manifests.yaml
```

部署Prometheus + Grafana：

```bash
kubectl apply -f ops_test/ops/manifests-monitoring/
```

部署Elasticsearch + Kibana：

```bash
kubectl apply -f ops_test/ops/manifests-logging/
```

