# -*- coding: utf-8 -*-
"""
chatbot_manager.py
My Garden Care - Smart Garden Assistant Chatbot Manager

A conversational AI to help users with garden management, IoT monitoring, and gamification features.
Features: NLTK pattern matching + Gemini AI fallback + Context awareness
"""

import os
import re
import nltk
from nltk.chat.util import Chat
from datetime import datetime
from typing import Optional, List, Tuple

# Gemini integration - match pattern from data_manager.py
GEMINI_AVAILABLE = False
try:
    import google.generativeai as genai
    from dotenv import load_dotenv
    load_dotenv()
    
    api_key = os.getenv("GOOGLE_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if api_key:
        genai.configure(api_key=api_key)
        GEMINI_AVAILABLE = True
        print("[Chatbot] Gemini AI configured successfully")
    else:
        print("[Chatbot] Warning: GOOGLE_API_KEY not found - Gemini fallback disabled")
except ImportError as e:
    print(f"[Chatbot] google.generativeai not installed: {e}")

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)

# ===========================================
# CONVERSATION PATTERNS
# ===========================================

PATTERNS = [
    # === GREETINGS & INTRODUCTIONS ===
    (r'hi|hello|hey|greetings|good morning|good afternoon|good evening', [
        "Hello, green thumb! 🌱 Welcome to My Garden Care. How can I help your garden thrive today?",
        "Hi there! 🌿 I'm your smart garden assistant. What do you need help with?",
        "Hey! Ready to make your garden flourish? Ask me anything about plant care, sensors, or your missions!"
    ]),
    
    # === ABOUT THE PLATFORM ===
    (r'what is this|about|tell me about|what does this do|purpose', [
        "My Garden Care is your smart gardening companion! We combine:\n🌡️ Real-time IoT sensors (soil moisture, temperature, humidity)\n🤖 AI-powered advice from Google Gemini\n🎮 Gamification with daily missions and leaderboards\n\nWhat would you like to explore first?",
    ]),
    
    (r'features|capabilities|what can you do|functionality', [
        "I can help you with:\n🌱 Plant care advice and tips\n📊 Understanding your sensor readings\n🎯 Daily missions and gamification\n🏖️ Vacation mode planning\n💧 Watering schedules\n🐛 Pest and disease identification\n\nWhat would you like to know more about?"
    ]),
    
    # === IOT SENSORS & MONITORING ===
    (r'sensor|sensors|monitoring|iot|readings|data', [
        "Our IoT sensors monitor three key metrics:\n• Soil moisture - keeps your plants hydrated\n• Temperature - ensures optimal growing conditions\n• Humidity - prevents mold and maintains plant health\n\nWant to know more about a specific sensor?",
    ]),
    
    (r'soil moisture|soil sensor|wet|dry', [
        "🌊 Soil moisture is crucial! Optimal levels vary:\n• Vegetables: 60-80%\n• Succulents: 20-40%\n• Most plants: 40-60%\n\nIf your soil is too dry, water deeply. Too wet? Improve drainage and reduce watering frequency.",
    ]),
    
    (r'temperature|temp|hot|cold|weather', [
        "🌡️ Temperature affects growth rates:\n• Too hot (>35°C): Stress, wilting\n• Too cold (<10°C): Slowed growth\n• Ideal: 18-24°C for most plants\n\nCheck your temperature readings to adjust plant placement or provide shade/protection.",
    ]),
    
    (r'humidity|humid|moisture in air', [
        "💨 Humidity impacts plant health:\n• High humidity (>70%): Risk of fungal diseases\n• Low humidity (<30%): Leaf browning, stress\n• Sweet spot: 40-60%\n\nMist plants or use a humidifier if too dry. Improve ventilation if too humid!",
    ]),
    
    # === GAMIFICATION ===
    (r'missions|daily mission|tasks|challenges|quest', [
        "🎯 Complete daily missions to level up!\n\nMissions include:\n✓ Check sensor readings\n✓ Water plants\n✓ Log growth progress\n✓ Add new plants\n\nEach completed mission earns you points. Check the Garden Race tab!",
    ]),
    
    (r'rank|ranks|level|levels|xp|points|score', [
        "🏆 My Garden Care Ranks:\n1. Fresh Sprout (0-200 XP)\n2. Diligent Gardener (201-500 XP)\n3. Growth Expert (501-1000 XP)\n4. Garden Master (1001+ XP)\n\nKeep completing missions to advance!",
    ]),
    
    (r'leaderboard|competition|compete|ranking|weekly', [
        "📊 The weekly leaderboard shows top gardeners!\n\nRankings are based on missions completed. Compete with friends and see who's the ultimate gardener! Resets weekly.",
    ]),
    
    # === PLANT CARE ADVICE ===
    (r'water|watering|how much water|how often', [
        "💧 Watering tips:\n• Check soil moisture first (use your sensor!)\n• Water deeply but less frequently\n• Morning watering is best\n• Avoid wet leaves to prevent disease\n\nMost plants need water when top 2-3cm of soil is dry.",
    ]),
    
    (r'fertilize|fertilizer|nutrients|feeding|feed', [
        "🌿 Fertilizing guidelines:\n• Growing season: Every 2-4 weeks\n• Dormant season: Monthly or less\n• Use balanced fertilizer (10-10-10)\n• Don't over-fertilize - causes burn\n\nOrganic options: compost, worm castings, fish emulsion.",
    ]),
    
    (r'sunlight|sun|shade|light|lighting', [
        "☀️ Light requirements vary:\n• Full sun: 6+ hours direct light\n• Partial shade: 3-6 hours\n• Shade: <3 hours\n\nObserve your space and match plants to light conditions!",
    ]),
    
    (r'pest|pests|bugs|insects|disease', [
        "🐛 Common garden issues:\n• Aphids: Spray with soapy water\n• Fungal spots: Improve air circulation\n• Yellowing leaves: Check water/nutrients\n• Wilting: Soil moisture too high or low\n\nUse our AI to identify specific problems!",
    ]),
    
    # === VACATION ===
    (r'vacation|away|travel|leave|trip', [
        "🏖️ Vacation Mode helps your garden survive while you're away!\n\nThe AI predicts survival chances based on current sensor readings, plant needs, and trip duration. Set up vacation mode from the Home page!",
    ]),
    
    # === TROUBLESHOOTING ===
    (r'dying|dead|wilting|brown|yellow|help|problem|wrong', [
        "😟 Let's diagnose the issue:\n\n1. Check soil moisture (too wet/dry?)\n2. Examine leaves (spots, pests?)\n3. Review light exposure\n4. Consider recent changes\n\nDescribe the problem and I can help more!",
    ]),
    
    # === THANKS & GOODBYE ===
    (r'thank|thanks|appreciate', [
        "You're very welcome! 🌱 Happy gardening!",
        "My pleasure! Keep growing and completing those missions! 🌿",
    ]),
    
    (r'bye|goodbye|see you|exit|quit', [
        "Happy gardening! Don't forget to check your sensors today! 🌱",
        "Goodbye! Come back anytime for garden advice. Keep growing! 🌿",
    ]),
]

