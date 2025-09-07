Of course. Using an "LLM as a Router" is an excellent and advanced approach to building a truly intelligent and efficient model dispatch system. It elevates the project from a simple load balancer to a smart, cost-aware, and task-aware AI gateway.

Here is a comprehensive architectural design for retrofitting the `Gemini Balance` project with an "LLM as a Router" capability.

---

### 1. Core Concept: The Two-Tier LLM System

The architecture revolves around a two-tier system:

1.  **Router LLM**: A fast, cheap, and highly capable model (e.g., `gemini-1.5-flash-latest`). Its sole purpose is to perform a near-instantaneous analysis of the user's prompt and decide which specialized model should handle the actual task. It acts as a "triage officer."

2.  **Worker LLMs**: A pool of more powerful, specialized, or expensive models. Each worker is optimized for a specific type of task (e.g., complex reasoning, web search, vision, code generation).

When a user sends a request to a virtual model named `AUTO`, the Router LLM is invoked first. It doesn't answer the user's question directly; instead, it outputs a structured decision (e.g., JSON) indicating which Worker LLM to use. The system then dispatches the original user request to that chosen Worker LLM.

### 2. Architectural Flowchart

This diagram illustrates the request lifecycle when using the `AUTO` model.

```mermaid
graph TD
    A[User Request: model="AUTO"] --> B{Gemini Balance API Gateway};
    B --> C[Chat Service: OpenAIChatService];
    C -- "Detects model='AUTO'" --> D{LLM Router Service};
    
    subgraph "Router Logic"
        D -- "1. Build System Prompt for Router" --> E[Construct Routing Prompt];
        E -- "2. Call Router LLM" --> F(Router LLM: gemini-1.5-flash);
        F -- "3. Get Structured Decision" --> G[Parse JSON Response: {"chosen_model": "gemini-1.5-pro-search"}];
    end

    G -- "4. Return selected model name" --> C;
    C -- "5. Replace 'AUTO' with chosen model" --> H[Modify Original Request];
    H -- "6. Dispatch to Worker" --> I{Worker LLM Pool};
    
    subgraph "Worker Execution"
        I --> J1(Worker 1: gemini-1.5-pro-latest);
        I --> J2(Worker 2: gemini-2.5-pro-search);
        I --> J3(Worker 3: text-embedding-004);
    end

    J2 -- "7. Generate final answer" --> K[Final Response];
    K -- "8. Stream/Return to User" --> B;

```

### 3. Detailed Component Design & Implementation Plan

Here’s how we'll modify the existing project structure to implement this architecture.

#### A. Configuration (`.env.example` and `app/config/config.py`)

The routing logic must be configurable. We will add new settings to define the router's behavior and its pool of available workers.

1.  **Add to `.env.example`**:
    ```env
    # --- LLM Router Configuration ---
    # The model to use as the router (must be fast and cheap).
    LLM_ROUTER_MODEL="gemini-1.5-flash-latest"

    # The default worker model to use if the router fails or is unsure.
    LLM_ROUTER_DEFAULT_WORKER="gemini-1.5-pro-latest"

    # A JSON string defining the available worker models and their descriptions.
    # The descriptions are crucial as they are passed to the router LLM for decision-making.
    LLM_ROUTER_CONFIG='[
      {
        "name": "gemini-1.5-flash-latest",
        "description": "A very fast and inexpensive model for simple tasks like summarization, translation, or answering simple questions."
      },
      {
        "name": "gemini-1.5-pro-latest",
        "description": "A powerful, general-purpose model for complex reasoning, creative writing, multi-turn dialogue, and code generation. Also handles requests containing images (vision)."
      },
      {
        "name": "gemini-2.5-pro-search",
        "description": "A specialized model for questions that require real-time information from the internet, such as news, weather, or recent events."
      }
    ]'
    ```

2.  **Update `app/config/config.py`**:
    Add these new fields to the `Settings` class to load and parse them correctly.

    ```python
    # app/config/config.py
    import json
    from typing import List, Dict, Any

    class Settings(BaseSettings):
        # ... existing settings ...
        LLM_ROUTER_MODEL: str = "gemini-1.5-flash-latest"
        LLM_ROUTER_DEFAULT_WORKER: str = "gemini-1.5-pro-latest"
        LLM_ROUTER_CONFIG: List[Dict[str, Any]] = Field(default_factory=list)

        @field_validator('LLM_ROUTER_CONFIG', mode='before')
        def parse_router_config(cls, v):
            if isinstance(v, str) and v:
                try:
                    return json.loads(v)
                except json.JSONDecodeError:
                    raise ValueError("LLM_ROUTER_CONFIG must be a valid JSON string")
            return v or []
    ```

#### B. New Module: LLM Router Service

To keep the logic clean and isolated, we'll create a new service dedicated to routing.

**Create a new file: `app/service/router/llm_router_service.py`**

