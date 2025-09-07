好的，这是一份为未来开发者准备的、覆盖整个项目、模块化且任务驱动的**权威编程架构指南**。这份指南旨在帮助任何缺乏全局视角的开发者快速理解项目结构、设计哲学，并能安全、高效地进行后续维护和功能扩展。

---

### **Gemini Balance - 权威编程架构与开发指南**

#### **1. 核心设计哲学**

在修改任何代码之前，请务必理解本项目的核心设计原则：

1.  **分层与解耦 (Layering & Decoupling)**: 项目严格遵循 **表现层 (Router) -> 业务逻辑层 (Service) -> 数据访问层 (Database)** 的分层结构。**绝对禁止**在路由层直接操作数据库或实现复杂逻辑。
2.  **配置驱动 (Configuration-Driven)**: 几乎所有行为都由配置 (`app/config/config.py` 和 `.env`) 控制。新增功能时，优先考虑通过添加配置项来实现，而不是硬编码。
3.  **服务单例化 (Singleton Services)**: 核心服务（如 `KeyManager`, `FilesService`）通过工厂函数 (`get_..._instance`) 作为单例存在，确保状态在整个应用中一致。
4.  **面向接口而非实现 (Interface-Oriented)**: 尽管 Python 是动态语言，但代码逻辑上遵循接口思想。例如，`OpenAIChatService` 和 `GeminiChatService` 提供相似的方法，使得替换和扩展变得容易。
5.  **全面的日志记录 (Comprehensive Logging)**: 任何关键操作、API 调用、错误都必须被记录。日志是项目唯一的“黑匣子”，是调试和监控的生命线。

---

#### **2. 项目模块导览 (代码地图)**

当你需要修改或添加功能时，请先通过这张地图找到你应该工作的“区域”。

| 模块路径 (`app/...`) | 职责 (做什么？) | 修改时机 (什么时候动这里？) | 关键文件/概念 |
| :--- | :--- | :--- | :--- |
| **`router/`** | **API 入口/表现层** | 添加新的 API 端点；修改现有端点的路径或参数。 | `openai_routes.py`, `gemini_routes.py` |
| **`service/`** | **核心业务逻辑层** | 实现 API 端点背后的具体功能；编排多个操作。 | `chat/`, `embedding/`, `key/` |
| **`handler/`** | **数据转换/处理层** | 在不同 API 格式间转换数据（如 OpenAI -> Gemini）；处理响应格式。 | `message_converter.py`, `response_handler.py` |
| **`domain/`** | **数据模型/领域对象** | 定义 API 请求和响应的数据结构 (使用 Pydantic)。 | `openai_models.py`, `gemini_models.py` |
| **`database/`** | **数据访问层** | 定义数据库表结构；提供数据库增删改查的基础服务。 | `models.py`, `services.py` |
| **`config/`** | **全局配置中心** | 定义所有可配置的参数。 | `config.py` |
| **`middleware/`** | **请求/响应管道** | 在请求到达路由前或响应返回客户端前执行全局操作（如认证、日志）。 | `middleware.py` |
| **`log/`** | **日志系统** | 配置日志格式、级别和获取日志实例。 | `logger.py` |

---

### **3. 标准开发流程 (SOP)**

当你接到一个新需求时，请严格遵循以下自上而下的流程进行开发。

**示例需求**: “添加一个新功能，允许用户通过 API 查询某个 Gemini Key 的历史使用统计。”

#### **第一步：定义 API 端点 (在 `router/` 中)**

1.  **选择或创建路由文件**: 统计功能与密钥相关，可以放在 `key_routes.py` 或新建一个 `stats_routes.py`。
2.  **定义路径和数据模型**:
    *   路径: `GET /api/keys/{api_key}/stats`
    *   请求参数: `api_key` (路径参数), `period` (查询参数, e.g., '24h', '7d')
    *   响应模型: 在 `app/domain/` 下创建一个新模型，如 `KeyStatsResponse`。
3.  **编写路由函数骨架**:
    ```python
    # app/router/key_routes.py
    @router.get("/api/keys/{api_key}/stats")
    async def get_key_stats(api_key: str, period: str = '24h'):
        # 错误：不要在这里写数据库查询！
        # 正确：调用即将创建的 Service 方法。
        stats = await stats_service.get_stats_for_key(api_key, period)
        return stats
    ```

#### **第二步：实现业务逻辑 (在 `service/` 中)**

1.  **选择或创建服务文件**: 在 `app/service/stats/stats_service.py` 中添加新方法。
2.  **编写服务方法**: 这个方法是业务逻辑的核心，它负责调用底层数据库服务来获取数据，并进行处理。
    ```python
    # app/service/stats/stats_service.py
    class StatsService:
        async def get_stats_for_key(self, api_key: str, period: str) -> dict:
            # 1. 验证输入参数 (例如, period 是否合法)
            if period not in ['24h', '7d']:
                raise ValueError("Invalid period")
            
            # 2. 调用数据库服务获取原始数据
            raw_logs = await db_services.get_request_logs_for_key(api_key, period)
            
            # 3. 处理数据 (计算总数、成功率等)
            total_calls = len(raw_logs)
            successful_calls = sum(1 for log in raw_logs if log.is_success)
            
            # 4. 组织并返回结果
            return {
                "total_calls": total_calls,
                "success_rate": (successful_calls / total_calls) if total_calls > 0 else 0
            }
    ```

