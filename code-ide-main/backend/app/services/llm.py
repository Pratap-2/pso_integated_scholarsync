from dotenv import load_dotenv
import os

load_dotenv()

# We will initialize these lazily
chat_llm = None
analysis_llm = None

def get_llm(agent_type: str):
    global chat_llm, analysis_llm

    if agent_type == "chat":
        if chat_llm is None:
            from langchain_groq import ChatGroq
            chat_llm = ChatGroq(
                model="llama-3.3-70b-versatile",
                temperature=0.7,  # Higher = more creative, less problem-anchored
                groq_api_key=os.getenv("GROQ_API_KEY")
            )
        return chat_llm
    else:
        if analysis_llm is None:
            from langchain_groq import ChatGroq
            analysis_llm = ChatGroq(
                model="llama-3.3-70b-versatile",
                temperature=0.8,
                groq_api_key=os.getenv("GROQ_API_KEY")
            )
        return analysis_llm
