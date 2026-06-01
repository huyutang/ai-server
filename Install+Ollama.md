Ubuntu 24.04 + Ollama + Qwen3.5-35B-A3B 完整安装文档

适用配置：RTX 5090 32GB + 4TB SSD | 最后更新：2026-06-01

---

目录

1. 系统安装与分区
2. NVIDIA驱动安装
3. Ollama安装与配置
4. 模型部署与优化
5. 性能测试与验证
6. 常见问题排查

---

一、系统安装与分区

1.1 版本选择

推荐使用 Ubuntu 24.04 LTS (Noble Numbat)，支持至2029年。RTX 5090 需要较新的内核（≥6.8）和驱动支持，24.04 原生内核版本满足要求。

1.2 制作启动U盘

```bash
# 下载Ubuntu 24.04 LTS镜像
wget https://releases.ubuntu.com/24.04/ubuntu-24.04.1-desktop-amd64.iso

# 使用dd命令写入U盘（替换/dev/sdX为实际U盘设备）
sudo dd if=ubuntu-24.04.1-desktop-amd64.iso of=/dev/sdX bs=4M status=progress && sync
```

1.3 BIOS/UEFI设置

重启电脑，按 F2 或 Del 进入BIOS：

设置项 推荐值 说明
Secure Boot Disabled 必须关闭，否则NVIDIA驱动安装受阻
Boot Mode UEFI 使用UEFI模式，不要用Legacy
Above 4G Decoding Enabled 确保大显存正常工作
Resizable BAR Enabled 提升GPU性能

1.4 磁盘分区方案（4TB SSD）

安装类型选择 "其他选项" 手动分区，确保 AI 相关数据集中存放：

挂载点 大小 文件系统 说明
/boot/efi 1 GB FAT32 EFI引导分区
/boot 2 GB ext4 内核文件
swap 32 GB swap 交换空间
/ 100 GB ext4 系统根目录
/var 200 GB ext4 系统日志、apt缓存
/opt 3 TB ext4 Docker + AI模型 + 平台数据
/home 剩余空间 ext4 用户目录

```bash
# 创建 AI 平台根目录
sudo mkdir -p /opt/ai-platform
sudo chown -R $(whoami):$(whoami) /opt/ai-platform
```

1.5 系统初始化

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装基础工具
sudo apt install -y curl wget git vim htop net-tools build-essential

# 配置国内软件源（可选，加速下载）
sudo sed -i 's/archive.ubuntu.com/mirrors.aliyun.com/g' /etc/apt/sources.list
sudo apt update
```

---

二、NVIDIA驱动安装

2.1 环境清理

```bash
# 卸载旧驱动
sudo apt purge nvidia* libnvidia* -y
sudo apt autoremove -y
sudo apt autoclean
```

2.2 安装依赖

```bash
# 安装必要编译工具
sudo apt install -y gcc-14 g++-14 make dkms

# 设置gcc-14为默认
sudo update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-14 14
sudo update-alternatives --set gcc /usr/bin/gcc-14

# 安装Linux内核头文件
sudo apt install -y linux-headers-$(uname -r)
```

2.3 安装RTX 5090驱动

RTX 5090 基于Blackwell架构，推荐使用 Ubuntu 驱动自动安装工具以获取最匹配的稳定版本。

```bash
# 安装推荐驱动
sudo ubuntu-drivers autoinstall

# 重启系统
sudo reboot
```

2.4 验证驱动

```bash
nvidia-smi
```

预期输出应显示：

```
+-----------------------------------------------------------------------------+
| NVIDIA-SMI 580.xx    Driver Version: 580.xx    CUDA Version: 13.0          |
|-------------------------------+----------------------+----------------------+
| GPU 0  NVIDIA GeForce RTX 5090 |               32256MiB |
```

2.5 配置GPU计算模式

```bash
# 启用持久模式（减少驱动加载延迟）
sudo nvidia-smi -pm 1

# 设置GPU为计算模式（可选，运行模型时自动调整）
sudo nvidia-smi -ac 5001,2000  # 如有需要
```

---

三、Ollama安装与配置

3.1 安装Ollama

```bash
# 一键安装脚本
curl -fsSL https://ollama.com/install.sh | sh

