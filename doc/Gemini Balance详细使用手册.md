好的，这是 `snailyp-gemini-balance` 代码库的详细使用手册。

***

# Gemini Balance 使用手册

## 1. 项目简介

**Gemini Balance** 是一个基于 Python 和 FastAPI 构建的应用程序，其核心功能是作为 Google Gemini API 的代理和负载均衡器。它允许用户通过简单的配置来管理和轮换多个 Gemini API 密钥，同时提供了如身份验证、模型过滤、状态监控、图像生成和 OpenAI API 格式兼容等一系列强大功能。

该项目旨在为开发者提供一个稳定、高效且功能丰富的 Gemini API 管理和使用方案。

**主要特性：**

*   **多密钥负载均衡**：通过轮询机制自动管理和使用多个 Gemini API 密钥。
*   **可视化管理后台**：提供 Web界面，用于实时监控密钥状态、查看日志和动态修改配置。
*   **双协议兼容**：同时支持原生 Gemini API 和 OpenAI Chat API 格式的请求。
*   **丰富的功能扩展**：集成了文生图、图文对话、网页搜索、文本转语音（TTS）等高级功能。
*   **强大的容错机制**：支持请求失败后自动重试，并能自动禁用失效的密钥。
*   **全面的日志系统**：记录详细的请求和错误日志，方便问题排查和性能分析。
*   **代理支持**：支持配置 HTTP/SOCKS5 代理进行网络请求。
*   **容器化部署**：提供 Docker 镜像和 Docker Compose 配置，简化部署流程。

**注意**：此项目采用 **CC BY-NC 4.0** 许可证，严禁任何形式的商业转售行为。

---

## 2. 快速入门

您可以根据自己的环境选择以下三种部署方式中的任意一种。

### 方式一：Docker Compose（推荐）

这是最推荐的部署方式，可以一键启动应用服务和数据库。

1.  **下载配置文件**:
    从项目仓库获取 `docker-compose.yml` 文件。

2.  **创建并配置 `.env` 文件**:
    复制项目中的 `.env.example` 文件并重命名为 `.env`。然后根据以下说明修改配置：
    *   `DATABASE_TYPE`: 保持 `mysql`。
    *   `MYSQL_HOST`: 保持 `gemini-balance-mysql` (这是 docker-compose 内部的服务名)。
    *   `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE`: 设置您的数据库用户名、密码和库名（需要与 `docker-compose.yml` 中 `environment` 部分的设置保持一致）。
    *   `API_KEYS`: **（必填）** 在方括号中填入您的一个或多个 Gemini API 密钥，用逗号隔开。
    *   `ALLOWED_TOKENS`: **（必填）** 设置至少一个用于访问此服务的授权令牌（Bearer Token）。

3.  **启动服务**:
    在包含 `docker-compose.yml` 和 `.env` 文件的目录下，执行以下命令：
    ```bash
    docker-compose up -d
    ```
    服务将在后台启动，应用程序可通过 `http://localhost:8000` 访问。

### 方式二：Docker 命令

如果您只想单独运行应用程序容器（例如，您已有外部数据库），可以使用此方式。

1.  **拉取 Docker 镜像**:
    ```bash
    docker pull ghcr.io/snailyp/gemini-balance:latest
    ```

2.  **创建并配置 `.env` 文件**:
    同上，复制并配置 `.env` 文件。确保数据库配置指向您可访问的数据库实例。

3.  **运行容器**:
    ```bash
    docker run -d -p 8000:8000 --name gemini-balance \
    -v ./data:/app/data \
    --env-file .env \
    ghcr.io/snailyp/gemini-balance:latest
    ```
    *   `-p 8000:8000`: 将容器的 8000 端口映射到主机的 8000 端口。
    *   `-v ./data:/app/data`: 将本地的 `data` 目录挂载到容器内，用于持久化 SQLite 数据库等数据。
    *   `--env-file .env`: 从 `.env` 文件加载环境变量。

