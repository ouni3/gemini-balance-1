好的，完全理解您的需求。您的目标非常明确：让 Gemini Balance 成为一个对 OpenAI 客户端完全透明的、无需特殊适配的中转服务。您指出的这两个端点正是实现这一目标的核心。

经过对代码库的再次深入审查，我已经为您准备了一套完整的、能解决所有问题的修改方案。我们将修复 embeddings 端点的实现逻辑，并验证 chat completions 端点的正确调用方式。

---

### 方案概述

1.  **修复 `POST /openai/v1/embeddings`**:
    *   **问题**: 当前 `openai_compatiable_routes.py` 中该端点的实现逻辑存在缺陷（会造成递归调用或错误转发），并且数据模型缺少对 `dimensions` 参数的支持。
    *   **解决方案**: 我们将修改此路由，使其**复用**项目中已经存在的、功能更完善的 `EmbeddingService`。同时，我们会更新数据模型和服务逻辑以支持 `dimensions` 参数，实现与 OpenAI 的完全兼容。

2.  **验证 `POST /openai/v1/chat/completions`**:
    *   **问题**: 根据您上次提供的日志，您在服务端应用了正确的路由前缀修复后，客户端仍然访问了错误的路径，导致 `405 Method Not Allowed`。
    *   **解决方案**: 我将再次确认服务端的代码是正确的，并为您提供一份**标准、无误的调用示例**。这可以确保只要客户端使用正确的 Base URL，该端点就能正常工作。

---

### 1. 实施标准的嵌入端点 (`/openai/v1/embeddings`)

我们将通过修改三个文件来完成此项任务，使该端点功能完备且符合 OpenAI 规范。

#### 步骤 1: 更新数据模型以支持 `dimensions`

首先，我们需要让请求模型能够接收 `dimensions` 参数。

**编辑文件: `app/domain/openai_models.py`**

在 `EmbeddingRequest` 类中添加 `dimensions` 字段。

```python
# app/domain/openai_models.py

class EmbeddingRequest(BaseModel):
    input: Union[str, List[str]]
    model: str = "text-embedding-004"
    encoding_format: Optional[str] = "float"
    dimensions: Optional[int] = None # <--- 新增此行
```
**说明**: 这使得 API 能够正确解析和验证包含 `dimensions` 参数的请求，这是 OpenAI V3 Embedding 模型的一个重要特性。

#### 步骤 2: 更新服务逻辑以处理 `dimensions`

接下来，我们需要修改 `EmbeddingService`，使其在调用上游 API 时能够传递 `dimensions` 参数。

**编辑文件: `app/service/embedding/embedding_service.py`**

修改 `create_embedding` 方法的签名和 `client.embeddings.create` 的调用。

```python
# app/service/embedding/embedding_service.py

class EmbeddingService:

    async def create_embedding(
        self, 
        input_text: Union[str, List[str]], 
        model: str, 
        api_key: str,
        dimensions: Optional[int] = None # <--- 新增 dimensions 参数
    ) -> CreateEmbeddingResponse:
        """Create embeddings using OpenAI API with database logging"""
        # ... (保留现有的日志和计时逻辑) ...
        try:
            client = openai.OpenAI(api_key=api_key, base_url=settings.BASE_URL)
            
            # 准备传递给 OpenAI 库的参数
            embedding_params = {
                "input": input_text,
                "model": model
            }
            if dimensions:
                embedding_params["dimensions"] = dimensions # <--- 如果提供了 dimensions，则添加到参数中
            
            response = client.embeddings.create(**embedding_params) # <--- 使用解包方式传递参数
            
            is_success = True
            status_code = 200
            return response
        # ... (保留现有的异常处理和 finally 逻辑) ...
```
**说明**: 此修改确保了如果客户端发送了 `dimensions` 参数，它会被正确地传递给底层的 `openai` 库，进而发送给 Gemini 的兼容端点。

#### 步骤 3: 修正并统一路由处理逻辑

这是最关键的一步。我们将修正 `/openai/v1/embeddings` 路由，使其调用我们刚刚增强过的、功能正确的 `EmbeddingService`，而不是之前有问题的逻辑。

**编辑文件: `app/router/openai_compatiable_routes.py`**

我们将修改 `embedding` 端点的依赖项和函数调用，使其与 `/hf/v1/embeddings` 端点的实现方式保持一致。

```python
# app/router/openai_compatiable_routes.py

from fastapi import APIRouter, Depends
# ... (其他 imports) ...
# 确保导入了正确的服务
from app.service.embedding.embedding_service import EmbeddingService 

# ... (保留 router 和其他依赖项的定义) ...
# ...

# 实例化正确的服务
embedding_service = EmbeddingService()

# ... (保留 /models 和 /chat/completions 路由) ...

@router.post("/embeddings")
async def embedding(
    request: EmbeddingRequest,
    _=Depends(security_service.verify_authorization),
    key_manager: KeyManager = Depends(get_key_manager),
    # 注意：这里不再需要 openai_service，我们直接使用 embedding_service
):
    """处理文本嵌入请求。"""
    operation_name = "embedding"
    async with handle_route_errors(logger, operation_name):
        logger.info(f"Handling embedding request for model: {request.model}")
        api_key = await key_manager.get_next_working_key()
        logger.info(f"Using API key: {redact_key_for_logging(api_key)}")
        
        # --- 核心修改：调用正确的服务和方法 ---
        return await embedding_service.create_embedding(
            input_text=request.input, 
            model=request.model, 
            api_key=api_key,
            dimensions=request.dimensions # <--- 传递 dimensions 参数
        )
```
**说明**: 通过这些修改，`POST /openai/v1/embeddings` 现在拥有了一条清晰、正确且功能完备的处理链路。它会接收标准的 OpenAI 请求，通过负载均衡获取一个可用的 Gemini Key，然后直接调用 Gemini API 来生成嵌入，最后返回标准的 OpenAI 格式响应。

---

### 2. 验证标准的聊天端点 (`/openai/v1/chat/completions`)

正如我们上次分析的，您在服务端对路由的**前缀修复是完全正确的**。`405 Method Not Allowed` 的错误是由于客户端请求了错误的 URL 导致的。

为了最终验证并确保此端点符合您的要求，这里提供一份标准的调用指南。

#### 服务端代码确认

请确保您的 `app/router/openai_compatiable_routes.py` 文件中，路由器的定义如下：

```python
# app/router/openai_compatiable_routes.py
router = APIRouter(prefix="/openai/v1")

@router.post("/chat/completions")
async def chat_completion(...):
    # ...
```
只要代码是这样，服务端就是配置正确的。

#### 客户端正确调用方式

您的客户端或工具**必须**将 API 的 **Base URL** 设置为 `http://<your-gemini-balance-host>/openai/v1`。

**正确调用示例 (cURL)**:
```bash
curl -X POST http://<your-gemini-balance-host>/openai/v1/chat/completions \
-H "Content-Type: application/json" \
-H "Authorization: Bearer <your-token>" \
-d '{
  "model": "gemini-1.5-pro-latest",
  "messages": [
    {
      "role": "user",
      "content": "Verify this endpoint."
    }
  ]
}'
```

**错误调用方式 (会导致 405 错误)**:
```bash
# 错误的 Base URL，缺少 /openai/v1
curl -X POST http://<your-gemini-balance-host>/chat/completions \
...```

只要您的客户端使用**包含 `/openai/v1` 前缀**的完整路径进行 `POST` 请求，该端点就能正确处理，绝不会返回 `405` 错误或进行不必要的重定向。

---

### 总结

完成以上修改后，您的 Gemini Balance 服务将：
1.  在 `POST /openai/v1/embeddings` 路径上提供一个功能完整、支持 `dimensions` 参数、完全符合 OpenAI 规范的嵌入端点。
2.  在 `POST /openai/v1/chat/completions` 路径上提供一个稳定、符合 OpenAI 规范的聊天端点，只要客户端使用正确的 Base URL 进行调用。

这些改动将使您的服务成为一个更加标准和透明的 OpenAI API 中转层，大大简化客户端的集成工作。