```python
# app/service/router/llm_router_service.py
from app.config.config import settings
from app.domain.openai_models import ChatRequest
from app.service.chat.openai_chat_service import OpenAIChatService # To make the API call
from app.log.logger import get_main_logger
import json

logger = get_main_logger()

class LLMRouterService:
    def __init__(self, key_manager):
        # The router service itself needs to call an LLM, so it needs a chat service instance.
        self.key_manager = key_manager
        self.chat_service = OpenAIChatService(settings.BASE_URL, self.key_manager)

    def _build_routing_prompt(self, user_prompt: str) -> list:
        """Constructs the full prompt for the Router LLM."""
        
        worker_descriptions = "\n".join(
            f'- `{model["name"]}`: {model["description"]}'
            for model in settings.LLM_ROUTER_CONFIG
        )

        system_prompt = f"""
You are an expert AI model router. Your task is to analyze the user's prompt and select the most appropriate and cost-effective model from the following list to handle the request.

Available Models:
{worker_descriptions}

You must respond in a pure JSON format with the following structure:
{{
  "chosen_model": "name_of_the_selected_model",
  "reasoning": "A brief explanation of why you chose this model."
}}

Analyze the following user prompt and provide your JSON decision.
User Prompt: "{user_prompt}"
"""
        return [{"role": "user", "content": system_prompt}]

    async def select_worker_model(self, original_request: ChatRequest) -> str:
        """Uses the Router LLM to select a worker model."""
        last_user_message = next((m['content'] for m in reversed(original_request.messages) if m['role'] == 'user'), None)

        if not isinstance(last_user_message, str): # Handle multi-modal case
            last_user_message = next((part['text'] for part in last_user_message if part['type'] == 'text'), "Image analysis requested")

        if not last_user_message:
            logger.warning("Router could not find user prompt, falling back to default worker.")
            return settings.LLM_ROUTER_DEFAULT_WORKER
        
        routing_messages = self._build_routing_prompt(last_user_message)

        try:
            # Prepare the request for the router LLM
            router_api_key = await self.key_manager.get_next_working_key()
            router_request = ChatRequest(
                model=settings.LLM_ROUTER_MODEL,
                messages=routing_messages,
                temperature=0.0, # Low temperature for deterministic routing
                response_format={"type": "json_object"} # Force JSON output
            )
            
            response_dict = await self.chat_service._handle_normal_completion(
                router_request.model,
                router_request.model_dump(exclude_none=True),
                router_api_key
            )
            
            decision_json = response_dict['choices'][0]['message']['content']
            decision = json.loads(decision_json)
            
            chosen_model = decision.get("chosen_model")
            
            # Validate the choice against our available workers
            available_workers = [m['name'] for m in settings.LLM_ROUTER_CONFIG]
            if chosen_model in available_workers:
                logger.info(f"LLM Router decision: Chose '{chosen_model}'. Reason: {decision.get('reasoning')}")
                return chosen_model
            else:
                logger.warning(f"Router chose an invalid model '{chosen_model}'. Falling back to default.")
                return settings.LLM_ROUTER_DEFAULT_WORKER

        except Exception as e:
            logger.error(f"LLM Router failed to make a decision: {e}. Falling back to default worker.")
            return settings.LLM_ROUTER_DEFAULT_WORKER

# Singleton instance
_router_service_instance = None
async def get_router_service(key_manager) -> LLMRouterService:
    global _router_service_instance
    if _router_service_instance is None:
        _router_service_instance = LLMRouterService(key_manager)
    return _router_service_instance
```

#### C. Integration with `OpenAIChatService`

Finally, we modify the chat service to use our new `LLMRouterService`.

**Modify `app/service/chat/openai_chat_service.py`**:

```python
# app/service/chat/openai_chat_service.py

# ... imports ...
# Add this new import
from app.service.router.llm_router_service import get_router_service

class OpenAIChatService:
    def __init__(self, base_url: str, key_manager: KeyManager = None):
        # ... existing __init__ ...
        self.key_manager = key_manager
        # No need to instantiate router here, we'll get it via dependency injection style

    async def create_chat_completion(
        self,
        request: ChatRequest,
        api_key: str,
    ) -> Union[Dict[str, Any], AsyncGenerator[str, None]]:
        """创建聊天完成"""

        if request.model.lower() == "auto":
            # Get the router service instance
            router_service = await get_router_service(self.key_manager)
            selected_model = await router_service.select_worker_model(request)
            logger.info(f"AUTO model selected. Dynamically routing to: {selected_model}")
            request.model = selected_model
        
        # ... the rest of the method remains the same ...
        messages, instruction = self.message_converter.convert(
            request.messages, request.model
        )
        payload = _build_payload(request, messages, instruction)
        if request.stream:
            return self._handle_stream_completion(request.model, payload, api_key)
        return await self._handle_normal_completion(request.model, payload, api_key)
        
    # ... all other methods remain the same ...
```

### 4. How to Use

With this architecture in place, the usage for the end-developer is incredibly simple:

1.  **Configure**: The administrator sets up the `LLM_ROUTER_*` variables in the `.env` file, defining the routing strategy.
2.  **Call**: The developer simply sends their request to the `AUTO` model. The system handles the rest.

**Example cURL call:**
```bash
curl -X POST http://<your-gemini-balance-host>:8000/hf/v1/chat/completions \
-H "Content-Type: application/json" \
-H "Authorization: Bearer <your-token>" \
-d '{
  "model": "AUTO",
  "messages": [
    {
      "role": "user",
      "content": "What are the latest developments in quantum computing this week?"
    }
  ]
}'
```
In this example, the Router LLM will see the keywords "latest developments" and "this week" and will almost certainly choose `gemini-2.5-pro-search` from its configured options.

### 5. Advantages and Considerations

*   **Advantages**:
    *   **Cost Optimization**: Simple queries are routed to cheaper models, saving money.
    *   **Performance**: Fast models are used for simple tasks, reducing latency.
    *   **Accuracy**: The best model is chosen for the specific task (e.g., vision, search), improving the quality of the response.
    *   **Extreme Flexibility**: The entire routing logic can be changed just by modifying the descriptions in the config and the system prompt, without deploying new code.

*   **Considerations**:
    *   **Increased Latency**: There is an added delay from the initial call to the Router LLM. This is why using a very fast model like `gemini-1.5-flash` is critical.
    *   **Cost of Routing**: Every `AUTO` call now incurs the small cost of the router model's inference.
    *   **Router Reliability**: The system's effectiveness depends heavily on the quality of the system prompt and the router's ability to follow instructions. A robust default fallback (`LLM_ROUTER_DEFAULT_WORKER`) is essential.