import streamlit as st
import PyPDF2
from langchain.text_splitter import RecursiveCharacterTextSplitter
import os
import random
import time
import subprocess

from langchain_google_genai import GoogleGenerativeAIEmbeddings
import google.generativeai as genai

from langchain_community.vectorstores import FAISS
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain.chains.question_answering import load_qa_chain

from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key = os.getenv("GOOGLE_API_KEY"))

def read_pdf(file_path):
    text = ""
    with open(file_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        for page_num in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_num]
            text += page.extract_text()
        print(text)
        return text
    
def get_text_chunks(text):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=10000, chunk_overlap=1000)
    chunks        = text_splitter.split_text(text)
    print(chunks)
    return chunks

def get_vector_store(text_chunks):
    embeddings   = GoogleGenerativeAIEmbeddings(model = "models/embedding-001")
    vector_store = FAISS.from_texts(text_chunks, embedding = embeddings)
    vector_store.save_local("faiss_index")

def get_conversational_chain():
    prompt_template = """
    Analyze the conversation thoroughly, considering each participant's input, and provide a comprehensive response. If specific details are not available, indicate "Information not found in the context." Avoid guessing or providing inaccurate information. If the required details are not in the meeting context, you may search the internet for factual information.\n\n

    Context:\n {context}?\n
    Question: \n{question}\n

    Detailed Answer:
    """

    model  = ChatGoogleGenerativeAI(model = "gemini-pro", temperature = 0.6)
    prompt = PromptTemplate(template = prompt_template, input_variables = ["context", "question"])
    chain  = load_qa_chain(model, chain_type = "stuff", prompt = prompt)
    return chain

def user_input(user_question):
    embeddings   = GoogleGenerativeAIEmbeddings(model = "models/embedding-001")

    new_db = FAISS.load_local("faiss_index", embeddings)
    docs   = new_db.similarity_search(user_question)

    chain  = get_conversational_chain()

    response = chain(
        {"input_documents":docs, "question": user_question}
        , return_only_outputs=True)
    
    print(response)
    st.write("Reply: ", response["output_text"])

def get_ques(question):
    embeddings   = GoogleGenerativeAIEmbeddings(model = "models/embedding-001")

    new_db = FAISS.load_local("faiss_index", embeddings)
    docs   = new_db.similarity_search(question)

    chain  = get_conversational_chain()

    response = chain(
        {"input_documents":docs, "question": question}
        , return_only_outputs=True)
    
    print(response)
    return response

@st.cache_data
def get_sidebar_text():
    response = get_ques("what are the top 5 questions that can be asked for the meeting")
    return response["output_text"]

def gpt_pop_up():
    subprocess.Popen(["streamlit", "run", "query.py"])

def main():
    st.set_page_config("MEETBOT")
    st.header("MeetBot - A Solution to ask your questions regarding a Meeting🤖")

    user_question = st.text_input("Ask a Question from the Transcript Files")

    if user_question:
        user_input(user_question)

    with st.sidebar:
        st.title("Menu:")
        file_path = "C:/Users/hp/Downloads/Transcipt.pdf"
        if st.button("Submit & Process"):
            with st.spinner("Processing..."):
                raw_text    = read_pdf(file_path)
                text_chunks = get_text_chunks(raw_text)
                get_vector_store(text_chunks)
                sidebar_text = get_sidebar_text()
                st.sidebar.text(sidebar_text)
        sidebar_text = get_sidebar_text()
        st.sidebar.text(sidebar_text)
        if st.button("Ask your questions here"):
            gpt_pop_up()

if __name__ == "__main__":
    main()