### 方式三：本地开发环境运行

适合需要进行二次开发或调试的用户。

1.  **克隆项目并安装依赖**:
    ```bash
    git clone https://github.com/snailyp/gemini-balance.git
    cd gemini-balance
    pip install -r requirements.txt
    ```

2.  **创建并配置 `.env` 文件**:
    同上，复制并配置 `.env` 文件。您可以选择使用 `sqlite` 数据库以便于快速启动。

3.  **启动应用**:
    ```bash
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    ```
    应用启动后，同样可以通过 `http://localhost:8000` 访问。`--reload` 参数会使应用在代码变更后自动重启。

---

## 3. Web 管理界面

项目提供了一个功能强大的 Web 管理后台，方便用户进行监控和配置。

### 3.1. 访问和认证

1.  **访问入口**：通过浏览器访问 `http://<你的服务器地址>:8000`。
2.  **身份认证**：首次访问会进入认证页面。您需要输入在 `.env` 文件中 `AUTH_TOKEN` 配置的超级管理员令牌才能登录。登录成功后，凭证将保存在 Cookie 中，有效期由 `ADMIN_SESSION_EXPIRE` 配置项决定（默认为1小时）。

### 3.2. 功能页面

管理后台主要包含三个页面，可通过页面顶部的导航栏切换：

*   **监控面板 (`/keys`)**:
    *   **实时统计**: 显示1分钟、1小时、24小时和本月的 API 调用总数、成功数和失败数。
    *   **密钥状态**: 以列表形式展示所有 Gemini API 密钥的状态，分为“有效密钥”和“无效密钥”两个区域。每个密钥都会显示其当前的失败次数。
    *   **密钥操作**:
        *   **批量验证/重置**: 可以对选中的有效或无效密钥进行批量有效性验证或重置失败计数。
        *   **单个操作**: 可以对单个密钥进行验证、重置失败计数或删除。
        *   **添加密钥**: 支持通过正则表达式批量添加密钥，系统会自动去重。

*   **配置编辑 (`/config`)**:
    *   **实时配置**: 在此页面修改的所有配置项都会**立即生效**，无需重启服务。
    *   **配置分组**: 配置项按功能分为数据库、API、模型、图像生成、日志安全等多个类别，方便查找和修改。
    *   **保存与重置**: 修改后点击“保存配置”即可生效。如果配置混乱，可以点击“重置配置”从 `.env` 文件和环境变量中重新加载初始设置。

*   **错误日志 (`/logs`)**:
    *   **日志列表**: 集中展示所有 API 调用失败的错误日志。
    *   **强大筛选**: 支持按密钥、错误类型、错误码和时间范围进行精确筛选和搜索。
    *   **详细信息**: 点击任意一条日志的“详情”按钮，可以查看完整的错误信息和当时引发错误的请求报文，极大地简化了调试过程。
    *   **批量操作**: 支持批量删除选中的日志，或一键清空所有日志。

---

## 4. API 端点详解

Gemini Balance 提供了与原生 Gemini 和 OpenAI 兼容的 API 端点。

### 4.1. OpenAI API 格式

这是项目推荐使用的 API 格式，因为它支持负载均衡、失败重试等所有高级功能。

#### 基础 URL

*   **推荐 (支持高级功能)**: `http://localhost:8000/hf/v1`
*   **标准 (仅转发)**: `http://localhost:8000/v1` 或 `http://localhost:8000/openai/v1`

#### API 端点

*   **模型列表**: `GET /models`
    *   返回一个兼容 OpenAI 格式的模型列表，其中包含了所有可用的 Gemini 模型以及通过配置衍生的特殊功能模型（如 `-search`, `-image`）。

*   **聊天补全**: `POST /chat/completions`
    *   核心功能端点，完全兼容 OpenAI 的 `/chat/completions` 接口。
    *   支持流式 (`stream: true`) 和非流式响应。
    *   会根据 `API_KEYS` 列表进行负载均衡和失败重试。

