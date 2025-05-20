import os
import json
import smtplib
import streamlit as st
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from dotenv import load_dotenv
from pypdf import PdfReader
from openai import OpenAI
import requests

load_dotenv()

# --- Email & Push Functions ---
def send_email_with_cv(to_email, chat_history):
    sender = os.getenv("SMTP_SENDER_EMAIL")
    password = os.getenv("SMTP_PASSWORD")
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT", 587))

    msg = MIMEMultipart()
    msg["Subject"] = "Chat with Raabiyah’s Assistant + CV"
    msg["From"] = sender
    msg["To"] = to_email

    body = "\n\n".join([f"User: {q}\nRaabiyah: {a}" for q, a in chat_history])
    msg.attach(MIMEText(f"Thanks for your interest in Raabiyah!\n\nHere’s a transcript of our chat:\n\n{body}", "plain"))

    with open("me/Raabiyah_CV.pdf", "rb") as f:
        part = MIMEApplication(f.read(), Name="Raabiyah_CV.pdf")
        part['Content-Disposition'] = 'attachment; filename="Raabiyah_CV.pdf"'
        msg.attach(part)

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(sender, password)
        server.send_message(msg)

def log_chat_to_file(email, history):
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    file_path = f"logs/chat_{ts}_{email.replace('@','_at_')}.json"
    with open(file_path, "w") as f:
        json.dump({"email": email, "chat": history}, f, indent=2)

def log_to_pushover(message):
    requests.post(
        "https://api.pushover.net/1/messages.json",
        data={
            "token": os.getenv("PUSHOVER_TOKEN"),
            "user": os.getenv("PUSHOVER_USER"),
            "message": message,
        }
    )

# --- Chatbot Class ---
class RaabiyahChatbot:

    def __init__(self):
        self.openai = OpenAI()
        self.name = "Raabiyah Adam"
        self.history_pairs = []

        reader = PdfReader("me/linkedin.pdf")
        self.linkedin = ""
        for page in reader.pages:
            text = page.extract_text()
            if text:
                self.linkedin += text.strip() + "\n"

        with open("me/summary.txt", "r", encoding="utf-8") as f:
            self.summary = f.read().strip()

    def system_prompt(self):
        return f"""
You are acting as {self.name}'s assistant on her personal site.
Your job is to answer questions about her background, experience, skills, and projects.
Be warm, insightful, and guide interested visitors to share their name and email for follow-up.

## Summary:
{self.summary}

## LinkedIn Profile:
{self.linkedin}
"""

    def respond(self, user_input):
        messages = [{"role": "system", "content": self.system_prompt()}]
        for q, a in self.history_pairs:
            messages.append({"role": "user", "content": q})
            messages.append({"role": "assistant", "content": a})
        messages.append({"role": "user", "content": user_input})

        response = self.openai.chat.completions.create(
            model="gpt-4o-mini", messages=messages
        )
        reply = response.choices[0].message.content
        self.history_pairs.append((user_input, reply))
        return reply

# --- Streamlit App ---
st.set_page_config(page_title="Raabiyah's Career Assistant", layout="centered")
st.title("🌟 Welcome to Raabiyah’s Site")
st.markdown("___")

st.subheader("Talk to Raabiyah’s Assistant")
if "chatbot" not in st.session_state:
    st.session_state.chatbot = RaabiyahChatbot()

user_input = st.text_input("Ask a question about Raabiyah...", key="input")
if user_input:
    reply = st.session_state.chatbot.respond(user_input)
    st.write(f"**Raabiyah's Assistant:** {reply}")

if len(st.session_state.chatbot.history_pairs) > 0:
    st.write("### Chat History:")
    for q, a in st.session_state.chatbot.history_pairs:
        st.write(f"**You:** {q}")
        st.write(f"**Raabiyah's Assistant:** {a}")

st.markdown("---")
st.subheader("📬 Share your email to receive Raabiyah’s CV")
name = st.text_input("Your name")
email = st.text_input("Your email")

if st.button("Send CV"):
    if name and email:
        send_email_with_cv(email, st.session_state.chatbot.history_pairs)
        log_chat_to_file(email, st.session_state.chatbot.history_pairs)
        log_to_pushover(f"New lead: {name} ({email}) interacted with the assistant.")
        st.success("Email sent! Raabiyah’s CV and chat summary are on the way.")
    else:
        st.error("Please enter both your name and email.")
