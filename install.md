# 日本SIer内部AI平台 安装配置文档（2026 企业版最终版）

# 1. 文档目标

构建企业内部本地AI平台。

用途：

* 日文式样书生成
* Coding Assistant
* SQL生成
* Code Review
* Bug分析
* VSCode Cline/Roo 接入
* 企业内部AI Copilot

---

# 2. 最终架构

```text
员工PC（VSCode + Cline/Roo）
        ↓
OpenAI Compatible API
        ↓
RTX5090 AI Server
        ↓
vLLM
        ↓
Qwen3-32B-AWQ
DeepSeek-R1-14B-AWQ
```

---

# 3. 推荐硬件

| 项目  | 推荐                    |
| --- | --------------------- |
| GPU | RTX5090 32GB          |
| CPU | Ryzen 9950X / Ultra 9 |
| RAM | 128GB DDR5            |
| SSD | 4TB NVMe Gen4         |
| LAN | 2.5GbE 以上             |
| PSU | 1200W Platinum        |

---

# 4. 操作系统

推荐：

```text
Ubuntu Server 24.04 LTS
```

下载：

https://ubuntu.com/download/server

---

# 5. BIOS 设置

进入 BIOS：

| 项目                | 设置       |
| ----------------- | -------- |
| Secure Boot       | Disabled |
| Above 4G Decoding | Enabled  |
| Resize BAR        | Enabled  |
| XMP/EXPO          | Enabled  |

---

# 6. Ubuntu 手动分区（重要）

AI服务器：

* Docker
* 模型
* Cache
* 日志

增长速度非常快。

必须：

```text
手动分区
```

不要使用默认自动分区。

---

# 7. 推荐磁盘规划（4TB SSD）

| 挂载点   | 大小    | 用途            |
| ----- | ----- | ------------- |
| EFI   | 1GB   | UEFI启动        |
| /boot | 2GB   | Kernel        |
| swap  | 64GB  | Swap          |
| /     | 200GB | Ubuntu系统      |
| /var  | 300GB | 系统日志          |
| /opt  | 2.5TB | Docker + AI模型 |
| /home | 剩余    | 用户目录          |

文件系统：

```text
ext4
```

---

# 8. Ubuntu 安装时手动分区步骤

安装 Ubuntu Server 时：

到：

```text
Storage Configuration
```

不要选择：

```text
Use entire disk
```

请选择：

```text
Custom storage layout
```

或者：

```text
Manual
```

---

# 9. 创建 GPT 分区表

选择：

```text
nvme0n1
```

创建：

```text
GPT Partition Table
```

---

# 10. 创建 EFI 分区

| 项目     | 值                    |
| ------ | -------------------- |
| Size   | 1GB                  |
| Type   | EFI System Partition |
| Format | FAT32                |
| Mount  | /boot/efi            |

---

# 11. 创建 /boot

| 项目     | 值     |
| ------ | ----- |
| Size   | 2GB   |
| Format | ext4  |
| Mount  | /boot |

---

# 12. 创建 swap

| 项目   | 值    |
| ---- | ---- |
| Size | 64GB |
| Type | swap |

---

# 13. 创建 /

| 项目     | 值     |
| ------ | ----- |
| Size   | 200GB |
| Format | ext4  |
| Mount  | /     |

---

# 14. 创建 /var

| 项目     | 值     |
| ------ | ----- |
| Size   | 300GB |
| Format | ext4  |
| Mount  | /var  |

---

# 15. 创建 /opt（非常重要）

| 项目     | 值      |
| ------ | ------ |
| Size   | 2500GB |
| Format | ext4   |
| Mount  | /opt   |

说明：

```text
AI模型与Docker数据将放在这里
```

---

# 16. 创建 /home

剩余全部空间：

| 项目     | 值         |
| ------ | --------- |
| Size   | Remaining |
| Format | ext4      |
| Mount  | /home     |

---

# 17. 安装 Ubuntu

安装时：

| 项目       | 设置        |
| -------- | --------- |
| hostname | ai-server |
| username | aiadmin   |
| OpenSSH  | 安装        |

---

# 18. 系统初始化

更新系统：

```bash
sudo apt update
sudo apt upgrade -y
```

安装工具：

```bash
sudo apt install -y \
curl \
wget \
git \
vim \
htop \
tmux \
net-tools \
ca-certificates \
gnupg \
build-essential \
rsync
```

---

# 19. 固定IP

编辑：

```bash
sudo vim /etc/netplan/00-installer-config.yaml
```

示例：

```yaml
network:
  version: 2
  ethernets:
    enp3s0:
      dhcp4: no
      addresses:
        - 192.168.1.50/24
      routes:
        - to: default
          via: 192.168.1.1
      nameservers:
        addresses:
          - 8.8.8.8
```

应用：

```bash
sudo netplan apply
```

---

# 20. 安装 NVIDIA Driver

自动安装：

```bash
sudo ubuntu-drivers autoinstall
```

重启：

```bash
sudo reboot
```

确认：

```bash
nvidia-smi
```

---

# 21. 安装 Docker

安装：

```bash
curl -fsSL https://get.docker.com | sh
```

加入 docker 组：

```bash
sudo usermod -aG docker $USER
```

重新登录。

测试：

```bash
docker run hello-world
```

---

