const API = "https://DEIN-BACKEND.onrender.com";
let consent = false;
let history = [];

function add(role, text) {
  const div = document.createElement("div");
  div.textContent = `${role}: ${text}`;
  document.getElementById("chat").appendChild(div);
}

async function start() {
  const res = await fetch(`${API}/symptom/start`, { method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({}) });
  const data = await res.json();
  add("Bot", data.reply);
}

async function reply(text) {
  add("User", text);
  history.push({ role: "user", content: text });
  if (!consent && text.toLowerCase().includes("ja")) consent = true;
  const res = await fetch(`${API}/symptom/reply`, { method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({ history, consent }) });
  const data = await res.json();
  add("Bot", data.reply);
}

document.getElementById("send").onclick = () => {
  const val = document.getElementById("msg").value;
  document.getElementById("msg").value = "";
  reply(val);
};

start();
