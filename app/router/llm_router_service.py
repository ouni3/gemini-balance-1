
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
User Prompt: \"{user_prompt}\" 
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