# 22. Docker 数据目录迁移到 /opt（重要）

默认：

```text
/var/lib/docker
```

AI环境下：

Docker会快速增长。

必须迁移到：

```text
/opt/docker
```

---

# 23. 停止 Docker

```bash
sudo systemctl stop docker
```

```bash
sudo systemctl stop containerd
```

---

# 24. 创建新目录

```bash
sudo mkdir -p /opt/docker
```

---

# 25. 迁移已有数据（如果已有容器）

```bash
sudo rsync -aP /var/lib/docker/ /opt/docker
```

---

# 26. 修改 Docker 配置

创建：

```bash
sudo vim /etc/docker/daemon.json
```

内容：

```json
{
  "data-root": "/opt/docker"
}
```

---

# 27. 启动 Docker

```bash
sudo systemctl daemon-reload
```

```bash
sudo systemctl start docker
```

---

# 28. 确认迁移成功

```bash
docker info | grep "Docker Root Dir"
```

应显示：

```text
Docker Root Dir: /opt/docker
```

---

# 29. 安装 NVIDIA Container Toolkit

添加源：

```bash
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey \
| sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
```

```bash
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
| sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
| sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
```

安装：

```bash
sudo apt update
sudo apt install -y nvidia-container-toolkit
```

配置：

```bash
sudo nvidia-ctk runtime configure --runtime=docker
```

重启：

```bash
sudo systemctl restart docker
```

测试：

```bash
docker run --rm --gpus all nvidia/cuda:12.8.0-base-ubuntu24.04 nvidia-smi
```

---

# 30. 创建 AI 平台目录

```bash
sudo mkdir -p /opt/ai-platform
sudo chown -R $USER:$USER /opt/ai-platform
```

创建：

```bash
mkdir -p \
/opt/ai-platform/models \
/opt/ai-platform/compose \
/opt/ai-platform/logs \
/opt/ai-platform/backups
```

---

# 31. 安装 Open WebUI

启动：

```bash
docker run -d \
--name open-webui \
-p 3000:8080 \
-v open-webui:/app/backend/data \
--restart always \
ghcr.io/open-webui/open-webui:main
```

访问：

```text
http://服务器IP:3000
```

---

# 32. 使用 AWQ 量化模型

本环境统一使用：

```text
AWQ 预量化模型
```

原因：

* 更稳定
* 启动更快
* 显存占用更低
* 企业环境更适合
* vLLM兼容更好

---

# 33. 推荐模型

## 主模型

```text
Qwen/Qwen3-32B-AWQ
```

用途：

* 日文式样书
* Coding
* SQL
* API设计

---

## 推理模型

```text
deepseek-ai/DeepSeek-R1-Distill-Qwen-14B-AWQ
```

用途：

* Review
* Bug分析
* 架构推理

---

# 34. 安装 vLLM

进入：

```bash
cd /opt/ai-platform/compose
```

创建：

```bash
vim docker-compose.yml
```

内容：

```yaml
services:

  qwen3:
    image: vllm/vllm-openai:latest
    container_name: qwen3
    runtime: nvidia
    ports:
      - "8000:8000"
    volumes:
      - /opt/ai-platform/models:/root/.cache/huggingface
    command:
      --model Qwen/Qwen3-32B-AWQ
      --quantization awq
      --gpu-memory-utilization 0.72
      --max-model-len 8192
      --tensor-parallel-size 1
    restart: always

  r1:
    image: vllm/vllm-openai:latest
    container_name: r1
    runtime: nvidia
    ports:
      - "8001:8000"
    volumes:
      - /opt/ai-platform/models:/root/.cache/huggingface
    command:
      --model deepseek-ai/DeepSeek-R1-Distill-Qwen-14B-AWQ
      --quantization awq
      --gpu-memory-utilization 0.25
      --max-model-len 4096
      --tensor-parallel-size 1
    restart: always
```

---

# 35. 启动模型

```bash
docker compose up -d
```

查看日志：

```bash
docker logs -f qwen3
```

等待：

```text
Application startup complete
```

---

# 36. Open WebUI 接入模型

进入：

```text
Settings
→ Connections
→ OpenAI API
```

添加：

Qwen3：

```text
http://服务器IP:8000/v1
```

R1：

```text
http://服务器IP:8001/v1
```

API Key：

```text
dummy
```

---

# 37. 推荐企业使用方式

## 普通员工

使用：

```text
Open WebUI
```

---

## 核心开发

使用：

```text
Cline / Roo / Continue
```

连接：

```text
http://服务器IP:8000/v1
```

---

# 38. 推荐并发人数

| 使用场景          | 推荐人数   |
| ------------- | ------ |
| Open WebUI聊天  | 10~20人 |
| 普通Coding      | 8~15人  |
| Cline/Roo重度开发 | 3~6人   |

---

# 39. 最终建议

不要一开始：

* 上复杂Agent
* 上Kubernetes
* 上RAG
* 上超长Context

优先：

* Prompt模板统一
* 文档格式统一
* 稳定输出
* 提高开发效率

---

# 40. 最终结论

本方案是：

```text
单RTX5090 企业AI平台最佳实践
```

特点：

* 企业级稳定
* 完全本地化
* 数据不出公司
* 支持多人开发
* 支持Cline/Roo
* 支持OpenAI API
* 易维护
* 成本远低于H100方案