#### **第三步：实现数据访问 (在 `database/` 中)**

1.  **选择或创建数据访问文件**: 在 `app/database/services.py` 中添加新函数。
2.  **编写数据库查询函数**: 这个函数只负责与数据库交互，执行纯粹的 `SELECT`, `INSERT`, `UPDATE`, `DELETE` 操作。
    ```python
    # app/database/services.py
    from sqlalchemy import select
    from .models import RequestLog
    from .connection import database
    from datetime import datetime, timedelta

    async def get_request_logs_for_key(api_key: str, period: str) -> list:
        # 1. 根据 period 计算时间范围
        if period == '24h':
            start_time = datetime.now() - timedelta(hours=24)
        # ... 其他时间段逻辑 ...

        # 2. 构建 SQLAlchemy 查询
        query = select(RequestLog).where(
            RequestLog.api_key == api_key,
            RequestLog.request_time >= start_time
        )
        
        # 3. 执行查询并返回结果
        return await database.fetch_all(query)
    ```

#### **第四步：添加配置项 (如果需要)**

如果新功能需要可配置的参数（例如，统计的时间段列表），请在 `app/config/config.py` 中添加，并在业务逻辑中使用 `settings.YOUR_NEW_CONFIG` 来访问。

---

### **4. 关键模块修改指南**

#### **修改聊天逻辑 (最常见)**

*   **文件**: `app/service/chat/openai_chat_service.py`
*   **场景**:
    *   **添加对新模型参数的支持**: 修改 `_build_payload` 函数，从 `ChatRequest` 中读取新参数，并将其添加到发送给 Gemini API 的 `payload` 中。
    *   **修改流式响应行为**: 修改 `_handle_stream_completion` 方法。例如，在 `yield` 之前对 `openai_chunk` 进行检查或修改。
    *   **添加自定义模型 (如 `AUTO`)**: 在 `create_chat_completion` 方法的开头添加逻辑，检测特定模型名称，并调用新的处理函数。

#### **添加新的 OpenAI 兼容端点**

*   **文件**: `app/router/openai_routes.py` 或 `openai_compatiable_routes.py`
*   **步骤**:
    1.  在 `app/domain/openai_models.py` 中为新端点创建请求和响应的 Pydantic 模型。
    2.  在 `app/service/` 下创建一个新的服务类来处理该端点的业务逻辑。
    3.  在路由文件中，添加新的 `@router.post(...)` 或 `@router.get(...)` 函数，并调用你创建的服务。

#### **修改 Web 管理界面**

*   **前端文件**: `app/templates/*.html` (HTML 结构) 和 `app/static/js/*.js` (交互逻辑)。
*   **后端文件**: `app/router/routes.py` (页面渲染和数据提供)。
*   **流程**:
    1.  **后端 API**: 首先，为前端需要的数据创建一个新的 API 端点 (通常在 `app/router/` 下，如 `config_routes.py` 或 `key_routes.py`)。
    2.  **JavaScript**: 在对应的 `.js` 文件中，使用 `fetchAPI` 函数调用你新创建的后端 API。
    3.  **渲染**: 获取到数据后，使用 JavaScript 动态地更新 `.html` 文件中的 DOM 元素来展示数据。
    4.  **交互**: 为新的按钮或输入框添加事件监听器，当用户操作时，再次调用 API。

#### **修改密钥管理逻辑**

*   **文件**: `app/service/key/key_manager.py`
*   **警告**: 这是项目的核心状态管理器，**修改时必须极其小心**，特别注意异步锁 `asyncio.Lock` 的使用，以避免竞态条件。
*   **场景**:
    *   **改变密钥选择策略**: 修改 `get_next_working_key` 方法。例如，从轮询改为随机选择。
    *   **改变密钥失效逻辑**: 修改 `handle_api_failure` 方法。例如，增加更复杂的失效判断（如基于特定错误码）。

---

### **5. 编程规范与最佳实践**

*   **日志先行**: 在写任何新逻辑之前，先想好应该在哪里加日志。使用 `logger.info()`, `logger.warning()`, `logger.error()`。对于敏感信息（如 API Key），**必须**使用 `redact_key_for_logging()` 函数。
*   **异步编程**: 项目完全基于 `asyncio`。所有 I/O 操作（API 调用、数据库查询）都必须是 `async` 的，并使用 `await`。
*   **依赖注入**: FastAPI 的依赖注入系统 (`Depends`) 是获取服务实例（如 `KeyManager`）的首选方式。
*   **Pydantic 模型**: 所有 API 的输入和输出都应使用 `app/domain/` 下的 Pydantic 模型进行严格定义和验证。
*   **不要重复造轮子**: 在写新代码前，先浏览 `app/utils/helpers.py` 和现有的服务，看是否有可以复用的函数。

遵循这份指南，即使您不了解项目的每一个角落，也能像一位经验丰富的架构师一样，精准、安全地对项目进行维护和扩展。