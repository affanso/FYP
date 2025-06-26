import os
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain
from langchain_core.messages import AIMessage,HumanMessage
from langchain_core.prompts import MessagesPlaceholder
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from transformers import AutoTokenizer, AutoModelForSequenceClassification
load_dotenv()

## Langsmith Tracking
os.environ["LANGCHAIN_API_KEY"]=os.getenv("LANGCHAIN_API_KEY")
os.environ["LANGSMITH_TRACING"]=os.getenv("LANGSMITH_TRACING")
os.environ["LANGSMITH_ENDPOINT"]=os.getenv("LANGSMITH_ENDPOINT")
os.environ["LANGSMITH_PROJECT"]=os.getenv("LANGSMITH_PROJECT")

os.environ["HF_TOKEN"]=os.getenv("HF_TOKEN")




# Create expanded emotion mapping
emotion_mapping = {
    'joy': 0,
    'sadness': 1,
    'anger': 2,
    'fear': 3,
    'anxiety': 4,  # Will be created from fear + specific patterns
    'stress': 5,   # Will be created from anger + specific patterns
    'surprise': 6,
    'love': 7
}

emotion_names = list(emotion_mapping.keys())

# Load saved model
model = AutoModelForSequenceClassification.from_pretrained("./emotion-detection")
tokenizer = AutoTokenizer.from_pretrained("./emotion-detection")

# Use for prediction
def predict(text):
    # inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True)
    # outputs = model(**inputs)
    # prediction = torch.argmax(outputs.logits, dim=-1)
    # return emotion_names[prediction.item()]
    llm = ChatGroq(model="Gemma2-9b-It")
    prompt = (
        "You are an emotion detector. Detect the emotion of the inptut and answer in one word.\n\n"
        f"{text}"
    )
    result = llm.invoke(prompt)
    return result.content



class BOT:
    def __init__(self):
        ##LLM
        ##self.llm = ChatGroq(model="mistral-saba-24b")
        self.llm = ChatGroq(model="Gemma2-9b-It")

        self.system_prompt = (
            "You are a compassionate and supportive AI mental health assistant. "
            "Always respond in a calm, non-judgmental, and empathetic tone. "
            "Keep your replies brief—no more than four sentences—and easy to understand. "
            "The user input includes a detected emotion, which may not be fully accurate, so interpret it thoughtfully and gently. "
            "Use the retrieved context below and consider the full chat history when formulating your response.\n\n"
            "{context}"
        )

        self.prompt = ChatPromptTemplate.from_messages(
            [
                ("system", self.system_prompt),
                MessagesPlaceholder("chat_history"),
                ("user", "{input}")
            ]
        )
        
        self.embedding_model = HuggingFaceEmbeddings(model="all-MiniLM-L6-v2")
        self.vectordb = Chroma(persist_directory="chroma_db",embedding_function=self.embedding_model)
        self.retriever = self.vectordb.as_retriever()
        
        self.question_answer_chain=create_stuff_documents_chain(self.llm,self.prompt)
        self.rag_chain=create_retrieval_chain(self.retriever,self.question_answer_chain)

        self.conversational_rag_chain = RunnableWithMessageHistory(
            self.rag_chain,
            self.get_session_history,
            input_messages_key="input",
            history_messages_key="chat_history",
            output_messages_key="answer",
        )
        self.store = {}
    
    
    def get_session_history(self,session_id: str) -> BaseChatMessageHistory:
        if session_id not in self.store:
            self.store[session_id] = ChatMessageHistory()
        return self.store[session_id]
    
    def add_configuration(self, session_id):
        self.config = {
            "configurable": {"session_id": str(session_id)}
        }

    def chat(self,user_message):

        emotion = predict(user_message)

        format = f"The user input is: \"{user_message}\" and the detected emotion is: \"{emotion}\" (maybe)."

        response = self.conversational_rag_chain.invoke({"input":format,},config=self.config)

        answer = response['answer']
        return emotion, answer
    
    
    def analyze_session(self, messages):
        conversation_text = "\n".join(
            f"{'User' if isinstance(m, HumanMessage) else 'AI'}: {m.content}" for m in messages
        )
        # Use the LLM to generate analysis based on the full session
        analysis_prompt = (
            "You are an empathetic AI therapist. Analyze the following chat history to provide insights about the user's emotional state."
            "give a short analysis in 3-4 sentences.\n\n"
            f"{conversation_text}\n\n"
            "Session Analysis:"
        )
        
        result = self.llm.invoke(analysis_prompt)
        
        return result.content

