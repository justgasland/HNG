import logging
import json
import uuid
from datetime import datetime
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils import timezone

from .chat import GeminiReelReadChat

logger = logging.getLogger(__name__)


class JSONErrorResponse:
    @staticmethod
    def error(request_id, code, message, data=None):
        return JsonResponse({
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": code,
                "message": message,
                "data": data or {}
            }
        })
    
    @staticmethod
    def invalid_request(request_id, details=None):

        return JSONErrorResponse.error(
            request_id, 
            -32600, 
            "Invalid Request",
            {"details": details}
        )
    
    @staticmethod
    def method_not_found(request_id):
        return JSONErrorResponse.error(
            request_id,
            -32601,
            "Method not found"
        )
    
    @staticmethod
    def internal_error(request_id, details=None):
        """Internal Error (-32603)."""
        return JSONErrorResponse.error(
            request_id,
            -32603,
            "Internal error",
            {"details": details}
        )


@method_decorator(csrf_exempt, name='dispatch')
class ReelReadView(View):
    def __init__(self):
        super().__init__()
        self.gemini_chat = GeminiReelReadChat()
        logger.info("ReelReadView initialized")
    
    def post(self, request):
        try:
            # Parse incoming JSON
            body = json.loads(request.body)
            logger.info(f"📨 Received request: {json.dumps(body, indent=2)}")
            
            # Validate JSON-RPC 2.0 format
            if body.get("jsonrpc") != "2.0":
                logger.warning(" Invalid jsonrpc version")
                return JSONErrorResponse.invalid_request(
                    body.get("id"),
                    "jsonrpc must be '2.0'"
                )
            
            if "id" not in body:
                logger.warning("Missing id field")
                return JSONErrorResponse.invalid_request(
                    None,
                    "id field is required"
                )
            
            request_id = body.get("id")
            method = body.get("method")
            params = body.get("params", {})
    
            if method == "message/send":
                return self.handle_message_send(request_id, params)
            elif method == "execute":
                return self.handle_execute(request_id, params)
            else:
                logger.warning(f"Unknown method: {method}")
                return JSONErrorResponse.method_not_found(request_id)
        
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {str(e)}")
            return JSONErrorResponse.invalid_request(
                None,
                f"Invalid JSON: {str(e)}"
            )
        
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            return JSONErrorResponse.internal_error(
                body.get("id") if 'body' in locals() else None,
                str(e)
            )
    
    def handle_message_send(self, request_id, params):
        try:
            message = params.get("message", {})
            
            context_id = message.get("taskId") or str(uuid.uuid4())
            task_id = message.get("messageId") or str(uuid.uuid4())
            
            user_message = ""
            for part in message.get("parts", []):
                if part.get("kind") == "text":
                    user_message = part.get("text", "").strip()
                    break
            
            logger.info(f" User message: {user_message}")
            
            if not user_message:
                response_text = "Hey there!I'm ReelRead AI, your personal entertainment curator! What kind of movie or book are you in the mood for?"
            
            elif not self.gemini_chat.is_entertainment_related(user_message):
                response_text = "I specialize in movies and books!  What kind of entertainment are you in the mood for? I can help you find your next favorite watch or read!"
            
            else:
                # Get AI response
                response_text = self.gemini_chat.chat(user_message, context_id)
            
            logger.info(f"AI response: {response_text[:100]}...")
            
            # Build and return success response
            return self.build_success_response(
                request_id,
                response_text,
                context_id,
                task_id
            )
        
        except Exception as e:
            logger.error(f" Error in handle_message_send: {str(e)}", exc_info=True)
            return JSONErrorResponse.internal_error(request_id, str(e))
    
    def handle_execute(self, request_id, params):
        try:
            logger.info("⚙️ Execute method called")
            
            return JsonResponse({
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "status": "executed",
                    "message": "ReelRead AI is ready to recommend!"
                }
            })
        
        except Exception as e:
            logger.error(f"Error in handle_execute: {str(e)}")
            return JSONErrorResponse.internal_error(request_id, str(e))
    
    def build_success_response(self, request_id, response_text, context_id, task_id):
        timestamp = datetime.utcnow().isoformat() + "Z"
        
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "id": task_id,
                "contextId": context_id,
                "status": {
                    "state": "completed",
                    "timestamp": timestamp,
                    "message": {
                        "messageId": str(uuid.uuid4()),
                        "role": "agent",
                        "parts": [
                            {
                                "kind": "text",
                                "text": response_text
                            }
                        ],
                        "kind": "message",
                        "taskId": task_id
                    }
                },
                "artifacts": [
                    {
                        "artifactId": str(uuid.uuid4()),
                        "name": "reelread_recommendation",
                        "parts": [
                            {
                                "kind": "text",
                                "text": response_text
                            }
                        ]
                    }
                ],
                "history": [
                    {
                        "messageId": str(uuid.uuid4()),
                        "role": "agent",
                        "parts": [
                            {
                                "kind": "text",
                                "text": response_text
                            }
                        ],
                        "kind": "message",
                        "taskId": task_id
                    }
                ],
                "kind": "task"
            }
        }
        
        logger.info(f"Built success response for request {request_id}")
        return JsonResponse(response)


class HealthCheck(View):
    def get(self, request):
        gemini_chat = GeminiReelReadChat()
        
        return JsonResponse({
            "status": "healthy",
            "service": "ReelRead AI - Movie & Book Recommender",
            "timestamp": timezone.now().isoformat(),
            "gemini_available": gemini_chat.available,
            "version": "1.0.0"
        })