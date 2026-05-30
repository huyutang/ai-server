# 企业内部AI平台 安装配置文档

> **版本**: 2.0  
> **更新日期**: 2026-05-30  
> **适用环境**: 日本SIer企业内部  
> **硬件**: 单台 RTX 5090 (32GB) 服务器

---

## 目录

1. [文档目标](#1-文档目标)
2. [系统架构](#2-系统架构)
3. [硬件要求](#3-硬件要求)
4. [BIOS 设置](#4-bios-设置)
5. [Ubuntu Server 安装](#5-ubuntu-server-安装)
6. [磁盘分区规划](#6-磁盘分区规划)
7. [分区操作步骤](#7-分区操作步骤)
8. [Ubuntu 安装选项](#8-ubuntu-安装选项)
9. [系统初始化](#9-系统初始化)
10. [固定 IP 配置](#10-固定-ip-配置)
11. [SSH 安全加固](#11-ssh-安全加固)
12. [NVIDIA 驱动安装](#12-nvidia-驱动安装)
13. [Docker 安装](#13-docker-安装)
14. [Docker 数据目录迁移](#14-docker-数据目录迁移)
15. [NVIDIA Container Toolkit](#15-nvidia-container-toolkit)
16. [Docker 统一配置](#16-docker-统一配置)
17. [Docker GPU 验证](#17-docker-gpu-验证)
18. [模型预下载](#18-模型预下载)
19. [AI 平台目录结构](#19-ai-平台目录结构)
20. [vLLM 配置 — Qwen3.5-35B-A3B](#20-vllm-配置--qwen35-35b-a3b)
21. [vLLM 配置 — Qwen3.5-35B-A3B-FP8](#21-vllm-配置--qwen35-35b-a3b-fp8)
22. [vLLM 配置 — DeepSeek-R1-Distill-Qwen-32B](#22-vllm-配置--deepseek-r1-distill-qwen-32b)
23. [启动模型服务](#23-启动模型服务)
24. [模型切换脚本](#24-模型切换脚本)
25. [Open WebUI 安装](#25-open-webui-安装)
26. [Open WebUI 接入 vLLM](#26-open-webui-接入-vllm)
27. [VSCode Cline/Roo 接入](#27-vscode-clineroo-接入)
28. [Continue 接入](#28-continue-接入)
29. [防火墙配置](#29-防火墙配置)
30. [vLLM API 密钥](#30-vllm-api-密钥)
31. [GPU 监控](#31-gpu-监控)
32. [日志管理](#32-日志管理)
33. [备份策略](#33-备份策略)
34. [端到端验证清单](#34-端到端验证清单)
35. [推荐并发人数](#35-推荐并发人数)
36. [运维手册](#36-运维手册)
37. [故障排除](#37-故障排除)

---

# 1. 文档目标

构建企业内部完全本地化的 AI 平台，数据不出公司网络。

**用途：**

- 日文式样书生成
- Coding Assistant
- SQL 生成
- Code Review
- Bug 分析
- VSCode Cline / Roo / Continue 接入
- 企业内部 AI Copilot

**前提条件：**

- 服务器可访问互联网（用于下载模型和软件包）
- 具备 Linux 基础管理能力
- 已采购符合要求的硬件

---

# 2. 系统架构

```text
┌─────────────────────────────────┐
│  员工PC                          │
│  ├─ VSCode + Cline/Roo/Continue │
│  └─ 浏览器 → Open WebUI         │
└──────────────┬──────────────────┘
               │ HTTP (OpenAI Compatible API)
               ▼
┌─────────────────────────────────┐
│  AI Server (RTX 5090)           │
│  ├─ Open WebUI (:8080)          │
│  └─ vLLM (:8000)               │
│       ├─ Qwen3.5-35B-A3B (BF16) │
│       ├─ Qwen3.5-35B-A3B-FP8 (推荐默认) │
│       └─ DeepSeek-R1-Distill-Qwen-32B (推理) │
│       （按需切换，一次运行一个）    │
└─────────────────────────────────┘
```

**运行模式说明：**

由于单张 RTX 5090 显存为 32GB，为确保模型运行质量，采用**按需切换**模式：
- 默认运行 Qwen3.5-35B-A3B-FP8（推荐，更快更省显存，支持32K上下文）
- 或运行 Qwen3.5-35B-A3B BF16（精度最高，16K上下文）
- 需要深度推理时切换到 DeepSeek-R1-Distill-Qwen-32B（Review、Bug分析、架构推理）
- 提供一键切换脚本，切换时间约 30 秒

---

# 3. 硬件要求

| 项目 | 实际配置 |
|------|----------|
| GPU | RTX 5090 32GB |
| CPU | Intel Core Ultra 9 |
| RAM | 128GB DDR5 |
| SSD | 4TB NVMe Gen4 |
| LAN | 2.5GbE |
| PSU | 1600W 80+ Platinum |
| 预算 | 约145万円 |

**PSU 说明：** RTX 5090 TDP 为 575W，加上 Intel Ultra 9 及其他组件，峰值功耗可达 800W+。1600W 电源确保充足余量和长期稳定运行。

---

# 4. BIOS 设置

开机按 DEL/F2 进入 BIOS，确认以下设置：

| 项目 | 设置 | 说明 |
|------|------|------|
| Secure Boot | Disabled | Ubuntu + NVIDIA 驱动兼容性 |
| Above 4G Decoding | Enabled | GPU 大显存映射必须 |
| Resizable BAR | Enabled | 提升 GPU 数据传输性能 |
| XMP / EXPO | Enabled | 启用内存额定频率 |
| IOMMU | Enabled | 容器 GPU 直通 |
| Boot Mode | UEFI | 不要使用 Legacy |

---

# 5. Ubuntu Server 安装

**下载：**

```text
Ubuntu Server 24.04.x LTS
https://ubuntu.com/download/server
```

**制作启动盘：**

使用 Rufus (Windows) 或 Balena Etcher (macOS/Linux) 将 ISO 写入 USB。

**启动安装：**

1. 插入 USB，开机按 F11/F12 选择 USB 启动
2. 选择 `Install Ubuntu Server`
3. 语言选择 `English`（系统语言建议英文，避免日志乱码）
4. 键盘布局选择 `Japanese` 或 `English (US)`

---

# 6. 磁盘分区规划

AI 服务器的 Docker 镜像、模型文件、缓存、日志增长速度极快。**必须手动分区**，不要使用默认自动分区。

**4TB SSD 推荐分区方案：**

| 挂载点 | 大小 | 文件系统 | 用途 |
|--------|------|----------|------|
| /boot/efi | 1GB | FAT32 | UEFI 启动 |
| /boot | 2GB | ext4 | 内核文件 |
| swap | 32GB | swap | 交换空间（RAM的1/4） |
| / | 100GB | ext4 | 系统根目录 |
| /var | 200GB | ext4 | 系统日志、apt缓存 |
| /opt | 3TB | ext4 | Docker + AI模型 + 平台数据 |
| /home | 剩余空间 | ext4 | 用户目录 |

**说明：**
- swap 设为 RAM 的 1/4 即可（128GB RAM → 32GB swap），AI 推理不依赖 swap
- `/opt` 分配最大空间，所有 AI 相关数据集中存放
- `/var` 给 200GB 足够存放系统日志（Docker 日志会配置到 /opt）

---

# 7. 分区操作步骤

安装过程中到达 `Storage Configuration` 界面时：

**1. 选择手动分区：**

```text
选择: Custom storage layout（不要选 Use entire disk）
```

**2. 创建 GPT 分区表：**

选择目标磁盘（如 `nvme0n1`），创建 `GPT Partition Table`。

**3. 依次创建分区：**

| 序号 | Size | Type/Format | Mount |
|------|------|-------------|-------|
| 1 | 1GB | EFI System Partition (FAT32) | /boot/efi |
| 2 | 2GB | ext4 | /boot |
| 3 | 32GB | swap | (swap) |
| 4 | 100GB | ext4 | / |
| 5 | 200GB | ext4 | /var |
| 6 | 3000GB | ext4 | /opt |
| 7 | 剩余 | ext4 | /home |

**4. 确认并继续安装。**

---

# 8. Ubuntu 安装选项

| 项目 | 设置 |
|------|------|
| Your name | AI Admin |
| Server name | ai-server |
| Username | aiadmin |
| Password | （设置强密码） |
| Install OpenSSH server | ✅ 勾选 |
| Featured Server Snaps | 不选任何 |

---

# 9. 系统初始化

安装完成后首次登录，执行以下操作：

**更新系统：**

```bash
sudo apt update && sudo apt upgrade -y
```

**安装基础工具：**

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
  lsb-release \
  build-essential \
  rsync \
  unzip \
  jq \
  python3-pip \
  python3-venv
```

**设置时区（日本）：**

```bash
sudo timedatectl set-timezone Asia/Tokyo
```

**确认时间同步：**

```bash
timedatectl status
```

---

# 10. 固定 IP 配置

编辑 netplan 配置：

```bash
sudo vim /etc/netplan/00-installer-config.yaml
```

内容示例（请根据实际网络环境修改）：

```yaml
network:
  version: 2
  ethernets:
    enp3s0:          # 网卡名称，用 ip link 确认
      dhcp4: no
      addresses:
        - 192.168.1.50/24
      routes:
        - to: default
          via: 192.168.1.1
      nameservers:
        addresses:
          - 192.168.1.1    # 公司DNS
          - 8.8.8.8        # 备用DNS
```

**查看网卡名称：**

```bash
ip link show
```

**应用配置：**

```bash
sudo chmod 600 /etc/netplan/00-installer-config.yaml
sudo netplan apply
```

**验证：**

```bash
ip addr show
ping -c 3 8.8.8.8
```

---

# 11. SSH 安全加固

**生成密钥对（在管理员PC上执行）：**

```bash
ssh-keygen -t ed25519 -C "aiadmin@ai-server"
```

**将公钥复制到服务器：**

```bash
ssh-copy-id aiadmin@192.168.1.50
```

**加固 SSH 配置（在服务器上执行）：**

```bash
sudo vim /etc/ssh/sshd_config
```

修改以下项：

```text
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
MaxAuthTries 3
```

**重启 SSH：**

```bash
sudo systemctl restart sshd
```

> ⚠️ **重要**：修改前确保密钥登录已测试成功，否则会被锁在外面。

---

# 12. NVIDIA 驱动安装

**安装驱动：**

```bash
sudo apt install -y linux-headers-$(uname -r)
sudo ubuntu-drivers autoinstall
```

**重启：**

```bash
sudo reboot
```

**验证驱动：**

```bash
nvidia-smi
```

预期输出应显示：
- Driver Version: 570.x 或更高
- CUDA Version: 12.8 或更高
- GPU: NVIDIA GeForce RTX 5090
- Memory: 32GB

如果 `nvidia-smi` 无输出或报错，参考[第37节故障排除](#37-故障排除)。

---

# 13. Docker 安装

**使用官方脚本安装：**

```bash
curl -fsSL https://get.docker.com | sh
```

**将当前用户加入 docker 组：**

```bash
sudo usermod -aG docker $USER
```

**重新登录使组权限生效：**

```bash
exit
# 重新 SSH 登录
```

**验证 Docker（暂不运行容器，先完成后续配置）：**

```bash
docker --version
```

---

# 14. Docker 数据目录迁移

默认 Docker 数据存储在 `/var/lib/docker`，AI 环境下镜像和容器数据增长极快，必须迁移到 `/opt`。

**停止 Docker：**

```bash
sudo systemctl stop docker
sudo systemctl stop containerd
```

**创建新目录：**

```bash
sudo mkdir -p /opt/docker
```

**迁移已有数据（如果有）：**

```bash
sudo rsync -aP /var/lib/docker/ /opt/docker/
```

**清理旧数据（迁移确认无误后）：**

```bash
sudo rm -rf /var/lib/docker
```

> ⚠️ 先不要启动 Docker，等第16节统一配置完成后再启动。

---

# 15. NVIDIA Container Toolkit

**添加 GPG 密钥：**

```bash
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey \
  | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
```

**添加软件源：**

```bash
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
  | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
  | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
```

**安装：**

```bash
sudo apt update
sudo apt install -y nvidia-container-toolkit
```

> ⚠️ 安装完成后不要单独运行 `nvidia-ctk runtime configure`，我们在下一节统一配置。

---

# 16. Docker 统一配置

将所有 Docker 配置一次性写入 `/etc/docker/daemon.json`：

```bash
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json > /dev/null << 'EOF'
{
  "data-root": "/opt/docker",
  "default-runtime": "nvidia",
  "runtimes": {
    "nvidia": {
      "args": [],
      "path": "nvidia-container-runtime"
    }
  },
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "50m",
    "max-file": "3"
  },
  "storage-driver": "overlay2"
}
EOF
```

**重新加载并启动 Docker：**

```bash
sudo systemctl daemon-reload
sudo systemctl start docker
sudo systemctl enable docker
```

**验证配置：**

```bash
docker info | grep -E "Docker Root Dir|Default Runtime|Logging Driver"
```

预期输出：

```text
Docker Root Dir: /opt/docker
Default Runtime: nvidia
Logging Driver: json-file
```

---

# 17. Docker GPU 验证

```bash
docker run --rm --gpus all nvidia/cuda:12.8.0-base-ubuntu24.04 nvidia-smi
```

应显示 GPU 信息。如果报错，参考[第37节故障排除](#37-故障排除)。

**运行完整测试：**

```bash
docker run --rm --gpus all nvidia/cuda:12.8.0-base-ubuntu24.04 \
  bash -c "nvidia-smi && echo '=== GPU Docker OK ==='"
```

---

# 18. 模型预下载

在启动 vLLM 之前，先将模型下载到本地，避免容器启动时因网络问题失败。

提供两种方案：
- **方案A**：在AI服务器上直接下载（服务器可上网时）
- **方案B**：在其他电脑预下载后传输到服务器（推荐，可提前准备）

---

## 方案A：在AI服务器上直接下载

**安装 HuggingFace CLI（hf）：**

```bash
sudo apt install -y python3-pip python3-venv pipx
pipx install huggingface-hub[cli]
pipx ensurepath
source ~/.bashrc
```

**确认 CLI 可用：**

```bash
hf version
```

**创建模型存储目录：**

```bash
sudo mkdir -p /opt/ai-platform/models
sudo chown -R $USER:$USER /opt/ai-platform
```

**下载 Qwen3.5-35B-A3B（约 18GB）：**

```bash

export HF_XET_HIGH_PERFORMANCE=1

hf download Qwen/Qwen3.5-35B-A3B \
  --local-dir /opt/ai-platform/models/Qwen3.5-35B-A3B
```

**下载 Qwen3.5-35B-A3B-FP8（约 18GB）：**

```bash
export HF_XET_HIGH_PERFORMANCE=1

hf download Qwen/Qwen3.5-35B-A3B-FP8 \
  --local-dir /opt/ai-platform/models/Qwen3.5-35B-A3B-FP8
```

**下载 DeepSeek-R1-Distill-Qwen-32B-AWQ（约 18GB）：**

```bash
export HF_XET_HIGH_PERFORMANCE=1

hf download casperhansen/DeepSeek-R1-Distill-Qwen-32B-AWQ \
  --local-dir /opt/ai-platform/models/DeepSeek-R1-Distill-Qwen-32B-AWQ
```

---

## 方案B：从其他电脑预下载后传输（推荐）

可以在任何有网络的电脑（Mac/Linux/Windows）上提前下载模型，服务器到货后通过局域网传输。

**步骤1：在预下载电脑上安装 hf CLI**

macOS：
```bash
brew install pipx
pipx install huggingface-hub[cli]
pipx ensurepath
```

Linux：
```bash
pipx install huggingface-hub[cli]
pipx ensurepath
```

**步骤2：下载模型到本地**

```bash
# 创建下载目录
mkdir -p ~/ai-models

export HF_XET_HIGH_PERFORMANCE=1

# 下载 Qwen3.5-35B-A3B（约 18GB）
hf download Qwen/Qwen3.5-35B-A3B \
  --local-dir ~/ai-models/Qwen3.5-35B-A3B

# 下载 Qwen3.5-35B-A3B-FP8（约 18GB）
hf download Qwen/Qwen3.5-35B-A3B-FP8 \
  --local-dir ~/ai-models/Qwen3.5-35B-A3B-FP8

# 下载 DeepSeek-R1-Distill-Qwen-32B-AWQ（约 18GB）
hf download casperhansen/DeepSeek-R1-Distill-Qwen-32B-AWQ \
  --local-dir ~/ai-models/DeepSeek-R1-Distill-Qwen-32B-AWQ
```

**步骤3：服务器到货后，通过 rsync 传输**

```bash
# 从预下载电脑传输到AI服务器（通过局域网，速度约 100-300MB/s）
rsync -avP --info=progress2 \
  ~/ai-models/ \
  aiadmin@192.168.1.50:/opt/ai-platform/models/
```

> 💡 也可以用外置SSD/U盘物理拷贝（适合网络慢的情况）：
> ```bash
> # 拷贝到外置存储
> cp -r ~/ai-models/ /Volumes/USB_DRIVE/ai-models/
>
> # 在服务器上从外置存储拷贝
> sudo cp -r /media/aiadmin/USB_DRIVE/ai-models/* /opt/ai-platform/models/
> ```

---

## 验证下载完成

无论使用哪种方案，最终确认模型文件完整：

```bash
ls -la /opt/ai-platform/models/Qwen3.5-35B-A3B/
ls -la /opt/ai-platform/models/Qwen3.5-35B-A3B-FP8/
ls -la /opt/ai-platform/models/DeepSeek-R1-Distill-Qwen-32B-AWQ/
```

确认包含 `config.json`、`tokenizer.json` 和模型权重文件（`.safetensors`）。

> 💡 **提示**：如果从HuggingFace下载速度慢，可设置镜像：
> ```bash
> export HF_ENDPOINT=https://hf-mirror.com
> export HF_XET_HIGH_PERFORMANCE=1
> 
> hf download Qwen/Qwen3.5-35B-A3B --local-dir ~/ai-models/Qwen3.5-35B-A3B
> ```

---

# 19. AI 平台目录结构

```bash
mkdir -p /opt/ai-platform/{compose,logs,backups,scripts}
```

最终目录结构：

```text
/opt/ai-platform/
├── models/                  # 模型文件
│   ├── Qwen3.5-35B-A3B/
│   ├── Qwen3.5-35B-A3B-FP8/
│   └── DeepSeek-R1-Distill-Qwen-32B-AWQ/
├── compose/                 # Docker Compose 文件
│   ├── docker-compose-qwen.yml
│   ├── docker-compose-qwen-fp8.yml
│   └── docker-compose-r1.yml
├── scripts/                 # 运维脚本
│   └── switch-model.sh
├── logs/                    # 应用日志
└── backups/                 # 配置备份
```

---

# 20. vLLM 配置 — Qwen3.5-35B-A3B

创建 Compose 文件：

```bash
cat > /opt/ai-platform/compose/docker-compose-qwen.yml << 'EOF'
services:
  vllm:
    image: vllm/vllm-openai:v0.8.5
    container_name: vllm-qwen
    runtime: nvidia
    ports:
      - "8000:8000"
    volumes:
      - /opt/ai-platform/models:/models:ro
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
    command:
      - --model
      - /models/Qwen3.5-35B-A3B
      - --served-model-name
      - qwen3.5-35b
      - --gpu-memory-utilization
      - "0.85"
      - --max-model-len
      - "16384"
      - --tensor-parallel-size
      - "1"
      - --trust-remote-code
      - --api-key
      - ${VLLM_API_KEY:-your-secure-api-key-here}
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 120s
EOF
```

**关键参数说明：**

| 参数 | 值 | 说明 |
|------|-----|------|
| image | vllm/vllm-openai:v0.8.5 | 锁定版本，避免意外升级 |
| --model | /models/Qwen3.5-35B-A3B | 使用本地预下载的模型 |
| --gpu-memory-utilization | 0.85 | 单模型独占GPU，留15%系统开销 |
| --max-model-len | 16384 | 最大上下文长度 |
| --api-key | 环境变量 | API访问认证 |
| 无 --quantization | — | MoE模型激活仅3B，BF16直接运行 |

> ⚠️ **重要**：Qwen3.5-35B-A3B 是 MoE（Mixture of Experts）架构，总参数35B但激活参数仅3B，不需要量化即可在32GB显存上流畅运行。

---

# 21. vLLM 配置 — Qwen3.5-35B-A3B-FP8

创建 Compose 文件：

```bash
cat > /opt/ai-platform/compose/docker-compose-qwen-fp8.yml << 'EOF'
services:
  vllm:
    image: vllm/vllm-openai:v0.8.5
    container_name: vllm-qwen-fp8
    runtime: nvidia
    ports:
      - "8000:8000"
    volumes:
      - /opt/ai-platform/models:/models:ro
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
    command:
      - --model
      - /models/Qwen3.5-35B-A3B-FP8
      - --served-model-name
      - qwen3.5-35b-fp8
      - --quantization
      - fp8
      - --gpu-memory-utilization
      - "0.85"
      - --max-model-len
      - "32768"
      - --tensor-parallel-size
      - "1"
      - --trust-remote-code
      - --api-key
      - ${VLLM_API_KEY:-your-secure-api-key-here}
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 120s
EOF
```

**与 BF16 版 Qwen 配置的区别：**

| 参数 | 值 | 说明 |
|------|-----|------|
| --quantization | fp8 | FP8 量化，RTX 5090 原生支持 FP8 tensor core |
| --max-model-len | 32768 | FP8 更省显存，可支持更长上下文（BF16版为16384） |
| --served-model-name | qwen3.5-35b-fp8 | 区分于 BF16 版本 |

> 💡 **FP8 vs BF16 对比**：FP8 版本显存占用降低约 40-50%，推理速度更快（FP8 tensor core 加速），精度损失极小。推荐作为日常默认模型使用。

---

# 22. vLLM 配置 — DeepSeek-R1-Distill-Qwen-32B

创建 Compose 文件：

```bash
cat > /opt/ai-platform/compose/docker-compose-r1.yml << 'EOF'
services:
  vllm:
    image: vllm/vllm-openai:v0.8.5
    container_name: vllm-r1
    runtime: nvidia
    ports:
      - "8000:8000"
    volumes:
      - /opt/ai-platform/models:/models:ro
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
    command:
      - --model
      - /models/DeepSeek-R1-Distill-Qwen-32B-AWQ
      - --served-model-name
      - deepseek-r1-32b
      - --quantization
      - awq
      - --gpu-memory-utilization
      - "0.85"
      - --max-model-len
      - "8192"
      - --tensor-parallel-size
      - "1"
      - --trust-remote-code
      - --api-key
      - ${VLLM_API_KEY:-your-secure-api-key-here}
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 120s
EOF
```

**与 Qwen 配置的区别：**

| 参数 | 说明 |
|------|------|
| --quantization awq | DeepSeek-R1-Distill-Qwen-32B-AWQ 是预量化模型，必须指定 |
| --served-model-name | 设为 deepseek-r1-32b，方便客户端区分 |

---

# 23. 启动模型服务

**设置 API 密钥环境变量：**

```bash
echo 'export VLLM_API_KEY="your-secure-api-key-here"' >> ~/.bashrc
source ~/.bashrc
```

> ⚠️ 请将 `your-secure-api-key-here` 替换为实际的强密码（建议32位随机字符串）。

**启动默认模型（Qwen3）：**

```bash
cd /opt/ai-platform/compose
docker compose -f docker-compose-qwen.yml up -d
```

**查看启动日志：**

```bash
docker logs -f vllm-qwen
```

等待出现以下信息表示启动成功：

```text
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**测试 API：**

```bash
curl -s http://localhost:8000/v1/models \
  -H "Authorization: Bearer $VLLM_API_KEY" | jq .
```

**测试推理：**

```bash
curl -s http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $VLLM_API_KEY" \
  -d '{
    "model": "qwen3.5-35b",
    "messages": [{"role": "user", "content": "Hello, who are you?"}],
    "max_tokens": 100
  }' | jq .choices[0].message.content
```

---

# 24. 模型切换脚本

创建一键切换脚本：

```bash
cat > /opt/ai-platform/scripts/switch-model.sh << 'EOF'
#!/bin/bash
set -e

COMPOSE_DIR="/opt/ai-platform/compose"
CURRENT=""

# 检测当前运行的模型
if docker ps --format '{{.Names}}' | grep -q "vllm-qwen-fp8"; then
    CURRENT="qwen-fp8"
elif docker ps --format '{{.Names}}' | grep -q "vllm-qwen"; then
    CURRENT="qwen"
elif docker ps --format '{{.Names}}' | grep -q "vllm-r1"; then
    CURRENT="r1"
fi

usage() {
    echo "用法: $0 [qwen|qwen-fp8|r1|status]"
    echo ""
    echo "  qwen     - 切换到 Qwen3.5-35B-A3B BF16（日常开发、式样书）"
    echo "  qwen-fp8 - 切换到 Qwen3.5-35B-A3B FP8（推荐，更快更省显存）"
    echo "  r1       - 切换到 DeepSeek-R1-Distill-Qwen-32B（深度推理、Review）"
    echo "  status   - 显示当前运行的模型"
    echo ""
    echo "当前运行: ${CURRENT:-无}"
}

stop_all() {
    echo "停止当前模型..."
    cd "$COMPOSE_DIR"
    docker compose -f docker-compose-qwen.yml down 2>/dev/null || true
    docker compose -f docker-compose-qwen-fp8.yml down 2>/dev/null || true
    docker compose -f docker-compose-r1.yml down 2>/dev/null || true
    echo "已停止。"
}

start_model() {
    local model=$1
    cd "$COMPOSE_DIR"
    echo "启动 $model ..."
    docker compose -f "docker-compose-${model}.yml" up -d
    echo "等待模型加载..."
    
    local container_name="vllm-${model}"
    local max_wait=180
    local waited=0
    
    while [ $waited -lt $max_wait ]; do
        if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
            echo "✅ $model 已就绪！(耗时 ${waited}s)"
            return 0
        fi
        sleep 5
        waited=$((waited + 5))
        echo "  等待中... (${waited}s/${max_wait}s)"
    done
    
    echo "❌ 启动超时，请检查日志: docker logs $container_name"
    return 1
}

case "${1:-}" in
    qwen)
        if [ "$CURRENT" = "qwen" ]; then
            echo "Qwen3 BF16 已在运行中。"
            exit 0
        fi
        stop_all
        start_model "qwen"
        ;;
    qwen-fp8)
        if [ "$CURRENT" = "qwen-fp8" ]; then
            echo "Qwen3 FP8 已在运行中。"
            exit 0
        fi
        stop_all
        start_model "qwen-fp8"
        ;;
    r1)
        if [ "$CURRENT" = "r1" ]; then
            echo "DeepSeek-R1-32B 已在运行中。"
            exit 0
        fi
        stop_all
        start_model "r1"
        ;;
    status)
        if [ -n "$CURRENT" ]; then
            echo "当前运行: $CURRENT"
            docker ps --filter "name=vllm" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
        else
            echo "当前无模型运行。"
        fi
        ;;
    *)
        usage
        ;;
esac
EOF

chmod +x /opt/ai-platform/scripts/switch-model.sh
```

**使用方法：**

```bash
# 查看当前状态
/opt/ai-platform/scripts/switch-model.sh status

# 切换到 Qwen3 BF16
/opt/ai-platform/scripts/switch-model.sh qwen

# 切换到 Qwen3 FP8（推荐默认）
/opt/ai-platform/scripts/switch-model.sh qwen-fp8

# 切换到 DeepSeek-R1（深度推理）
/opt/ai-platform/scripts/switch-model.sh r1
```

**添加快捷别名（可选）：**

```bash
echo 'alias ai-switch="/opt/ai-platform/scripts/switch-model.sh"' >> ~/.bashrc
source ~/.bashrc

# 之后可以简写
ai-switch qwen
ai-switch qwen-fp8
ai-switch r1
ai-switch status
```

---

# 25. Open WebUI 安装

在 vLLM 模型确认运行正常后，安装 Web 界面：

```bash
docker run -d \
  --name open-webui \
  --network host \
  -v /opt/ai-platform/open-webui:/app/backend/data \
  -e WEBUI_AUTH=true \
  --restart unless-stopped \
  ghcr.io/open-webui/open-webui:v0.6.5
```

**参数说明：**

| 参数 | 说明 |
|------|------|
| --network host | 使用主机网络，方便访问本地 vLLM |
| -v | 数据持久化到 /opt 分区 |
| WEBUI_AUTH=true | 启用用户认证 |
| v0.6.5 | 锁定版本号 |

**访问：**

```text
http://服务器IP:8080
```

首次访问时注册的用户自动成为管理员。

> 💡 如果 8080 端口冲突，可以改用 `-p 3000:8080` 替代 `--network host`。

---

# 26. Open WebUI 接入 vLLM

登录 Open WebUI 后：

1. 进入 `Admin Panel` → `Settings` → `Connections`
2. 在 `OpenAI API` 部分点击 `+` 添加连接
3. 填写：

| 项目 | 值 |
|------|-----|
| URL | http://localhost:8000/v1 |
| API Key | （你设置的 VLLM_API_KEY） |

4. 点击保存，刷新模型列表
5. 应该能看到 `qwen3.5-35b`、`qwen3.5-35b-fp8` 或 `deepseek-r1-32b`（取决于当前运行的模型）

**切换模型后：** Open WebUI 会自动检测到新模型，无需重新配置连接。

---

# 27. VSCode Cline/Roo 接入

在 VSCode 中安装 Cline 或 Roo 扩展后，配置连接：

**Cline 配置：**

1. 打开 Cline 设置
2. 选择 `API Provider` → `OpenAI Compatible`
3. 填写：

| 项目 | 值 |
|------|-----|
| Base URL | http://服务器IP:8000/v1 |
| API Key | （你设置的 VLLM_API_KEY） |
| Model | qwen3.5-35b |

**Roo 配置：**

1. 打开 Roo 设置
2. 选择 `API Provider` → `OpenAI Compatible`
3. 填写同上

> 💡 **提示**：切换模型后，需要在 Cline/Roo 中将 Model 名称改为对应的 `served-model-name`：
> - Qwen3 BF16 运行时：`qwen3.5-35b`
> - Qwen3 FP8 运行时：`qwen3.5-35b-fp8`
> - DeepSeek-R1 运行时：`deepseek-r1-32b`

---

# 28. Continue 接入

在 VSCode 中安装 Continue 扩展后，编辑配置文件：

**macOS/Linux：**

```bash
vim ~/.continue/config.yaml
```

**配置内容：**

```yaml
models:
  - model: qwen3.5-35b
    title: Qwen3.5-35B BF16 (Local)
    provider: openai
    apiBase: http://服务器IP:8000/v1
    apiKey: your-secure-api-key-here

  - model: qwen3.5-35b-fp8
    title: Qwen3.5-35B FP8 (Local)
    provider: openai
    apiBase: http://服务器IP:8000/v1
    apiKey: your-secure-api-key-here

  - model: deepseek-r1-32b
    title: DeepSeek-R1-32B (Local)
    provider: openai
    apiBase: http://服务器IP:8000/v1
    apiKey: your-secure-api-key-here
```

> 💡 三个模型都配置在列表中，但同一时间只有当前运行的模型可用。

---

# 29. 防火墙配置

**启用 UFW：**

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
```

**允许必要端口：**

```bash
# SSH
sudo ufw allow 22/tcp

# vLLM API（仅允许内网访问）
sudo ufw allow from 192.168.1.0/24 to any port 8000

# Open WebUI（仅允许内网访问）
sudo ufw allow from 192.168.1.0/24 to any port 8080
```

**启用防火墙：**

```bash
sudo ufw enable
```

**确认规则：**

```bash
sudo ufw status verbose
```

> ⚠️ 请根据实际公司内网网段修改 `192.168.1.0/24`。

---

# 30. vLLM API 密钥

API 密钥已在 docker-compose 文件中通过环境变量 `VLLM_API_KEY` 配置。

**生成强密钥：**

```bash
openssl rand -hex 32
```

**更新密钥：**

1. 修改 `~/.bashrc` 中的 `VLLM_API_KEY`
2. 重启模型服务：

```bash
ai-switch qwen  # 或 ai-switch r1
```

3. 更新所有客户端（Open WebUI、Cline、Roo、Continue）中的 API Key

**密钥管理建议：**

- 定期轮换（建议每季度）
- 不要在文档或代码中硬编码
- 不同用途可设置不同密钥（需要反向代理支持）

---

# 31. GPU 监控

**创建监控脚本：**

```bash
cat > /opt/ai-platform/scripts/gpu-monitor.sh << 'EOF'
#!/bin/bash
# GPU 状态监控 - 每分钟记录一次

LOG_DIR="/opt/ai-platform/logs"
LOG_FILE="$LOG_DIR/gpu-$(date +%Y%m%d).log"

mkdir -p "$LOG_DIR"

echo "=== $(date '+%Y-%m-%d %H:%M:%S') ===" >> "$LOG_FILE"
nvidia-smi --query-gpu=timestamp,name,temperature.gpu,utilization.gpu,utilization.memory,memory.used,memory.total,power.draw \
  --format=csv,noheader >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

# 温度告警（超过85度）
TEMP=$(nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader,nounits)
if [ "$TEMP" -gt 85 ]; then
    echo "⚠️ GPU温度过高: ${TEMP}°C" | logger -t gpu-monitor
fi
EOF

chmod +x /opt/ai-platform/scripts/gpu-monitor.sh
```

**设置定时任务：**

```bash
(crontab -l 2>/dev/null; echo "* * * * * /opt/ai-platform/scripts/gpu-monitor.sh") | crontab -
```

**实时查看 GPU 状态：**

```bash
watch -n 1 nvidia-smi
```

---

# 32. 日志管理

**Docker 日志已在 daemon.json 中限制大小（50MB × 3 文件）。**

**配置 GPU 日志轮转：**

```bash
sudo tee /etc/logrotate.d/ai-platform << 'EOF'
/opt/ai-platform/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 aiadmin aiadmin
}
EOF
```

**手动测试轮转：**

```bash
sudo logrotate -f /etc/logrotate.d/ai-platform
```

---

# 33. 备份策略

**创建备份脚本：**

```bash
cat > /opt/ai-platform/scripts/backup.sh << 'EOF'
#!/bin/bash
# AI平台配置备份

BACKUP_DIR="/opt/ai-platform/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/ai-platform-config-$DATE.tar.gz"

mkdir -p "$BACKUP_DIR"

tar -czf "$BACKUP_FILE" \
  /opt/ai-platform/compose/ \
  /opt/ai-platform/scripts/ \
  /opt/ai-platform/open-webui/ \
  /etc/docker/daemon.json \
  /etc/netplan/ \
  /etc/ssh/sshd_config \
  2>/dev/null

# 保留最近30天的备份
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +30 -delete

echo "备份完成: $BACKUP_FILE"
ls -lh "$BACKUP_FILE"
EOF

chmod +x /opt/ai-platform/scripts/backup.sh
```

**设置每周自动备份：**

```bash
(crontab -l 2>/dev/null; echo "0 3 * * 0 /opt/ai-platform/scripts/backup.sh") | crontab -
```

**备份内容说明：**

| 备份项 | 说明 |
|--------|------|
| compose/ | Docker Compose 配置 |
| scripts/ | 运维脚本 |
| open-webui/ | Open WebUI 用户数据和对话历史 |
| daemon.json | Docker 配置 |
| netplan/ | 网络配置 |
| sshd_config | SSH 配置 |

> 💡 模型文件不需要备份（可从 HuggingFace 重新下载）。

---

# 34. 端到端验证清单

安装完成后，按以下清单逐项验证：

```text
[ ] 1. nvidia-smi 显示 RTX 5090, 32GB
[ ] 2. docker info 显示 Docker Root Dir: /opt/docker
[ ] 3. docker info 显示 Default Runtime: nvidia
[ ] 4. docker run --gpus all nvidia/cuda 正常显示GPU
[ ] 5. 模型文件存在于 /opt/ai-platform/models/（3个模型目录）
[ ] 6. ai-switch qwen 启动成功
[ ] 7. curl localhost:8000/v1/models 返回模型列表
[ ] 8. curl 推理测试返回正常结果
[ ] 9. ai-switch qwen-fp8 切换成功
[ ] 10. ai-switch r1 切换成功
[ ] 11. Open WebUI 可访问并登录
[ ] 12. Open WebUI 可正常对话
[ ] 13. VSCode Cline/Roo 可连接并生成代码
[ ] 14. ufw status 显示正确的防火墙规则
[ ] 15. GPU 监控日志正常生成
[ ] 16. 重启服务器后服务自动恢复
```

**重启验证：**

```bash
sudo reboot
# 等待重启完成后
nvidia-smi
docker ps
curl -s http://localhost:8000/health
```

---

# 35. 推荐并发人数

单模型运行时的推荐并发：

| 使用场景 | Qwen3.5-35B-A3B (BF16) | Qwen3.5-35B-A3B (FP8) | DeepSeek-R1-Distill-Qwen-32B |
|----------|------------------------|------------------------|---------------------------|
| Open WebUI 聊天 | 15~25人 | 20~30人 | 15~20人 |
| 普通 Coding 辅助 | 10~15人 | 12~18人 | 10~15人 |
| Cline/Roo 重度开发 | 5~8人 | 6~10人 | 6~10人 |

> 💡 MoE 模型（Qwen3.5-35B-A3B）激活参数少，推理速度快，适合日常高并发场景。
> FP8 版本比 BF16 更省显存、推理更快，支持更长上下文（32K vs 16K），推荐作为日常默认。
> DeepSeek-R1-Distill-Qwen-32B 推理能力显著增强，适合需要深度思考的场景。

---

# 36. 运维手册

## 日常操作

**查看服务状态：**

```bash
ai-switch status
docker ps
nvidia-smi
```

**查看 vLLM 日志：**

```bash
# Qwen3 BF16 运行时
docker logs --tail 100 -f vllm-qwen

# Qwen3 FP8 运行时
docker logs --tail 100 -f vllm-qwen-fp8

# DeepSeek-R1 运行时
docker logs --tail 100 -f vllm-r1
```

**重启模型服务：**

```bash
ai-switch qwen  # 会自动停止旧服务并启动新服务
```

**更新 vLLM 版本：**

```bash
# 1. 修改 docker-compose-*.yml 中的 image 版本号
# 2. 拉取新镜像
docker pull vllm/vllm-openai:v0.8.x

# 3. 重启服务
ai-switch qwen
```

**更新 Open WebUI：**

```bash
docker stop open-webui
docker rm open-webui
docker pull ghcr.io/open-webui/open-webui:v0.6.x
# 重新运行第25节的 docker run 命令（数据已持久化，不会丢失）
```

## 定期维护

| 频率 | 任务 |
|------|------|
| 每天 | 检查 GPU 温度日志 |
| 每周 | 检查磁盘使用率 `df -h /opt` |
| 每月 | 系统安全更新 `sudo apt update && sudo apt upgrade -y` |
| 每季度 | 轮换 API 密钥 |
| 每季度 | 评估是否需要更新模型版本 |

---

# 37. 故障排除

## nvidia-smi 无输出或报错

```bash
# 检查驱动是否加载
lsmod | grep nvidia

# 重新安装驱动
sudo apt purge nvidia-*
sudo ubuntu-drivers autoinstall
sudo reboot
```

## Docker GPU 不可用

```bash
# 检查 nvidia-container-runtime
which nvidia-container-runtime

# 检查 daemon.json 配置
cat /etc/docker/daemon.json

# 重启 Docker
sudo systemctl restart docker

# 测试
docker run --rm --gpus all nvidia/cuda:12.8.0-base-ubuntu24.04 nvidia-smi
```

## vLLM 启动失败 / OOM

```bash
# 查看详细日志
docker logs vllm-qwen 2>&1 | tail -50

# 常见原因：
# 1. 显存不足 → 降低 --gpu-memory-utilization（如 0.80）
# 2. 模型文件损坏 → 重新下载模型
# 3. 另一个模型未停止 → ai-switch status 检查
```

## vLLM 响应慢

```bash
# 检查 GPU 利用率
nvidia-smi

# 检查是否有其他进程占用 GPU
nvidia-smi --query-compute-apps=pid,name,used_memory --format=csv

# 降低 max-model-len 可提升速度
# 在 docker-compose 中将 16384 改为 8192
```

## Open WebUI 无法连接 vLLM

```bash
# 确认 vLLM 正在运行
curl http://localhost:8000/health

# 确认 API Key 正确
curl -s http://localhost:8000/v1/models \
  -H "Authorization: Bearer $VLLM_API_KEY"

# 如果使用 --network host，确认端口未被占用
ss -tlnp | grep 8000
```

## 磁盘空间不足

```bash
# 检查各分区使用情况
df -h

# 清理 Docker 无用镜像
docker system prune -a

# 清理旧日志
find /opt/ai-platform/logs -name "*.log" -mtime +7 -delete
```

## 服务器重启后服务未恢复

```bash
# Docker 容器设置了 restart: unless-stopped
# 如果未自动启动，手动启动：
ai-switch qwen

# 确认 Docker 服务开机自启
sudo systemctl enable docker
```

---

# 附录 A：完整文件清单

安装完成后，服务器上的关键文件：

```text
/etc/docker/daemon.json                              # Docker 配置
/etc/netplan/00-installer-config.yaml                # 网络配置
/etc/ssh/sshd_config                                 # SSH 配置
/etc/logrotate.d/ai-platform                         # 日志轮转
/opt/docker/                                         # Docker 数据
/opt/ai-platform/models/Qwen3.5-35B-A3B/              # Qwen3 BF16 模型
/opt/ai-platform/models/Qwen3.5-35B-A3B-FP8/          # Qwen3 FP8 模型
/opt/ai-platform/models/DeepSeek-R1-Distill-Qwen-32B-AWQ/  # R1 模型
/opt/ai-platform/compose/docker-compose-qwen.yml     # Qwen3 BF16 配置
/opt/ai-platform/compose/docker-compose-qwen-fp8.yml # Qwen3 FP8 配置
/opt/ai-platform/compose/docker-compose-r1.yml       # R1 配置
/opt/ai-platform/scripts/switch-model.sh             # 模型切换脚本
/opt/ai-platform/scripts/gpu-monitor.sh              # GPU 监控
/opt/ai-platform/scripts/backup.sh                   # 备份脚本
/opt/ai-platform/open-webui/                         # WebUI 数据
/opt/ai-platform/logs/                               # 监控日志
/opt/ai-platform/backups/                            # 配置备份
```

---

# 附录 B：快速命令参考

```bash
# 模型管理
ai-switch status          # 查看当前模型
ai-switch qwen            # 切换到 Qwen3 BF16
ai-switch qwen-fp8        # 切换到 Qwen3 FP8（推荐）
ai-switch r1              # 切换到 DeepSeek-R1

# 服务状态
docker ps                 # 查看运行中的容器
nvidia-smi                # GPU 状态
df -h /opt                # 磁盘使用

# 日志查看
docker logs -f vllm-qwen      # Qwen3 BF16 日志
docker logs -f vllm-qwen-fp8  # Qwen3 FP8 日志
docker logs -f vllm-r1        # DeepSeek-R1 日志
docker logs -f open-webui      # WebUI 日志

# API 测试
curl http://localhost:8000/health
curl http://localhost:8000/v1/models -H "Authorization: Bearer $VLLM_API_KEY"

# 备份
/opt/ai-platform/scripts/backup.sh
```

---

# 附录 C：安全注意事项

1. **API 密钥**：不要使用默认值，务必生成强随机密钥
2. **防火墙**：仅允许公司内网访问 AI 服务端口
3. **SSH**：禁用密码登录，仅使用密钥认证
4. **系统更新**：定期执行安全更新
5. **物理安全**：服务器应放置在有门禁的机房
6. **数据安全**：所有推理数据仅在本地处理，不会发送到外部

---

> **文档结束**
> 如有问题，请联系 AI 平台管理员。