# Custom reflections for natural conversation
REFLECTIONS = {
    "i am": "you are",
    "i was": "you were",
    "i": "you",
    "i'm": "you are",
    "my": "your",
    "you are": "I am",
    "your": "my",
    "you": "me",
    "me": "you"
}


# ===========================================
# CHATBOT CLASS
# ===========================================

class GardenCareChatbot:
    """
    Smart Garden Assistant with NLTK patterns + Gemini AI fallback.
    """
    
    # Gemini models to try (in order)
    GEMINI_MODELS = [
        'gemini-2.5-flash',
        'gemini-2.0-flash',
        'gemini-1.5-flash',
        'gemini-pro',
    ]
    
    def __init__(self, username: Optional[str] = None):
        """
        Initialize chatbot with optional user context.
        
        Args:
            username: Optional username for personalized responses
        """
        self.chat = Chat(PATTERNS, REFLECTIONS)
        self.conversation_history: List[Tuple[str, str]] = []
        self.session_start = datetime.now()
        self.username = username
        self.use_gemini = GEMINI_AVAILABLE
        
        # User context (populated on demand)
        self._user_context = None
    
    def _load_user_context(self) -> dict:
        """Load user's plants and sensor data for context-aware responses."""
        if not self.username:
            return {}
        
        try:
            from plants_manager import list_plants, count_plants
            from data_manager import get_latest_reading
            from auth_service import get_user_details
            import gamification_rules
            
            # Get user details
            user_data = get_user_details(self.username) or {}
            score = user_data.get('score', 0)
            rank = gamification_rules.get_user_rank(score)
            
            # Get plants
            plants = list_plants(self.username) or []
            plant_count = len(plants)
            
            # Get latest sensor readings for each plant
            plant_info = []
            for p in plants[:5]:  # Limit to 5 for context size
                pid = p.get('plant_id') or p.get('id')
                name = p.get('name') or p.get('species') or 'Unknown'
                reading = get_latest_reading(pid) if pid else None
                plant_info.append({
                    'name': name,
                    'species': p.get('species', ''),
                    'soil': reading.get('soil') if reading else None,
                    'temp': reading.get('temp') if reading else None,
                    'humidity': reading.get('humidity') if reading else None,
                })
            
            return {
                'username': self.username,
                'score': score,
                'rank': rank,
                'plant_count': plant_count,
                'plants': plant_info,
            }
        except Exception as e:
            print(f"[Chatbot] Context load error: {e}")
            return {}
    
    def _build_context_string(self) -> str:
        """Build a context string for Gemini prompts."""
        if self._user_context is None:
            self._user_context = self._load_user_context()
        
        ctx = self._user_context
        if not ctx:
            return ""
        
        lines = [f"User: {ctx.get('username', 'Guest')}"]
        lines.append(f"Rank: {ctx.get('rank', 'Fresh Sprout')} ({ctx.get('score', 0)} XP)")
        lines.append(f"Plants: {ctx.get('plant_count', 0)} registered")
        
        for p in ctx.get('plants', []):
            status = []
            if p.get('soil') is not None:
                status.append(f"Soil: {p['soil']}%")
            if p.get('temp') is not None:
                status.append(f"Temp: {p['temp']}°C")
            if p.get('humidity') is not None:
                status.append(f"Humidity: {p['humidity']}%")
            status_str = ", ".join(status) if status else "No recent readings"
            lines.append(f"  - {p['name']} ({p.get('species', '')}): {status_str}")
        
        return "\n".join(lines)
    
    def _is_fallback_response(self, response: str) -> bool:
        """Check if the NLTK response is a generic fallback."""
        fallback_phrases = [
            "I'm not sure I understand",
            "Hmm, I'm still learning",
            "Could you be more specific",
            "I want to help but need more details",
        ]
        return any(phrase in response for phrase in fallback_phrases)
    
    def _query_gemini(self, user_input: str) -> Optional[str]:
        """Query Gemini AI for complex questions."""
        if not self.use_gemini:
            return None
        
        context = self._build_context_string()
        
        prompt = f"""You are a helpful garden assistant for the "My Garden Care" smart garden app.
You help users with plant care, IoT sensors (soil moisture, temperature, humidity), gamification, and vacation mode.

User Context:
{context if context else "No user data available"}

User Question: {user_input}

Instructions:
- Be helpful, friendly, and concise (max 3-4 sentences)
- If the question is about the user's specific plants or sensors, reference their actual data
- Use emojis sparingly for friendliness
- If you don't know something, say so honestly
"""
        
        for model_name in self.GEMINI_MODELS:
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt)
                if response and response.text:
                    return response.text.strip()
            except Exception as e:
                print(f"[Chatbot] Gemini {model_name} failed: {e}")
                continue
        
        return None
    
    def get_response(self, user_input: str) -> str:
        """
        Get chatbot response with hybrid NLTK + Gemini approach.
        
        Args:
            user_input: User's message
            
        Returns:
            Chatbot's response string
        """
        if not user_input or not user_input.strip():
            return "Please type a message so I can help you! 🌱"
        
        user_input = user_input.strip()
        
        # First try NLTK pattern matching
        response = self.chat.respond(user_input)
        
        # Check if response is None or a fallback response
        if response is None or self._is_fallback_response(response):
            # Try Gemini for complex questions
            gemini_response = self._query_gemini(user_input)
            if gemini_response:
                response = gemini_response
            elif response is None:
                response = "I'm not sure how to help with that. Try asking about sensors, plant care, or missions! 🌱"
        
        # Track conversation
        self.conversation_history.append((user_input, response))
        
        return response
    
    def get_quick_response(self, quick_type: str) -> str:
        """Get response for quick reply buttons with context."""
        # Refresh context for quick replies
        self._user_context = self._load_user_context()
        ctx = self._user_context or {}
        
        if quick_type == "sensors":
            # Context-aware sensor response
            plants = ctx.get('plants', [])
            if not plants:
                return "🌡️ You don't have any plants registered yet! Add a plant first to see sensor data."
            
            lines = ["🌡️ **Your Current Sensor Readings:**\n"]
            for p in plants:
                name = p.get('name', 'Plant')
                soil = p.get('soil')
                temp = p.get('temp')
                hum = p.get('humidity')
                
                if soil is None and temp is None and hum is None:
                    lines.append(f"• **{name}**: No recent sensor data")
                else:
                    parts = []
                    if soil is not None:
                        status = "✅" if 30 <= soil <= 70 else "⚠️"
                        parts.append(f"Soil: {soil}% {status}")
                    if temp is not None:
                        status = "✅" if 15 <= temp <= 30 else "⚠️"
                        parts.append(f"Temp: {temp}°C {status}")
                    if hum is not None:
                        parts.append(f"Humidity: {hum}%")
                    lines.append(f"• **{name}**: {', '.join(parts)}")
            
            return "\n".join(lines)
        
        elif quick_type == "watering":
            plants = ctx.get('plants', [])
            if not plants:
                return "💧 Add some plants first, then I can give you personalized watering tips based on your sensor data!"
            
            lines = ["💧 **Watering Status:**\n"]
            for p in plants:
                name = p.get('name', 'Plant')
                soil = p.get('soil')
                
                if soil is None:
                    lines.append(f"• **{name}**: No soil data - check sensors")
                elif soil < 30:
                    lines.append(f"• **{name}**: 🔴 Dry ({soil}%) - Water needed!")
                elif soil > 70:
                    lines.append(f"• **{name}**: 🔵 Very wet ({soil}%) - Hold off on watering")
                else:
                    lines.append(f"• **{name}**: 🟢 Good ({soil}%) - No action needed")
            
            lines.append("\n*Tip: Water deeply in the morning for best results!*")
            return "\n".join(lines)
        
        elif quick_type == "missions":
            score = ctx.get('score', 0)
            rank = ctx.get('rank', 'Fresh Sprout')
            plant_count = ctx.get('plant_count', 0)
            
            lines = [
                f"🎯 **Your Garden Status:**\n",
                f"🏆 Rank: **{rank}**",
                f"⭐ Score: **{score} XP**",
                f"🌱 Plants: **{plant_count}**",
                f"\n**Ways to earn points:**",
                f"• 💧 Water a plant: +10 XP",
                f"• 🌿 Fertilize: +10 XP",
                f"• 🔍 Use Search: +5 XP",
                f"• ➕ Add new plant: +25 XP",
            ]
            return "\n".join(lines)
        
        return "How can I help you? 🌱"
    
    def get_welcome_message(self) -> str:
        """Returns the welcome message for the chat interface."""
        name_part = f", {self.username}" if self.username else ""
        return (
            f"Hello{name_part}! 🌿 Welcome to My Garden Care Assistant.\n\n"
            "I can help you with:\n"
            "• 📊 IoT sensor readings and monitoring\n"
            "• 🌱 Plant care advice and troubleshooting\n"
            "• 🎯 Daily missions and gamification\n"
            "• 🤖 AI-powered recommendations\n\n"
            "Use the quick buttons below or type your question!"
        )
    
    def get_history(self) -> List[Tuple[str, str]]:
        """Return conversation history as list of (user, bot) tuples."""
        return self.conversation_history
    
    def clear_history(self):
        """Clear conversation history and reset session."""
        self.conversation_history = []
        self.session_start = datetime.now()
        self._user_context = None


# ===========================================
# MODULE-LEVEL FUNCTIONS (Singleton pattern)
# ===========================================

_chatbot_instances: dict = {}


def get_chatbot(username: Optional[str] = None) -> GardenCareChatbot:
    """Get or create a chatbot instance for the user."""
    key = username or "_anonymous_"
    if key not in _chatbot_instances:
        _chatbot_instances[key] = GardenCareChatbot(username=username)
    return _chatbot_instances[key]


def get_chat_response(username: Optional[str], user_message: str) -> str:
    """Quick function to get a chatbot response."""
    chatbot = get_chatbot(username)
    return chatbot.get_response(user_message)


def get_quick_reply_response(username: Optional[str], quick_type: str) -> str:
    """Get response for quick reply buttons."""
    chatbot = get_chatbot(username)
    return chatbot.get_quick_response(quick_type)


def clear_chat_session(username: Optional[str] = None):
    """Clear a user's chat session."""
    key = username or "_anonymous_"
    if key in _chatbot_instances:
        _chatbot_instances[key].clear_history()