*   **文本嵌入**: `POST /embeddings`
    *   兼容 OpenAI 的 `/embeddings` 接口，用于生成文本向量。
    *   底层调用 Gemini 的 `text-embedding-004` 或等效模型。

*   **图像生成**: `POST /images/generations`
    *   兼容 OpenAI 的 `/images/generations` 接口。
    *   底层调用 Google 的 `imagen-3.0-generate-002` 模型进行图像生成。需要配置付费密钥 `PAID_KEY`。

### 4.2. Gemini API 格式

此端点主要用于直接转发到 Google 官方 API，不经过项目的高级功能处理（如负载均衡）。

#### 基础 URL

*   `http://localhost:8000/gemini/v1beta`
*   `http://localhost:8000/v1beta`

#### API 端点

*   **模型列表**: `GET /models`
*   **内容生成**: `POST /models/{model_name}:generateContent`
*   **流式内容生成**: `POST /models/{model_name}:streamGenerateContent`

---

## 5. 高级功能使用指南

### 5.1. 网页搜索

*   **配置**: 在 `.env` 或后台配置 `SEARCH_MODELS` 列表，填入支持搜索的模型名称（如 `"gemini-2.0-flash-exp"`）。
*   **调用**: 在请求时，将模型名称设置为 `配置的模型名-search`，例如 `gemini-2.0-flash-exp-search`。
*   **效果**: 模型会根据你的问题进行网络搜索，并在回答的末尾附上引用来源链接。

### 5.2. 图文对话与图像修改

*   **配置**: 在 `.env` 或后台配置 `IMAGE_MODELS` 列表，填入支持图像处理的模型名称（如 `"gemini-2.0-flash-exp"`）。
*   **调用**: 在请求时，将模型名称设置为 `配置的模型名-image`，例如 `gemini-2.0-flash-exp-image`。
*   **效果**: 你可以发送包含图像的请求，或者在对话中要求模型根据描述生成或修改图片。

### 5.3. 文本转语音 (TTS)

项目集成了两种 TTS 功能：

1.  **OpenAI 兼容 TTS**:
    *   **端点**: `POST /v1/audio/speech`
    *   **模型**: `gemini-2.5-flash-preview-tts`
    *   **说明**: 通过 OpenAI 格式的 API 调用 Gemini 的 TTS 模型，生成语音。

2.  **原生 Gemini TTS (单人/多人)**:
    *   **端点**: `POST /gemini/v1beta/models/gemini-2.5-flash-preview-tts:generateContent`
    *   **说明**: 智能检测原生 Gemini TTS 请求（包含 `responseModalities` 和 `speechConfig` 字段），并自动调用增强的 TTS 服务。支持单人和多人语音合成的复杂场景。处理失败时会自动回退到标准服务。

### 5.4. 文件 API

项目实现了对 Gemini Files API 的代理和管理。

*   **端点**:
    *   `POST /upload/v1beta/files`: 初始化文件上传。
    *   `GET /v1beta/files`: 列出已上传的文件。
    *   `GET /v1beta/files/{file_id}`: 获取单个文件的元数据。
    *   `DELETE /v1beta/files/{file_id}`: 删除文件。
*   **特性**:
    *   **自动清理**: 定时任务会自动清理已过期的文件记录和对应的 Gemini 服务器上的文件。
    *   **用户隔离**: 开启 `FILES_USER_ISOLATION_ENABLED` 后，每个用户（以来源 `ALLOWED_TOKENS` 区分）只能看到和管理自己上传的文件。

---

## 6. 详细配置项说明

所有配置项均可在 `.env` 文件中设置，或在 `/config` 页面动态修改。

