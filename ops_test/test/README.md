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
kubectl apply -f kubernetes-manifests.yaml
```

部署fluent收集日志：

```bash
kubectl apply -f manifests-logging/
```

注：收集日志需要在创建miinikube的时候指定数据卷挂载，根据你想要存放目录的位置进行挂载