# 验证安装
ollama --version
```

3.2 配置模型存储路径（指向 /opt 分区）

```bash
# 停止Ollama服务
sudo systemctl stop ollama

# 创建模型目录并授权给 ollama 用户
sudo mkdir -p /opt/ai-platform/models/ollama
sudo chown -R ollama:ollama /opt/ai-platform/models/ollama

# 确保父目录对 ollama 用户可遍历（必须设置 x 权限）
sudo chmod 755 /opt/ai-platform
sudo chmod 755 /opt/ai-platform/models

# 配置systemd服务环境变量
sudo mkdir -p /etc/systemd/system/ollama.service.d
cat << EOF | sudo tee /etc/systemd/system/ollama.service.d/override.conf
[Service]
Environment="OLLAMA_MODELS=/opt/ai-platform/models/ollama"
Environment="OLLAMA_KEEP_ALIVE=-1"
Environment="OLLAMA_HOST=0.0.0.0:11434"
Environment="OLLAMA_NUM_GPU=1"
EOF

# 重载并重启服务
sudo systemctl daemon-reload
sudo systemctl start ollama
sudo systemctl enable ollama
```

3.3 环境变量说明

变量 值 说明
OLLAMA_MODELS /opt/ai-platform/models/ollama 模型存储路径（/opt 分区）
OLLAMA_KEEP_ALIVE -1 模型常驻内存，下次响应更快
OLLAMA_HOST 0.0.0.0:11434 允许外部访问API
OLLAMA_NUM_GPU 1 使用1张GPU（RTX 5090）

3.4 验证服务状态

```bash
# 查看服务状态
sudo systemctl status ollama

# 测试API
curl http://localhost:11434/api/generate -d '{"model": "dummy", "prompt": "test"}'
# 预期返回"model not found"即可（服务正常）
```

---

四、模型部署与优化

4.1 模型推荐：Qwen3.5-35B-A3B

根据RTX 5090 32GB配置和实测数据，推荐 Qwen3.5-35B-A3B：

属性 数值
总参数量 35B (MoE架构)
激活参数量 ~3B（每次推理）
模型大小 ~20.5 GB (Q4_K_M)
量化格式 Q4_K_M（官方推荐）
许可证 Apache 2.0

为什么选35B MoE而不是27B Dense？

· MoE架构每次只激活3B参数，生成速度更快（约165 tok/s on 5090）
· 相同显存下，长上下文处理能力更强
· 35B MoE在多项基准测试中优于27B Dense

4.2 下载模型

```bash
# 官方标签：qwen3.5:35b
ollama pull qwen3.5:35b
```

下载完成后，模型文件位于 /mnt/models/ollama/blobs/，大小约 24GB。

4.3 运行模型

基础运行

```bash
ollama run qwen3.5:35b
```

带参数运行（推荐）

```bash
ollama run qwen3.5:35b \
  --num-ctx 32768 \
  --temperature 0.7 \
  --top-p 0.95
```

API服务模式

```bash
# 模型常驻后台
ollama serve &

# 通过API调用
curl http://localhost:11434/api/generate -d '{
  "model": "qwen3.5:35b",
  "prompt": "用Python写一个快速排序算法",
  "stream": false,
  "options": {
    "temperature": 0.6,
    "num_ctx": 32768
  }
}'
```

4.4 性能优化参数

根据实测，Qwen3.5-35B MoE在Blackwell架构上的推荐配置：

参数 推荐值 说明
num_ctx 32768 上下文窗口，32GB显存下稳定
temperature 0.6-0.8 代码任务偏低，创意任务偏高
top_p 0.95 核采样阈值
repeat_penalty 1.05 减少重复输出

4.5 创建Modelfile（高级配置）

```bash
cat << EOF > Qwen35b.modelfile
FROM qwen3.5:35b

# 系统提示词
SYSTEM """你是一个专业的技术助手，擅长编程、算法和系统设计。
请用中文回答，回答时保持清晰、准确、有条理。"""

# 默认参数
PARAMETER temperature 0.6
PARAMETER top_p 0.95
PARAMETER num_ctx 32768
PARAMETER repeat_penalty 1.05

# 模板
TEMPLATE """{{- if .System }}<|im_start|>system
{{ .System }}<|im_end|>
{{- end }}
<|im_start|>user
{{ .Prompt }}<|im_end|>
<|im_start|>assistant
"""
EOF

