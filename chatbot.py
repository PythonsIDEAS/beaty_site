from g4f.client import Client
from flask import session

client = Client()

def get_ai_response(message):
    try:
        # Initialize chat history if it doesn't exist
        if 'chat_history' not in session:
            session['chat_history'] = []
        
        # Add user message to history
        session['chat_history'].append({"role": "user", "content": message})
        
        # Create messages array with history
        messages = session['chat_history']
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            web_search=False
        )
        
        # Add assistant response to history
        assistant_message = {"role": "assistant", "content": response.choices[0].message.content}
        session['chat_history'].append(assistant_message)
        
        # Keep only last 10 messages to manage context window
        if len(session['chat_history']) > 10:
            session['chat_history'] = session['chat_history'][-10:]
        
        return {
            'status': 'success',
            'response': response.choices[0].message.content
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }