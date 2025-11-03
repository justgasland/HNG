import os
import logging

logger = logging.getLogger(__name__)
from decouple import config

class GeminiReelReadChat:
    def __init__(self):
        self.api_key = config('GEMINI_API_KEY')
        self.available = False
        self.conversation_history = {}
        
        if self.api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
                self.available = True
                
            except Exception as e:
                logger.error(f"Gemini initialization failed: {e}")
                self.available = False
        else:
            logger.error("No GEMINI_API_KEY found in environment")
    
    def is_entertainment_related(self, message):
        entertainment_keywords = [
            'movie', 'movies', 'film', 'films', 'cinema', 'watch',
            'book', 'books', 'novel', 'novels', 'read', 'reading',
            'author', 'director', 'actor', 'actress', 'show', 'series',
            'recommend', 'recommendation', 'suggest', 'suggestion',
            'genre', 'thriller', 'romance', 'comedy', 'drama', 'horror',
            'action', 'adventure', 'fantasy', 'sci-fi', 'mystery',
            'fiction', 'non-fiction', 'biography', 'manga', 'anime',
            'documentary', 'tv', 'television', 'streaming', 'netflix',
            'review', 'rating', 'plot', 'story', 'character'
        ]
        
        
        off_topic_keywords = [
            'weather', 'temperature', 'forecast', 'sports', 'game',
            'recipe', 'cooking', 'food', 'restaurant', 'health',
            'medical', 'doctor', 'exercise', 'workout', 'code',
            'programming', 'python', 'javascript', 'math', 'calculate'
        ]
        
        message_lower = message.lower()
        has_entertainment_content = any(keyword in message_lower for keyword in entertainment_keywords)
        is_off_topic = any(keyword in message_lower for keyword in off_topic_keywords)
        return has_entertainment_content or not is_off_topic
    
    def get_conversation_history(self, session_id):
        if session_id not in self.conversation_history:
            self.conversation_history[session_id] = [
                {
                    "role": "user",
                    "parts": [{
                        "text": "You are ReelRead AI, a friendly and knowledgeable movie and book recommendation assistant."
                    }]
                },
                {
                    "role": "model",
                    "parts": [{
                        "text": "Hey! I'm ReelRead AI, your personal entertainment curator! Whether you're looking for your next binge-worthy movie, a gripping book, or just some entertainment suggestions, I'm here to help. What are you in the mood for today?"
                    }]
                }
            ]
        
        return self.conversation_history[session_id]
    
    def chat(self, user_message, session_id):
        if not self.available:
            return "Sorry, I'm having trouble connecting to the server right now. Please try again later!"
        
        try:
            history = self.get_conversation_history(session_id)
            history.append({
                "role": "user",
                "parts": [{"text": user_message}]
            })
            chat = self.model.start_chat(history=history[:-1])
            
            response = chat.send_message(user_message)
            response_text = response.text
            
            history.append({
                "role": "model",
                "parts": [{"text": response_text}]
            })
            
            logger.info(f"Generated recommmendations")
            return response_text
            
        except Exception as e:
            logger.error(f" Error in chat: {str(e)}")
            return "Oops! Something went wrong. Try again"
    
    def clear_history(self, session_id):
        if session_id in self.conversation_history:
            del self.conversation_history[session_id]
            logger.info(f"History cleared")