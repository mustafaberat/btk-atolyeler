const rowsEl = document.querySelector("#rows");
const countEl = document.querySelector("#count");
const detailEl = document.querySelector("#detail");
const qEl = document.querySelector("#q");
const ilEl = document.querySelector("#il");
const durumEl = document.querySelector("#durum");

let ilanlar = [];
let selected = null;
let score = null;

function esc(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

async function api(path, body) {
  const response = await fetch(path, body
    ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }
    : undefined);
  const data = await response.json();
  if (!response.ok) throw new Error(data.hata || "İstek olmadı");
  return data;
}

function paintRows() {
  rowsEl.innerHTML = ilanlar.map((ilan) => `
    <tr data-ikn="${esc(ilan.ikn)}" class="${selected === ilan.ikn ? "active" : ""}">
      <td class="ikn">${esc(ilan.ikn)}</td>
      <td>${esc(ilan.baslik)}</td>
      <td>${esc(ilan.il || "")}</td>
      <td>${esc(ilan.teklif_tarihi || "")}</td>
      <td><span class="pill ${esc(ilan.durum)}">${esc(ilan.durum)}</span></td>
    </tr>
  `).join("");
}

async function loadList() {
  const params = new URLSearchParams({
    q: qEl.value.trim(),
    il: ilEl.value.trim(),
    durum: durumEl.value,
  });
  const data = await api(`/api/ilanlar?${params}`);
  ilanlar = data.ilanlar;
  countEl.textContent = `${data.kayit} kayıt · arşivde ${data.toplam}`;
  paintRows();
}

function renderDetail(ilan, lead) {
  const winner = ilan.kazanan_firma
    ? `<div class="winner"><b>Kazanan:</b> ${esc(ilan.kazanan_firma)}${ilan.kazanan_tutar ? ` · ${esc(ilan.kazanan_tutar)}` : ""}</div>`
    : "";
  const scoreBlock = score
    ? `<div class="score"><strong>${esc(score.skor)} → ${esc(score.aksiyon)}</strong>
        <ul>${(score.gerekce || []).map((item) => `<li>${esc(item)}</li>`).join("")}</ul></div>`
    : "";
  const mail = lead
    ? `<p class="note">Taslak kayıtlı. Mail gönderilmez.</p>
       <pre class="mail">${esc(lead.mail_taslagi || "")}</pre>
       <div class="actions">
         <button class="quiet" data-durum="yazilacak" data-id="${lead.id}">yazılacak</button>
         <button class="quiet" data-durum="yazildi" data-id="${lead.id}">yazıldı</button>
         <button class="quiet" data-durum="cevap_yok" data-id="${lead.id}">cevap yok</button>
       </div>`
    : "";
  const askLead = ilan.kazanan_firma && !lead
    ? `<button id="make-lead" type="button">Görev talebi yaz</button>`
    : "";
  detailEl.innerHTML = `
    <p class="kicker">${esc(ilan.ikn)}</p>
    <h2>${esc(ilan.baslik)}</h2>
    <p class="meta">${esc(ilan.kurum || "")} · ${esc(ilan.il || "")} · teklif ${esc(ilan.teklif_tarihi || "—")}</p>
    <p class="ozet">${esc(ilan.ozet_text || "")}</p>
    ${winner}
    <div class="actions">
      <button id="score" type="button">Uygunluk skorunu hesapla</button>
      ${askLead}
    </div>
    ${scoreBlock}
    ${mail}
  `;
  detailEl.querySelector("#score").addEventListener("click", () => runScore(ilan.ikn));
  const leadButton = detailEl.querySelector("#make-lead");
  if (leadButton) leadButton.addEventListener("click", () => runLead(ilan.ikn));
  detailEl.querySelectorAll("[data-durum]").forEach((button) => {
    button.addEventListener("click", () => setDurum(button.dataset.id, button.dataset.durum, ilan.ikn));
  });
}

async function openIlan(ikn, keepScore = false) {
  selected = ikn;
  if (!keepScore) score = null;
  paintRows();
  const data = await api(`/api/ilan?ikn=${encodeURIComponent(ikn)}`);
  renderDetail(data.ilan, data.lead);
  const row = rowsEl.querySelector("tr.active");
  if (row) row.scrollIntoView({ block: "nearest" });
}

async function runScore(ikn) {
  const button = detailEl.querySelector("#score");
  button.disabled = true;
  button.textContent = "Skorlanıyor…";
  try {
    const data = await api("/api/skor", { ikn });
    score = data.uygunluk;
    await openIlan(ikn, true);
  } catch (error) {
    button.disabled = false;
    button.textContent = error.message;
  }
}

async function runLead(ikn) {
  await api("/api/lead", { ikn });
  await openIlan(ikn, true);
}

async function setDurum(id, durum, ikn) {
  await api("/api/lead/durum", { id: Number(id), durum });
  await openIlan(ikn, true);
}

let timer = 0;
function scheduleLoad() {
  clearTimeout(timer);
  timer = setTimeout(() => loadList().catch((error) => { countEl.textContent = error.message; }), 180);
}

qEl.addEventListener("input", scheduleLoad);
ilEl.addEventListener("input", scheduleLoad);
durumEl.addEventListener("change", () => loadList());
rowsEl.addEventListener("click", (event) => {
  const row = event.target.closest("tr");
  if (row) openIlan(row.dataset.ikn);
});
document.querySelector("#demo").addEventListener("click", async () => {
  qEl.value = "1475835";
  ilEl.value = "";
  durumEl.value = "";
  await loadList();
  await openIlan("2026/1475835");
});

loadList()
  .then(() => openIlan("2026/1475835"))
  .catch((error) => { countEl.textContent = error.message; });
