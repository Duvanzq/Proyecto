import os
import json
import random
import requests
from flask import Flask, render_template, request, jsonify

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KB_PATH = os.path.join(BASE_DIR, "kb.json")
STATE_PATH = os.path.join(BASE_DIR, "pet_state.json")

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static"),
)

LLAMA_URL = os.getenv("LLAMA_URL", "http://127.0.0.1:11434/api/generate")
LLAMA_TIMEOUT = int(os.getenv("LLAMA_TIMEOUT", "10"))

SYSTEM_PROMPT = (
    "Eres 'Minetico', una mascota virtual experta en Minecraft. Responde breve, amable y útil. "
    "Incluye pasos concretos, comandos o niveles Y cuando apliquen. Mantén personalidad carismática."
)
def load_kb():
    if not os.path.exists(KB_PATH):
        default = {
            "diamante": "Los diamantes se encuentran entre Y= -59 y -16; mejor entre -58 y -59.",
            "redstone": "Redstone abunda entre Y= -64 y -32; útil para circuitos y granjas."
        }
        with open(KB_PATH, "w", encoding="utf-8") as f:
            json.dump(default, f, ensure_ascii=False, indent=2)
        return default
    with open(KB_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_kb(kb):
    with open(KB_PATH, "w", encoding="utf-8") as f:
        json.dump(kb, f, ensure_ascii=False, indent=2)

KB = load_kb()
def load_state():
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    state = {"name": "Minetico", "mood": "feliz", "hunger": 20}
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    return state

def save_state(state):
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

PET_STATE = load_state()

def lookup_kb(prompt: str) -> str:
    p = (prompt or "").lower()
    snippets = []
    for k, v in KB.items():
        if k.lower() in p or any(word in p for word in k.lower().split()):
            snippets.append(f"{k.capitalize()}: {v}")
    return "\n".join(snippets)

def generate_response(prompt: str) -> str:
    prompt_l = (prompt or "").lower()
    if any(k in prompt_l for k in ["hola", "buenas", "hey"]):
        return f"¡Hola! Soy {PET_STATE.get('name','tu mascota')} 🐾 — ¿minar, construir o domesticar mobs?"
    frases = [
        "¡Buena idea! ¿Quieres que te sugiera un plano de base?",
        "¡Genial! ¿Te cuento un truco para conseguir más hierro?",
        "¡Aventura! ¿Exploramos una cueva?"
    ]
    return random.choice(frases)

def parse_llama_response(j):
    if not j:
        return None
    if isinstance(j, dict):
        if "response" in j and isinstance(j["response"], str):
            return j["response"]
        if "text" in j and isinstance(j["text"], str):
            return j["text"]
        if "output" in j and isinstance(j["output"], str):
            return j["output"]
        choices = j.get("choices") or j.get("results") or []
        if isinstance(choices, list) and len(choices) > 0:
            first = choices[0]
            for k in ("content","text","output"):
                if k in first and isinstance(first[k], str):
                    return first[k]
            content = first.get("content")
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get("type")=="output_text" and "text" in item:
                        return item["text"]
            return str(first)
    return str(j)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    mensaje = data.get("mensaje", "").strip()
    if not mensaje:
        return jsonify({"response": "Escribe algo sobre Minecraft."})

    kb_snips = lookup_kb(mensaje)
    prompt_to_send = SYSTEM_PROMPT
    prompt_to_send += f"\nMascota: nombre={PET_STATE.get('name')}, estado={PET_STATE.get('mood')}\n"
    if kb_snips:
        prompt_to_send += "\nConocimientos relevantes:\n" + kb_snips
    prompt_to_send += "\nUsuario: " + mensaje + "\nRespuesta:"

    try:
        payload = {"model":"llama3","prompt":prompt_to_send,"stream":False}
        resp = requests.post(LLAMA_URL, json=payload, timeout=LLAMA_TIMEOUT)
        if resp.status_code == 200:
            j = resp.json()
            text = parse_llama_response(j) or generate_response(mensaje)
            return jsonify({"response": text})
    except Exception:
        pass

    return jsonify({"response": generate_response(mensaje)})
@app.route("/kb", methods=["GET","POST"])
def kb_route():
    global KB
    if request.method == "GET":
        return jsonify(KB)
    data = request.get_json(silent=True) or {}
    term = (data.get("term") or "").strip()
    text = (data.get("text") or "").strip()
    if not term or not text:
        return jsonify({"error":"term y text requeridos"}), 400
    KB[term] = text
    save_kb(KB)
    return jsonify({"ok": True, "kb": KB})

@app.route("/upload_kb", methods=["POST"])
def upload_kb():
    global KB
    f = request.files.get("file")
    if not f:
        return jsonify({"error":"file requerido"}), 400
    try:
        data = json.load(f)
        if not isinstance(data, dict):
            return jsonify({"error":"JSON invalid, debe ser objeto {term: text}"}), 400
        KB = data
        save_kb(KB)
        return jsonify({"ok": True, "kb": KB})
    except Exception as e:
        return jsonify({"error": str(e)}), 400
@app.route("/state", methods=["GET","POST"])
def state_route():
    global PET_STATE
    if request.method == "GET":
        return jsonify(PET_STATE)
    data = request.get_json(silent=True) or {}
    PET_STATE.update(data)
    save_state(PET_STATE)
    return jsonify(PET_STATE)

@app.route("/__debug")
def _debug():
    info = {"cwd": BASE_DIR, "template_folder": app.template_folder, "static_folder": app.static_folder}
    try:
        info["templates"] = os.listdir(app.template_folder) if os.path.isdir(app.template_folder) else []
        info["statics"] = os.listdir(app.static_folder) if os.path.isdir(app.static_folder) else []
        info["kb"] = list(KB.keys())
    except Exception as e:
        info["error"] = str(e)
    return jsonify(info)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
