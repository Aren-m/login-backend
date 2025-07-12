# fastapi_server.py
"""
Self‑contained FastAPI backend + minimal web‑chat frontend
---------------------------------------------------------
* Run with  :  `uvicorn fastapi_server:app --reload`

Dependencies
------------
    python -m venv venv && source venv/bin/activate  # Windows: venv\Scripts\activate
    pip install fastapi "uvicorn[standard]" python-dotenv openai pillow

Notes
-----
* No ngrok / nest_asyncio here—pure local dev. Add back if you need tunnelling.
* Frontend is a single HTML page injected by FastAPI; tweak as you like.
"""
from __future__ import annotations

import os
from textwrap import dedent
from typing import List, Tuple

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from openai import OpenAI

# ---------------------------------------------------------------------------
# 1.  ENV & OpenAI client
# ---------------------------------------------------------------------------
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY missing – add it to .env or export before launch")

client = OpenAI(api_key=OPENAI_API_KEY)

EXTRA_PATH = "GravityMedTech.rtf"  # filename
extra_prompt = ""
if os.path.exists(EXTRA_PATH):
    with open(EXTRA_PATH, "r", encoding="utf-8") as f:
        extra_prompt = f.read().strip()


SYSTEM_PROMPT = os.getenv(
    "SYSTEM_PROMPT",
    )

if extra_prompt:
    SYSTEM_PROMPT += "\n\n" + extra_prompt

# ---------------------------------------------------------------------------
# 2.  FastAPI app setup
# ---------------------------------------------------------------------------
app = FastAPI(title="Gurome Guru")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# 3.  Pydantic models
# ---------------------------------------------------------------------------
class ChatRequest(BaseModel):
    message: str
    image_base64: str | None = None
    history: List[Tuple[str, str]] = []  # outer list, each tuple = (user, assistant)

class ChatResponse(BaseModel):
    reply: str

# ---------------------------------------------------------------------------
# 4.  /chat endpoint (POST)
# ---------------------------------------------------------------------------
@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for user_msg, assistant_msg in req.history:
        messages.append({"role": "user", "content": user_msg})
        messages.append({"role": "assistant", "content": assistant_msg})

    user_content = [{"type": "text", "text": req.message}]
    if req.image_base64:
        user_content.append({"type": "image_url", "image_url": {"url": req.image_base64}})
    messages.append({"role": "user", "content": user_content})

    try:
        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.7,
        )
        reply = completion.choices[0].message.content.strip()
    except Exception as exc:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"OpenAI error: {exc}"
        )

    return {"reply": reply}

