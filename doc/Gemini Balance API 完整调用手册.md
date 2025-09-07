
好的，这是一份专门为开发者准备的、涵盖各种调用方式的 **Gemini Balance API 完整调用手册**。

***

# Gemini Balance API 完整调用手册

## 1. 准备工作：基础信息

在开始调用之前，请确保您已准备好以下两项信息：

1.  **服务基础 URL (Base URL)**：您部署 Gemini Balance 服务的地址。在本手册中，我们将使用占位符 `http://<your-gemini-balance-host>:8000`。
2.  **授权令牌 (Token)**：您在 `.env` 文件的 `ALLOWED_TOKENS` 中配置的访问令牌。

所有 API 请求都需要通过 `Authorization` 请求头进行身份验证。

**请求头格式**:
```http
Content-Type: application/json
Authorization: Bearer <your-token>
```
其中 `<your-token>` 就是您在 `ALLOWED_TOKENS` 中设置的值。

---

## 2. 核心调用方式：OpenAI API 格式 (`/hf/v1`)

这是**最推荐**的调用方式，因为它支持 Gemini Balance 提供的所有高级功能，包括多密钥负载均衡、失败自动重试、网页搜索、图像生成等。

### 2.1. 基础聊天补全 (非流式)

用于标准的一问一答。

*   **端点**: `POST /hf/v1/chat/completions`
*   **请求体**:
    ```json
    {
      "model": "gemini-1.5-pro-latest",
      "messages": [
        {
          "role": "user",
          "content": "你好，请介绍一下你自己。"
        }
      ]
    }
    ```
*   **cURL 示例**:
    ```bash
    curl -X POST http://<your-gemini-balance-host>:8000/hf/v1/chat/completions \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer <your-token>" \
    -d '{
      "model": "gemini-1.5-pro-latest",
      "messages": [
        {
          "role": "user",
          "content": "你好，请介绍一下你自己。"
        }
      ]
    }'
    ```

### 2.2. 流式聊天补全

用于实现打字机效果的实时响应。

*   **端点**: `POST /hf/v1/chat/completions`
*   **关键参数**: 在请求体中添加 `"stream": true`。
*   **请求体**:
    ```json
    {
      "model": "gemini-1.5-flash-latest",
      "messages": [
        {
          "role": "user",
          "content": "请写一首关于星空的短诗。"
        }
      ],
      "stream": true
    }
    ```
*   **cURL 示例**:
    ```bash
    curl -X POST http://<your-gemini-balance-host>:8000/hf/v1/chat/completions \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer <your-token>" \
    -d '{
      "model": "gemini-1.5-flash-latest",
      "messages": [
        {
          "role": "user",
          "content": "请写一首关于星空的短诗。"
        }
      ],
      "stream": true
    }'
    ```
*   **响应格式**: 服务器将返回 Server-Sent Events (SSE) 流，每条消息以 `data:` 开头，以 `[DONE]` 结束。

### 2.3. 网页搜索功能

调用具备联网搜索能力的模型。

*   **前置条件**: 管理员已在 Gemini Balance 配置的 `SEARCH_MODELS` 列表中添加了基础模型（例如 `gemini-2.5-pro`）。
*   **端点**: `POST /hf/v1/chat/completions`
*   **关键参数**: 将 `model` 设置为 **`基础模型名-search`**。
*   **请求体**:
    ```json
    {
      "model": "gemini-2.5-pro-search",
      "messages": [
        {
          "role": "user",
          "content": "2024年欧冠决赛的结果是什么？"
        }
      ]
    }
    ```
*   **cURL 示例**:
    ```bash
    curl -X POST http://<your-gemini-balance-host>:8000/hf/v1/chat/completions \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer <your-token>" \
    -d '{
      "model": "gemini-2.5-pro-search",
      "messages": [
        {
          "role": "user",
          "content": "2024年欧冠决赛的结果是什么？"
        }
      ]
    }'
    ```

### 2.4. 图文对话 (多模态)

向模型发送包含图片的对话内容。

*   **端点**: `POST /hf/v1/chat/completions`
*   **关键参数**: `messages` 数组中的 `content` 字段需要是一个包含文本和图片的数组。
*   **请求体**:
    ```json
    {
      "model": "gemini-1.5-flash-latest",
      "messages": [
        {
          "role": "user",
          "content": [
            {
              "type": "text",
              "text": "这张图片里有什么？"
            },
            {
              "type": "image_url",
              "image_url": {
                "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg"
              }
            }
          ]
        }
      ]
    }
    ```
*   **cURL 示例**:
    ```bash
    curl -X POST http://<your-gemini-balance-host>:8000/hf/v1/chat/completions \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer <your-token>" \
    -d '{
      "model": "gemini-1.5-flash-latest",
      "messages": [
        {
          "role": "user",
          "content": [
            { "type": "text", "text": "这张图片里有什么？" },
            { "type": "image_url", "image_url": { "url": "https://<image_url>" } }
          ]
        }
      ]
    }'
    ```

### 2.5. 图像生成

调用文生图功能。

