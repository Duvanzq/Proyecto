// ...existing code...
document.addEventListener("DOMContentLoaded", () => {
  const input = document.getElementById("input");
  const send = document.getElementById("send");
  const messages = document.getElementById("messages");

  function addMsg(text, cls){
    const el = document.createElement("div");
    el.className = cls;
    el.textContent = text;
    messages.appendChild(el);
    messages.scrollTop = messages.scrollHeight;
  }

  async function enviar(msg){
    addMsg("Tú: " + msg, "me");
    try {
      const res = await fetch("/chat", {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify({mensaje: msg})
      });
      const j = await res.json();
      const text = j.response || j.output || JSON.stringify(j);
      addMsg("Mascota: " + text, "bot");
    } catch (e) {
      addMsg("Mascota: error de conexión", "bot");
    }
  }

  send.addEventListener("click", () => {
    const msg = input.value.trim();
    if(!msg) return;
    input.value = "";
    enviar(msg);
  });

  input.addEventListener("keypress", (e) => {
    if(e.key === "Enter") send.click();
  });
});
// ...existing code...