# ---------------------------------------------------------------------------
# 5.  Front‑end: serve a very small HTML/JS chatbot
# ---------------------------------------------------------------------------
CHAT_HTML = dedent("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
    <meta charset="UTF-8" />
    <title>Guru AI</title>
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');
    body {
    background-size: cover;
    font-family: 'Inter', sans-serif;
    margin: 0;
    padding: 0;
    }
    #chat-toggle.code-badge {
    position: fixed;
    bottom: 24px;
    right: 24px;
    z-index: 1001;
    padding: 13px 32px;
    font-size: 1.17rem;
    font-weight: 700;
    background: linear-gradient(90deg, rgba(20,148,255,0.95) 60%, rgba(59,193,255,0.50) 100%);
    color: #fff;
    border: none;
    border-radius: 22px;
    box-shadow: 0 6px 24px rgba(20, 148, 255, 0.14), 0 2px 12px #b3e1ff4d;
    cursor: pointer;
    letter-spacing: 0.02em;
    transition: 
        background 0.19s, 
        color 0.17s, 
        transform 0.13s,
        box-shadow 0.21s;
    outline: none;
    display: inline-block;
    overflow: visible;
    /* Frosted glass effect: */
    backdrop-filter: blur(8px) saturate(170%);
    -webkit-backdrop-filter: blur(8px) saturate(170%);
    border: 1.5px solid rgba(255,255,255,0.22);
    }

    #chat-toggle.code-badge:hover,
    #chat-toggle.code-badge:focus {
        background: linear-gradient(90deg, rgba(59,193,255,0.55) 0%, rgba(20,148,255,1) 100%);
        color: #e9f7ff;
        transform: scale(1.04);
        box-shadow: 0 12px 36px rgba(20, 148, 255, 0.18), 0 4px 18px #b3e1ff55;
    }



    #chat-container {
        position: fixed; bottom: 100px; right: 36px;
        width: 690px; max-width: 96vw;
        background: rgba(255,255,255,0.80);
        border-radius: 18px;
        box-shadow: 0 16px 48px 0 rgba(90,120,160,0.15), 0 1.5px 8px #e8f0fa;
        opacity: 0; pointer-events: none; 
        transform: scale(0.98) translateY(20px);
        transition: opacity .18s, transform .22s;
        display: flex; flex-direction: column;
        overflow: hidden; z-index: 1000;
        backdrop-filter: blur(16px) saturate(170%);
        -webkit-backdrop-filter: blur(16px) saturate(170%);
        border: 1.5px solid rgba(255,255,255,0.3);
    }
    #chat-container.open {
    opacity: 1; pointer-events: auto; transform: scale(1) translateY(0);
    }
    #chat-onboard {
    padding: 40px 44px 30px 44px;
    display: flex; flex-direction: column; align-items: flex-start;
    animation: fadein .7s;
    }
    @keyframes fadein { from{opacity:0;} to{opacity:1;} }

    #chat-icon {
    font-size: 2.3rem;
    background: linear-gradient(135deg,#e3ebff 50%,#fff 100%);
    border-radius: 50%; width: 44px; height: 44px; display: flex; align-items: center; justify-content: center;
    margin-bottom: 15px; color: #7f94ff; box-shadow: 0 2px 10px #b4c9f621;
    }
    #chat-title {
    font-size: 1.5rem; font-weight: 600; margin-bottom: 10px; color: #26324b;
    letter-spacing: .01em;
    }
    #chat-desc {
    font-size: 1.16rem; color: #415066; margin-bottom: 14px;
    line-height: 1.6;
    }
    .code-badge {
    display: inline-block;
    font-family: inherit;
    font-size: 1.08rem;
    padding: 7px 20px;
    border-radius: 22px;
    margin: 0 3px 0 2px;
    font-weight: 700;
    letter-spacing: 0.01em;
    background: linear-gradient(90deg, #1494ff 60%, #3bc1ff 100%);
    color: #fff;
    box-shadow: 0 2px 8px rgba(20, 148, 255, 0.13);
    border: none;
    transition: 
        background 0.19s,
        color 0.17s,
        transform 0.13s,
        box-shadow 0.21s;
    }
    .code-badge:hover, .code-badge:focus {
    background: linear-gradient(90deg, #3bc1ff 0%, #1494ff 100%);
    color: #e6f7ff;
    transform: scale(1.04);
    box-shadow: 0 8px 24px rgba(20,148,255,0.18);
    }

    .code-badge2 {
    display: inline-block !important;
    color: #1976d2 !important;
    font-weight: 700 !important;
    background: none !important;
    padding: 0 4px !important;
    border-radius: 5px !important;
    font-size: 1.10rem !important;
    transition: transform 0.38s cubic-bezier(.77,.05,.58,1), opacity 0.24s !important;
    }

    #guru-badge-onboard {
    z-index: 10;
    position: relative;
    }

    #guru-badge-header {
    opacity: 0;
    transform: scale(0.85) translateY(-18px);
    transition: opacity 0.33s, transform 0.35s;
    }

    .guru-badge-move {
    transform: translateY(-60px) scale(0.85);
    opacity: 0;
    }

    .guru-badge-show {
    opacity: 1 !important;
    transform: scale(1) translateY(0) !important;
    }
    .chat-example-btn-row {
    display: flex;
    gap: 14px; /* or whatever spacing you want */
    margin-top: 9px;
    }
    #chat-header {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 15px 32px 7px 32px;
    font-size: 1.18rem;
    font-weight: 700;
    background: transparent;
    border-bottom: 1.2px solid #e5ecf6;
    position: sticky;
    top: 0;
    z-index: 2;
    } 
    #chat-example-label {
    font-size: .85rem; color: #8896ad; font-weight: 600;
    margin-top: 12px; letter-spacing: 0.12em;
    }
    .loading-circle {
    display: inline-block;
    width: 28px;
    height: 28px;
    border: 3.5px solid #cbeaff;
    border-top: 3.5px solid #1494ff;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
    margin: 6px 0;
    vertical-align: middle;
    }
    @keyframes spin {
    100% { transform: rotate(360deg); }
    }
    .chat-example-btn {
    margin-top: 9px; padding: 13px 22px;
    border-radius: 11px; border: 1.5px solid #e5eaf0;
    background: #fff; color: #26324b; font-size: 1.05rem; font-family: inherit;
    cursor: pointer; box-shadow: 0 2px 12px #e7effc4d;
    transition: background .12s, box-shadow .18s;
    }
    .chat-example-btn:hover { background: #f6f8fc; box-shadow: 0 4px 24px #b4c9f633;}
    #chat-messages {
    flex: 1; padding: 16px 32px 16px 32px; display: flex; flex-direction: column; gap: 13px;
    overflow-y: auto; background: none; min-height: 56px; max-height: 400px;
    }
    .message {
    max-width: 92%; padding: 15px 18px; border-radius: 16px;
    font-size: 1.06rem; margin-bottom: 0; line-height: 1.66;
    white-space: pre-line; word-break: break-word; box-shadow: 0 1.5px 8px #e7eefa17;
    }
    .user {
    align-self: flex-end; background: linear-gradient(110deg, #eaf4ff 60%, #d2ecff 100%);
    color: #1494ff; border-bottom-right-radius: 6px;
    border-bottom-left-radius: 14px; border-top-left-radius: 13px; border-top-right-radius: 16px;
    margin-right: 4px; margin-left: 38px; border: 1.1px solid #e5edfb;
    }
    .bot {
    align-self: flex-start; background: #fff;
    color: #12254b; border-bottom-left-radius: 7px; border-bottom-right-radius: 16px;
    border-top-right-radius: 13px; border-top-left-radius: 16px;
    margin-left: 4px; margin-right: 38px; border: 1.1px solid #e5edfb;
    }
    #chat-input-area {
    display: flex; border-top: 1.7px solid #e6ecf6; background: #f8fafc;
    padding: 18px 22px; min-height: 68px;
    }
    #chat-input {
    flex: 1; border: none; padding: 15px 14px; font-size: 1.08rem; border-radius: 13px;
    margin-right: 12px; background: #f5f8fd; color: #283c4c; outline: none;
    font-family: inherit; transition: box-shadow 0.12s;
    box-shadow: 0 1.5px 8px #dde7f58e inset;
    }
    #chat-input:focus { box-shadow: 0 2.5px 18px #b2c9ff2b inset; }
    #chat-send {
    border: none;
    background: #1494ff;
    color: #fff;
    font-size: 1.11rem;
    padding: 0 24px;
    border-radius: 11px;
    cursor: pointer;
    font-weight: 600;
    font-family: inherit;
    box-shadow: 0 2px 9px #1494ff26;
    transition: background 0.13s;
    }
    #chat-send:hover:not(:disabled) {
    background: #1070c4;
    }


    </style>
    </head>
    <body>
    <button id="chat-toggle" class="code-badge">Guru AI</button>
    <div id="chat-container">
    <div id="chat-onboard">
        <div id="chat-title">Hi!</div>
        <div id="chat-desc">
        I'm <span id="guru-badge-onboard" class="code-badge">Guru AI</span>, an assistant trained on documentation, clinical studies, and other content.<br>
        Ask me anything about <span class="code-badge2">Supernova</span> or <span class="code-badge2">Neutron</span>.
        </div>
        <div id="chat-example-label">EXAMPLE QUESTIONS</div>
        <div class="chat-example-btn-row">
            <button class="chat-example-btn">What is Supernova?</button>
            <button class="chat-example-btn">What is Neutron?</button>
        </div>
    </div>
    <div id="chat-messages" style="display:none"></div>
    <div id="chat-input-area">
        <input id="chat-input" type="text" autocomplete="off" />
        <button id="chat-send">&#10148;</button>
    </div>
    </div>
    <script>
    const backendUrl = "/chat"; // Change if backend hosted elsewhere
    const toggleBtn = document.getElementById('chat-toggle');
    const container = document.getElementById('chat-container');
    const onboard = document.getElementById('chat-onboard');
    const input = document.getElementById('chat-input');
    const sendBtn = document.getElementById('chat-send');
    const messages = document.getElementById('chat-messages');

                   


    const historyPairs = [];

    toggleBtn.addEventListener('click', () => {
    container.classList.toggle('open');
    if(container.classList.contains('open')) input.focus();
    });

    document.querySelectorAll('.chat-example-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        input.value = btn.textContent;
        input.focus();
    });
    });


    /* Markdown to HTML */
    function renderMarkdown(md) {
    // Headings: #, ##, ###, ####
    md = md.replace(/^#### (.*)$/gm, '<h4>$1</h4>');
    md = md.replace(/^### (.*)$/gm, '<h3>$1</h3>');
    md = md.replace(/^## (.*)$/gm, '<h2>$1</h2>');
    md = md.replace(/^# (.*)$/gm, '<h1>$1</h1>');
    md = md.replace(/\*\*(.*?)\*\*/g, '<b>$1</b>');
    md = md.replace(/\*(.*?)\*/g, '<i>$1</i>');
    md = md.replace(/`([^`]+)`/g, '<span class="code-badge">$1</span>');
    md = md.replace(/\[(.*?)\]\((.*?)\)/g, '<a href="$2" target="_blank">$1</a>');
    // Add badge styling for "Supernova" and "Neutron"
    md = md.replace(/(\bSupernova\b|\bNeutron\b)/gi, '<span class="code-badge2">$1</span>');
    return md;
    }


    function appendMessage(text, sender){
    if(onboard.style.display !== 'none') {
        // Animate onboard Guru AI badge up and out
        document.getElementById('guru-badge-onboard').classList.add('guru-badge-move');
        setTimeout(() => {
        onboard.style.display = 'none';
        messages.style.display = 'flex';
        }, 410); // matches the CSS transition duration
    }

    const div = document.createElement('div');
    div.className = 'message ' + sender;
    div.innerHTML = renderMarkdown(text);
    messages.appendChild(div);
    }

    function setWaiting(wait){
    input.disabled = wait;
    sendBtn.disabled = wait;
    }

    async function sendMessage(){
    const userText = input.value.trim();
    if(!userText) return;
    appendMessage(userText,'user');
    input.value='';
    setWaiting(true);
                   
    const placeholderDiv = document.createElement('div');
    placeholderDiv.className = 'message bot';
    placeholderDiv.innerHTML = `<span class="loading-circle"></span>`;
    messages.appendChild(placeholderDiv);
    messages.scrollTop = messages.scrollHeight; // Scroll to bottom

    try{
        const res = await fetch(backendUrl, {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({message:userText, history:historyPairs})
        });
        if(!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        placeholderDiv.innerHTML = renderMarkdown(data.reply);
        historyPairs.push([userText, data.reply]);
    }catch(err){
        console.error(err);
        appendMessage('⚠️ Error contacting server','bot');
    }finally{
        setWaiting(false);
        input.focus();
    }
    }

    sendBtn.addEventListener('click', sendMessage);
    input.addEventListener('keypress', e => { if(e.key==='Enter') sendMessage(); });
    </script>
    </body>
    </html>
""")

from fastapi.staticfiles import StaticFiles

app.mount("/static", StaticFiles(directory="."), name="static")


@app.get("/", response_class=HTMLResponse)
async def root():
    return CHAT_HTML

# ---------------------------------------------------------------------------
# 6.  Run directly:  python fastapi_server.py
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "fastapi_server:app",
        host="127.0.0.1",
        port=8000,
        reload=True,  # convenient during dev
    )