| 配置项 | 描述 | 默认值 |
| :--- | :--- | :--- |
| **数据库** | | |
| `DATABASE_TYPE` | 数据库类型，支持 `mysql` 或 `sqlite`。 | `mysql` |
| `MYSQL_HOST` | MySQL 主机地址。 | `localhost` |
| `MYSQL_PORT` | MySQL 端口。 | `3306` |
| `MYSQL_USER` | MySQL 用户名。 | `your_db_user` |
| `MYSQL_PASSWORD` | MySQL 密码。 | `your_db_password` |
| `MYSQL_DATABASE` | MySQL 数据库名。 | `defaultdb` |
| **API 与密钥** | | |
| `API_KEYS` | **必需**，Gemini API 密钥列表。 | `[]` |
| `ALLOWED_TOKENS` | **必需**，允许访问本服务的授权令牌列表。 | `[]` |
| `AUTH_TOKEN` | 超级管理员令牌，用于登录后台，默认为 `ALLOWED_TOKENS` 的第一个。 | `sk-123456` |
| `MAX_FAILURES` | 单个密钥允许的最大连续失败次数，超过后将被禁用。 | `3` |
| `MAX_RETRIES` | API 请求失败后的最大重试次数。 | `3` |
| `CHECK_INTERVAL_HOURS` | 定时任务重新检查已禁用密钥的间隔（小时）。 | `1` |
| `PROXIES` | 代理服务器列表，支持 HTTP 和 SOCKS5 格式。 | `[]` |
| **模型与功能** | | |
| `TEST_MODEL` | 用于测试密钥有效性的模型。 | `gemini-1.5-flash` |
| `IMAGE_MODELS` | 支持图文对话和图像修改的模型列表。 | `["gemini-2.0-flash-exp"]` |
| `SEARCH_MODELS` | 支持网页搜索的模型列表。 | `["gemini-2.0-flash-exp"]` |
| `FILTERED_MODELS` | 需要禁用的模型列表，这些模型不会出现在模型列表中。 | `[]` |
| `SHOW_SEARCH_LINK` | 是否在搜索结果中显示引用链接。 | `true` |
| `SHOW_THINKING_PROCESS` | 是否在支持的模型响应中显示思考过程。 | `true` |
| **图像生成** | | |
| `PAID_KEY` | 用于高级功能（如图形生成）的付费 API 密钥。 | `your-paid-api-key` |
| `CREATE_IMAGE_MODEL` | 图像生成模型。 | `imagen-3.0-generate-002` |
| `UPLOAD_PROVIDER` | 生成图片后的托管服务商，支持 `smms`, `picgo`, `cloudflare_imgbed`。 | `smms` |
| `SMMS_SECRET_TOKEN` | SM.MS 的 API Token。 | `your-smms-token` |
| **日志与安全** | | |
| `LOG_LEVEL` | 日志级别，可选 `DEBUG`, `INFO`, `WARNING`, `ERROR`。 | `INFO` |
| `AUTO_DELETE_ERROR_LOGS_ENABLED`| 是否自动删除旧的错误日志。 | `true` |
| `AUTO_DELETE_ERROR_LOGS_DAYS` | 错误日志保留天数。 | `7` |
| `SAFETY_SETTINGS` | 内容安全设置，用于控制模型的响应安全等级。 | `[{"category": "HARM_CATEGORY_HARASSMENT", "threshold": "OFF"}, ...]` |
| **文件 API** | | |
| `FILES_CLEANUP_ENABLED` | 是否启用文件过期自动清理。 | `true` |
| `FILES_CLEANUP_INTERVAL_HOURS` | 文件过期清理任务的运行间隔（小时）。 | `1` |
| `FILES_USER_ISOLATION_ENABLED` | 是否启用用户文件隔离（推荐开启）。 | `true` |
| **高级设置** | | |
| `STREAM_OPTIMIZER_ENABLED` | 是否启用流式输出优化，使输出更平滑。 | `false` |
| `FAKE_STREAM_ENABLED` | 是否启用“假流式”输出，用于解决某些客户端的超时问题。 | `false` |

#api路由 #大模型 #待探索 #开源 #AI工具 #Gemini #API #负载均衡 #手册 #配置