*   **前置条件**: 管理员已在 Gemini Balance 配置中设置了 `PAID_KEY`。
*   **端点**: `POST /hf/v1/images/generations`
*   **请求体**:
    ```json
    {
      "model": "imagen-3.0-generate-002",
      "prompt": "一只戴着宇航员头盔的可爱猫咪，在月球上，数字艺术",
      "n": 1,
      "size": "1024x1024",
      "response_format": "url"
    }
    ```*   **cURL 示例**:
    ```bash
    curl -X POST http://<your-gemini-balance-host>:8000/hf/v1/images/generations \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer <your-token>" \
    -d '{
      "model": "imagen-3.0-generate-002",
      "prompt": "一只戴着宇航员头盔的可爱猫咪，在月球上，数字艺术",
      "n": 1,
      "size": "1024x1024"
    }'
    ```
*   **注意**: `model` 字段的值当前是固定的，由配置中的 `CREATE_IMAGE_MODEL` 决定。

### 2.6. 文本嵌入 (Embeddings)

将文本转换为向量表示。

*   **端点**: `POST /hf/v1/embeddings`
*   **请求体**:
    ```json
    {
      "model": "text-embedding-004",
      "input": "Gemini Balance 是一个强大的API代理工具"
    }
    ```
*   **cURL 示例**:
    ```bash
    curl -X POST http://<your-gemini-balance-host>:8000/hf/v1/embeddings \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer <your-token>" \
    -d '{
      "model": "text-embedding-004",
      "input": "Gemini Balance 是一个强大的API代理工具"
    }'
    ```

### 2.7. 文本转语音 (TTS)

将文本转换为音频。

*   **端点**: `POST /hf/v1/audio/speech`
*   **请求体**:
    ```json
    {
      "model": "gemini-2.5-flash-preview-tts",
      "input": "你好，欢迎使用 Gemini Balance。",
      "voice": "Kore"
    }
    ```
*   **cURL 示例**:
    ```bash
    curl -X POST http://<your-gemini-balance-host>:8000/hf/v1/audio/speech \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer <your-token>" \
    -d '{
      "model": "gemini-2.5-flash-preview-tts",
      "input": "你好，欢迎使用 Gemini Balance。",
      "voice": "Kore"
    }' \
    --output speech.wav
    ```
*   **注意**: 响应是 `audio/wav` 格式的音频文件，使用 `--output` 参数可将其保存到本地。

---

## 3. 辅助调用方式：原生 Gemini API 格式 (`/gemini/v1beta`)

这种方式主要用于需要与原生 Gemini API 保持完全一致的场景。它**不经过**负载均衡、失败重试等高级功能。

*   **认证方式**: 使用 `x-goog-api-key` 请求头，值为您在 `ALLOWED_TOKENS` 中设置的令牌。
*   **端点**: `POST /gemini/v1beta/models/{model_name}:generateContent`
*   **请求体 (与官方一致)**:
    ```json
    {
      "contents": [{
        "parts":[{
          "text": "写一个关于旅行的短故事。"
        }]
      }]
    }
    ```
*   **cURL 示例**:
    ```bash
    curl -X POST \
    'http://<your-gemini-balance-host>:8000/gemini/v1beta/models/gemini-1.5-flash-latest:generateContent' \
    -H 'Content-Type: application/json' \
    -H 'x-goog-api-key: <your-token>' \
    -d '{
      "contents": [{
        "parts":[{
          "text": "写一个关于旅行的短故事。"
        }]
      }]
    }'
    ```

---

## 4. 使用 Python 客户端库调用

您可以将任何兼容 OpenAI 的客户端库指向 Gemini Balance 服务。

以下是使用官方 `openai` Python 库的示例：

```python
import openai

# 初始化客户端，关键是设置 base_url 和 api_key
client = openai.OpenAI(
    base_url="http://<your-gemini-balance-host>:8000/hf/v1",
    api_key="<your-token>"  # 这里填入你在 ALLOWED_TOKENS 中配置的令牌
)

# --- 基础调用 ---
response = client.chat.completions.create(
    model="gemini-1.5-pro-latest",
    messages=[
        {"role": "user", "content": "用Python写一个快速排序算法"}
    ]
)
print(response.choices[0].message.content)

# --- 调用搜索功能 ---
search_response = client.chat.completions.create(
    model="gemini-2.5-pro-search",  # 使用 -search 后缀
    messages=[
        {"role": "user", "content": "今天天气怎么样？"}
    ]
)
print(search_response.choices[0].message.content)

# --- 流式调用 ---
stream = client.chat.completions.create(
    model="gemini-1.5-flash-latest",
    messages=[
        {"role": "user", "content": "讲个笑话"}
    ],
    stream=True
)
for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")
print()

```

---

## 5. 常见错误与排查

*   **`401 Unauthorized`**:
    *   原因：`Authorization` 请求头中的 `Bearer <token>` 不正确，或 `x-goog-api-key` 的值不在 `ALLOWED_TOKENS` 列表中。
    *   解决：请检查您的令牌是否正确。
*   **`503 Service Unavailable`**:
    *   原因：Gemini Balance 后端配置的所有 `API_KEYS` 都已失效或达到了失败次数上限。
    *   解决：请登录 Web 管理后台检查密钥状态，添加新的有效密钥或重置失效密钥的失败计数。

#api路由 #大模型 #待探索 #AI工具 #Gemini #API
