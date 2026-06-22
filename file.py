import os
import json
import streamlit as st
from dotenv import load_dotenv
from typing import List, Dict, Any

# Detect if running in Pyodide (browser environment)
try:
    import js
    from js import XMLHttpRequest
    IS_PYODIDE = True
except ImportError:
    IS_PYODIDE = False

# Import Groq only if not in Pyodide to avoid ModuleNotFoundError: No module named 'ssl'
if not IS_PYODIDE:
    from groq import Groq

# Load environment variables
load_dotenv()

# Set page config
st.set_page_config(
    page_title="Coding Assistant",
    page_icon="💻",
    layout="wide"
)

# Call Groq API via synchronous XMLHttpRequest in Pyodide
def call_groq_pyodide(api_key: str, messages: list) -> str:
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 1024,
        "stream": False
    }
    
    xhr = XMLHttpRequest.new()
    xhr.open("POST", "https://api.groq.com/openai/v1/chat/completions", False)  # False = synchronous
    xhr.setRequestHeader("Authorization", f"Bearer {api_key}")
    xhr.setRequestHeader("Content-Type", "application/json")
    xhr.send(json.dumps(payload))
    
    if xhr.status == 200:
        response_data = json.loads(xhr.responseText)
        return response_data["choices"][0]["message"]["content"]
    else:
        raise Exception(f"HTTP Error {xhr.status}: {xhr.responseText or xhr.statusText}")

# Initialize Groq client or get API key
def setup_groq():
    api_key = os.getenv("GROQ_API_KEY")
    
    # Check URL query parameters (e.g. ?key=gsk_...)
    if not api_key and "key" in st.query_params:
        api_key = st.query_params["key"]
    
    # If not in env, check sidebar input
    if not api_key and "groq_api_key" in st.session_state:
        api_key = st.session_state.groq_api_key

    if not api_key:
        st.sidebar.warning("Groq API key not found.")
        api_key_input = st.sidebar.text_input("Enter your Groq API Key:", type="password", key="groq_api_key_input")
        if api_key_input:
            st.session_state.groq_api_key = api_key_input
            st.rerun()
        return None

    if IS_PYODIDE:
        return api_key

    try:
        import httpx
        client = Groq(
            api_key=api_key,
            http_client=httpx.Client(
                timeout=30.0,
                follow_redirects=True,
                verify=True
            )
        )
        return client
    except Exception as e:
        st.error(f"Failed to initialize Groq client: {str(e)}")
        return None

groq_client_instance = setup_groq()

# Initialize session state for chat history
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "👋 Hello! I'm your coding assistant. What programming challenge can I help you solve today?"
        }
    ]

# Sidebar with instructions and settings
with st.sidebar:
    st.title("💻 Coding Assistant")
    st.markdown("""
    ### How to use:
    1. Type your coding question in the chat box below
    2. Press Enter or click Send
    3. I can help you with:
       - Debugging code
       - Writing scripts
       - Understanding programming concepts
       - Exploring frameworks and libraries
    """)
    
    if st.button("🔄 Clear Chat"):
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "👋 Hello! I'm your coding assistant. What programming challenge can I help you solve today?"
            }
        ]
        st.rerun()

# Main chat interface
def main():
    st.title("💬 Coding Assistant")
    
    groq_client = groq_client_instance
    
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    if prompt := st.chat_input("Type your coding question here..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            
            if not groq_client:
                full_response = "Error: Could not connect to the AI service. Please check your API key."
            else:
                try:
                    if IS_PYODIDE:
                        # Direct HTTP call since SDK imports are not supported in Pyodide/browser
                        api_messages = [
                            {
                                "role": "system",
                                "content": """You are a knowledgeable and friendly coding assistant. 
                                Help users with programming questions, debugging, code generation, and 
                                explanations of technical concepts. Be clear, concise, and supportive.
                                """
                            },
                            *[{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
                        ]
                        with st.spinner("Thinking..."):
                            full_response = call_groq_pyodide(groq_client, api_messages)
                        message_placeholder.markdown(full_response)
                    else:
                        response = groq_client.chat.completions.create(
                            model="llama-3.3-70b-versatile",
                            messages=[
                                {
                                    "role": "system",
                                    "content": """You are a knowledgeable and friendly coding assistant. 
                                    Help users with programming questions, debugging, code generation, and 
                                    explanations of technical concepts. Be clear, concise, and supportive.
                                    """
                                },
                                *[{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
                            ],
                            temperature=0.7,
                            max_tokens=1024,
                            stream=True
                        )
                        
                        for chunk in response:
                            if chunk.choices[0].delta.content is not None:
                                content = chunk.choices[0].delta.content
                                full_response += content
                                message_placeholder.markdown(full_response + "▌")
                        
                        message_placeholder.markdown(full_response)
                    
                except Exception as e:
                    full_response = f"⚠️ Sorry, I encountered an error: {str(e)}"
                    message_placeholder.error(full_response)
        
        st.session_state.messages.append({"role": "assistant", "content": full_response})
        st.rerun()

# Custom CSS
st.markdown("""
    <style>
        .stChatFloatingInputContainer {
            bottom: 20px;
        }
        .stChatMessage {
            padding: 1rem;
            border-radius: 0.8rem;
            margin-bottom: 1rem;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        }
        .stChatMessage p {
            margin: 0;
            line-height: 1.6;
        }
        .stButton>button {
            width: 100%;
            margin-top: 0.5rem;
            background-color: #2196F3;
            color: white;
            border: none;
            border-radius: 0.5rem;
            padding: 0.5rem 1rem;
            font-weight: 500;
        }
        .stButton>button:hover {
            background-color: #1976D2;
        }
    </style>
""", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
