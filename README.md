# ✨ Prompt Optimizer

AI 驱动的提示词优化工具。输入一段原始提示词，自动调用大模型进行结构重组和语言润色，输出更清晰、更专业、更易被 LLM 理解的优化版本。

## 功能

- **提示词优化**：自动补充角色设定、任务描述、约束条件、输出格式等缺失结构
- **多模型切换**：Web UI 上直接切换提供商，无需重启
- **可编辑结果**：优化后可手动微调，一键复制
- **私密部署**：Nginx HTTP Basic Auth，公网访问需密码

## 支持的 LLM 提供商

| 提供商 | 模型示例 | 协议 |
|--------|----------|------|
| Claude (Anthropic) | claude-sonnet-4-6 | Anthropic 原生 |
| DeepSeek | deepseek-v4-flash | OpenAI 兼容 |
| ModelScope | stepfun-ai/Step-3.7-Flash | OpenAI 兼容 |

> 添加新的 OpenAI 兼容服务只需一行配置，无需写代码。参见下方「添加新提供商」。

## 项目结构

```
prompt_optimization/
├── app.py                         # FastAPI 入口，路由定义
├── requirements.txt               # Python 依赖
├── .env.example                   # 环境变量模板
├── optimizer/
│   ├── __init__.py
│   ├── base.py                    # 抽象基类 + 优化 System Prompt
│   ├── claude_provider.py         # Anthropic Claude（原生协议）
│   ├── openai_provider.py         # 通用 OpenAI 兼容协议
│   └── factory.py                 # 工厂 + 提供商注册表
├── templates/
│   └── index.html                 # 单页 Web UI
└── static/
    └── style.css                  # 响应式样式
```

## 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/Earthaveeman/prompt-optimizer.git
cd prompt-optimizer
```

### 2. 配置环境

```bash
cp .env.example .env
```

编辑 `.env`，填入至少一个提供商的 API Key：

```bash
# 选择默认提供商
LLM_PROVIDER=deepseek

# DeepSeek
DEEPSEEK_API_KEY=sk-your-key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-flash

# ModelScope
MODELSCOPE_API_KEY=ms-your-key
MODELSCOPE_BASE_URL=https://api-inference.modelscope.cn/v1
MODELSCOPE_MODEL=stepfun-ai/Step-3.7-Flash

# Claude
ANTHROPIC_API_KEY=sk-ant-your-key
ANTHROPIC_MODEL=claude-sonnet-4-6
```

### 3. 安装依赖

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. 启动

```bash
python app.py
# 访问 http://127.0.0.1:8000
```

## 公网部署（Nginx + Basic Auth）

本项目设计为私有化部署。用 Nginx 反向代理 + HTTP Basic Auth，不改一行项目代码就能加上密码保护。

### Nginx 配置

```nginx
server {
    listen 80;
    server_name _;

    location /prompt-optimizer/ {
        auth_basic "Prompt Optimizer";
        auth_basic_user_file /etc/nginx/.htpasswd;

        proxy_pass http://127.0.0.1:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # 自动改写 HTML 中的绝对路径，无需修改项目代码
        sub_filter_once off;
        sub_filter '/api/' '/prompt-optimizer/api/';
        sub_filter '/static/' '/prompt-optimizer/static/';
    }

    location / {
        return 404;
    }
}
```

### systemd 服务

```ini
[Unit]
Description=Prompt Optimizer FastAPI App
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/prompt-optimizer
Environment=PATH=/opt/prompt-optimizer/venv/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=/opt/prompt-optimizer/venv/bin/python app.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

### 创建密码

```bash
htpasswd -c /etc/nginx/.htpasswd your-username
```

### 访问

```
https://your-server.com/prompt-optimizer/
```

未经认证的请求返回 401，根路径 `/` 返回 404，不暴露服务存在。

## API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | Web UI |
| GET | `/api/providers` | 列出可用提供商及配置状态 |
| POST | `/api/optimize` | 优化提示词 |

### POST `/api/optimize`

**请求**：
```json
{
    "text": "帮我写一份数据分析报告",
    "provider": "deepseek"
}
```

`provider` 可选，不传则使用 `.env` 中 `LLM_PROVIDER` 的默认值。

**响应**：
```json
{
    "optimized": "你是一位资深数据分析师。任务：撰写一份专业的数据分析报告...",
    "provider": "DeepSeek (V4-Flash) (deepseek-v4-flash)"
}
```

## 添加新提供商

在 `optimizer/factory.py` 的 `_providers` 中添加一行即可。以 Groq 为例：

```python
_providers = {
    # ...existing providers...
    "groq": _ProviderDef(
        label="Groq (Llama-3)",
        env_prefix="GROQ",
    ),
}
```

然后在 `.env` 中配置：

```bash
GROQ_API_KEY=gsk-your-key
GROQ_BASE_URL=https://api.groq.com/openai/v1
GROQ_MODEL=llama-3.1-70b-versatile
```

Web UI 会自动发现新提供商。前提是目标服务使用 OpenAI 兼容 API（绝大多数国产模型和代理都兼容）。

## 优化原理

System Prompt（`optimizer/base.py`）指导 LLM 从四个方面优化：

1. **结构** — 补充角色设定、任务描述、约束条件、输出格式等层次
2. **语言** — 修正语法、提升精确度和专业性
3. **完整性** — 对模糊之处补充合理默认约束
4. **保留意图** — 不改变用户原始需求，不添加无关内容

## 技术栈

- **后端**：FastAPI + Uvicorn
- **前端**：原生 HTML/CSS/JS（零框架依赖）
- **LLM SDK**：Anthropic Python SDK / OpenAI Python SDK
- **反向代理**：Nginx（sub_filter 实现路径透明改写）

## License

MIT
