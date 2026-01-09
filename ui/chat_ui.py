# -*- coding: utf-8 -*-
"""
chat_ui.py
My Garden Care - Chatbot UI Screen
"""

import gradio as gr
from chatbot_manager import get_chatbot, get_chat_response, get_quick_reply_response, clear_chat_session


def _get_username(user_state) -> str:
    """Extract username from user state."""
    return user_state.strip() if isinstance(user_state, str) else ""


def chat_screen(user_state: gr.State):
    """
    Creates the Chatbot UI screen with quick reply buttons.
    """
    
    gr.Markdown("## 💬 Garden Assistant")
    gr.Markdown("Chat with your AI garden companion for tips, sensor help, and more!")
    
    # Chatbot display
    chatbot = gr.Chatbot(
        label="",
        height=380,
        show_label=False,
    )
    
    # Quick Reply Buttons
    gr.Markdown("### ⚡ Quick Actions")
    with gr.Row():
        btn_sensors = gr.Button("🌡️ Sensor Status", variant="secondary", scale=1)
        btn_watering = gr.Button("💧 Watering Tips", variant="secondary", scale=1)
        btn_missions = gr.Button("🎯 My Missions", variant="secondary", scale=1)
    
    # Input area
    with gr.Row():
        msg_input = gr.Textbox(
            label="",
            placeholder="Ask me anything about plant care, sensors, or gardening...",
            show_label=False,
            scale=9,
            container=False,
        )
        send_btn = gr.Button("Send", variant="primary", scale=1, min_width=80)
    
    with gr.Row():
        clear_btn = gr.Button("🗑️ Clear Chat", variant="secondary", scale=1)
    
    # =========================================
    # EVENT HANDLERS
    # =========================================
    
    def respond(u, message, chat_history):
        """Process user message and get bot response."""
        username = _get_username(u)
        
        if not message or not message.strip():
            return "", chat_history
        
        # Get response from chatbot manager (with Gemini fallback)
        response = get_chat_response(username if username else None, message)
        
        # Build history using gr.ChatMessage
        if chat_history is None:
            chat_history = []
        
        chat_history.append(gr.ChatMessage(role="user", content=message))
        chat_history.append(gr.ChatMessage(role="assistant", content=response))
        
        return "", chat_history
    
    def handle_quick_reply(u, chat_history, quick_type: str):
        """Handle quick reply button clicks."""
        username = _get_username(u)
        
        # Get context-aware response
        response = get_quick_reply_response(username if username else None, quick_type)
        
        if chat_history is None:
            chat_history = []
        
        # Add the quick action as a user message for context
        quick_labels = {
            "sensors": "🌡️ Show my sensor readings",
            "watering": "💧 Give me watering tips",
            "missions": "🎯 Show my missions status",
        }
        user_msg = quick_labels.get(quick_type, "Quick action")
        
        chat_history.append(gr.ChatMessage(role="user", content=user_msg))
        chat_history.append(gr.ChatMessage(role="assistant", content=response))
        
        return chat_history
    
    def clear_chat(u):
        """Clear chat history."""
        username = _get_username(u)
        clear_chat_session(username if username else None)
        
        chatbot_instance = get_chatbot(username if username else None)
        welcome = chatbot_instance.get_welcome_message()
        
        return [gr.ChatMessage(role="assistant", content=welcome)], ""
    
    def init_chat(u):
        """Initialize chat when tab is opened."""
        username = _get_username(u)
        chatbot_instance = get_chatbot(username if username else None)
        
        history = chatbot_instance.get_history()
        
        if not history:
            welcome = chatbot_instance.get_welcome_message()
            return [gr.ChatMessage(role="assistant", content=welcome)]
        
        messages = []
        for user_msg, bot_msg in history:
            messages.append(gr.ChatMessage(role="user", content=user_msg))
            messages.append(gr.ChatMessage(role="assistant", content=bot_msg))
        return messages
    
    # =========================================
    # WIRE EVENTS
    # =========================================
    
    # Send message on button click
    send_btn.click(
        fn=respond,
        inputs=[user_state, msg_input, chatbot],
        outputs=[msg_input, chatbot],
    )
    
    # Send message on Enter key
    msg_input.submit(
        fn=respond,
        inputs=[user_state, msg_input, chatbot],
        outputs=[msg_input, chatbot],
    )
    
    # Quick reply buttons
    btn_sensors.click(
        fn=lambda u, h: handle_quick_reply(u, h, "sensors"),
        inputs=[user_state, chatbot],
        outputs=[chatbot],
    )
    
    btn_watering.click(
        fn=lambda u, h: handle_quick_reply(u, h, "watering"),
        inputs=[user_state, chatbot],
        outputs=[chatbot],
    )
    
    btn_missions.click(
        fn=lambda u, h: handle_quick_reply(u, h, "missions"),
        inputs=[user_state, chatbot],
        outputs=[chatbot],
    )
    
    # Clear chat
    clear_btn.click(
        fn=clear_chat,
        inputs=[user_state],
        outputs=[chatbot, msg_input],
    )
    
    # Return components for auto-load on navigation
    return clear_btn, init_chat, [user_state], [chatbot]