# 构建自定义模型
ollama create my-qwen35b -f Qwen35b.modelfile

# 运行自定义模型
ollama run my-qwen35b
```

---

五、性能测试与验证

5.1 生成速度测试

```bash
ollama run qwen3.5:35b --verbose
```

在RTX 5090上的预期性能：

上下文长度 Prompt处理速度 生成速度 (tok/s)
4K ~6600 tok/s ~165 tok/s
16K ~6100 tok/s ~148 tok/s
32K ~5600 tok/s ~143 tok/s
65K ~4600 tok/s ~133 tok/s

5.2 显存占用监控

```bash
# 实时监控GPU状态
watch -n 1 nvidia-smi

# 查看Ollama GPU使用情况
ollama ps
```

预期输出应显示 100% GPU，表示所有层都在GPU上运行。

5.3 功能验证

```bash
# 测试中文对话
ollama run qwen3.5:35b "介绍一下你自己"

# 测试代码生成
ollama run qwen3.5:35b "用Python实现二分查找算法"

# 测试长上下文（处理大文件）
ollama run qwen3.5:35b "$(cat long_document.txt) 请总结这篇文章的主要内容"
```

---

六、常见问题排查

6.1 驱动安装失败

现象：运行 nvidia-smi 提示"No devices were found"

解决方案：RTX 5090必须使用开源内核模块版本

```bash
# 彻底清理后重新安装
sudo apt purge nvidia* libnvidia* -y
sudo apt autoremove -y
sudo apt install nvidia-driver-580-open
sudo reboot
```

6.2 CUDA不可用

现象：ollama run 提示CUDA not available

解决方案：检查环境变量和权限

```bash
# 检查用户组
sudo usermod -aG video $USER

# 验证CUDA可用性
ollama run qwen3.5:35b --verbose 2>&1 | grep -i cuda
```

6.3 模型加载失败

现象：Error: model requires more memory than available

解决方案：显存不足，调整上下文窗口

```bash
# 减少上下文窗口
ollama run qwen3.5:35b --num-ctx 8192

# 或限制GPU使用量
export OLLAMA_NVIDIA_GPU_MEMORY=28000
ollama run qwen3.5:35b
```

6.4 模型下载缓慢

原因：默认从ollama.com下载，海外服务器

解决方案：使用国内镜像或代理

```bash
# 使用代理（根据实际配置）
export HTTP_PROXY=http://127.0.0.1:7890
export HTTPS_PROXY=http://127.0.0.1:7890
ollama pull qwen3.5:35b
```

6.5 服务无法启动

现象：systemctl start ollama 失败

解决方案：

```bash
# 查看详细日志
journalctl -u ollama -f

# 常见原因：端口冲突
sudo netstat -tulnp | grep 11434

# 权限修复（确保 ollama 用户拥有目录所有权且父目录可遍历）
sudo chown -R ollama:ollama /opt/ai-platform/models/ollama
sudo chmod 755 /opt/ai-platform
sudo chmod 755 /opt/ai-platform/models
```

6.6 内核版本过低

现象：驱动安装后无法识别GPU

解决方案：升级内核到6.8+

```bash
# 安装Mainline工具
sudo add-apt-repository ppa:cappelikan/ppa -y
sudo apt update
sudo apt install mainline

# 安装最新稳定内核
sudo mainline install-latest

# 重启后选择新内核
sudo reboot
```

---

快速命令参考

```bash
# 系统更新
sudo apt update && sudo apt upgrade -y

# NVIDIA驱动状态
nvidia-smi

# Ollama服务管理
sudo systemctl status ollama
sudo systemctl restart ollama

# 下载模型
ollama pull qwen3.5:35b

# 运行模型
ollama run qwen3.5:35b --verbose

# API调用
curl http://localhost:11434/api/generate -d '{"model": "qwen3.5:35b", "prompt": "Hello"}'

# 查看已下载模型
ollama list

# 删除模型
ollama rm qwen3.5:35b
```

---

文档结束

如需获取最新驱动版本或模型信息，请访问：

· NVIDIA驱动：https://www.nvidia.com/en-us/drivers
· Ollama模型库：https://ollama.com/library
· Qwen3.5官方页面：https://ollama.com/library/qwen3.5:35b
