const form = document.querySelector("#pilotForm");
const note = document.querySelector("#formNote");
const chatForm = document.querySelector("#chatForm");
const chatLog = document.querySelector("#chatLog");
const chatNote = document.querySelector("#chatNote");
const runEnrichment = document.querySelector("#runEnrichment");
const pipelineResults = document.querySelector("#pipelineResults");
const generateSaleLead = document.querySelector("#generateSaleLead");
const leadMarketGrid = document.querySelector("#leadMarketGrid");

window.addEventListener("hashchange", renderPage);
window.addEventListener("load", renderPage);
renderPage();

function renderPage() {
  const params = new URLSearchParams(window.location.search);
  const page = (params.get("page") || window.location.hash.replace("#", "")).toLowerCase();

  if (page === "dashboard") {
    loadDashboard();
  }
}

function loadDashboard() {
  // Inside the NEXUS app shell this page is framed; break out to the live React console.
  try {
    window.top.location.href = "/dashboard";
  } catch (e) {
    window.location.href = "/dashboard";
  }
}

form?.addEventListener("submit", (event) => {
  event.preventDefault();

  const data = new FormData(form);
  const email = String(data.get("email") || "").trim();

  if (!email) {
    note.textContent = "Enter a work email to request pilot access.";
    return;
  }

  submitWaitlistRequest(email);
});

async function submitWaitlistRequest(email) {
  const button = form.querySelector("button");
  button.disabled = true;
  note.textContent = "Sending pilot request...";

  try {
    const response = await fetch("/api/waitlist", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email }),
    });
    const result = await response.json();

    if (!response.ok) {
      throw new Error(result.error || "Unable to submit pilot request.");
    }

    form.reset();
    note.textContent = "Pilot request received. We will follow up with next steps.";
  } catch (error) {
    const requests = JSON.parse(localStorage.getItem("leadgenPilotRequests") || "[]");
    requests.push({ email, capturedAt: new Date().toISOString(), fallback: true });
    localStorage.setItem("leadgenPilotRequests", JSON.stringify(requests));
    note.textContent = "Saved locally for this prototype. Start the launch server to enable /api/waitlist.";
  } finally {
    button.disabled = false;
  }
}

chatForm?.addEventListener("submit", (event) => {
  event.preventDefault();
  const data = new FormData(chatForm);
  const prompt = String(data.get("prompt") || "").trim();
  if (!prompt) {
    chatNote.textContent = "Enter a command-center question.";
    return;
  }
  submitChatPrompt(prompt);
});

async function submitChatPrompt(prompt) {
  const button = chatForm.querySelector("button");
  appendChatMessage("user", "You", prompt);
  chatForm.reset();
  button.disabled = true;
  chatNote.textContent = "Nexus AI is thinking...";

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt }),
    });
    const result = await response.json();

    if (!response.ok) {
      throw new Error(result.error || "Unable to reach Nexus AI.");
    }

    appendChatMessage("assistant", "Nexus Llama 3", result.answer);
    chatNote.textContent = result.mode === "llama_endpoint"
      ? "Connected to configured Llama endpoint."
      : "Safe mode response. Configure LLAMA_CHAT_ENDPOINT for live Llama 3.";
  } catch (error) {
    appendChatMessage("assistant", "Nexus Llama 3", "Chat is offline locally. Restart the launch server and try again.");
    chatNote.textContent = "Unable to reach /api/chat.";
  } finally {
    button.disabled = false;
  }
}

function appendChatMessage(kind, name, text) {
  const message = document.createElement("div");
  message.className = `chat-message ${kind}`;

  const speaker = document.createElement("strong");
  speaker.textContent = name;

  const body = document.createElement("p");
  body.textContent = text;

  message.append(speaker, body);
  chatLog.append(message);
  chatLog.scrollTop = chatLog.scrollHeight;
}

runEnrichment?.addEventListener("click", async () => {
  runEnrichment.disabled = true;
  pipelineResults.innerHTML = resultCard("Running", "AI pipeline in progress", "Validating scrape record, enriching context, scoring priority, and preparing storefront-safe fields.");

  try {
    const response = await fetch("/api/enrich-score", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        lead: {
          company: "Northstar Labs",
          signal: "Hiring growth and new contract activity",
          market: "GovTech / field operations",
          source: "Approved source allowlist",
        },
      }),
    });
    const body = await response.json();
    if (!response.ok) {
      throw new Error(body.error || "Pipeline failed.");
    }
    renderPipelineResult(body.result);
  } catch (error) {
    pipelineResults.innerHTML = resultCard("Error", "Pipeline unavailable", "Restart the launch server and try again.");
  } finally {
    runEnrichment.disabled = false;
  }
});

function renderPipelineResult(result) {
  pipelineResults.innerHTML = [
    resultCard("Enrichment", result.company, result.summary),
    resultCard("Score", `${result.scoreBand} priority: ${result.score}`, `Confidence: ${result.confidence}. ${result.reasons.join(" ")}`),
    resultCard("Next action", result.nextAction, `Storefront draft: ${result.storefrontSafeFields.title} - ${result.storefrontSafeFields.summary}`),
  ].join("");
}

function resultCard(label, title, body) {
  return `
    <div class="result-card">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(title)}</strong>
      <p>${escapeHtml(body)}</p>
    </div>
  `;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

generateSaleLead?.addEventListener("click", async () => {
  generateSaleLead.disabled = true;
  leadMarketGrid.innerHTML = marketListingSkeleton("Generating", "Creating AI-enriched lead package...");

  try {
    const response = await fetch("/api/sale-listing", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        lead: {
          company: "Northstar Labs",
          signal: "Hiring growth and new contract activity",
          market: "GovTech / field operations",
          source: "Approved source allowlist",
        },
      }),
    });
    const body = await response.json();
    if (!response.ok) {
      throw new Error(body.error || "Sale listing generation failed.");
    }
    renderSaleListing(body.listing);
  } catch (error) {
    leadMarketGrid.innerHTML = marketListingSkeleton("Error", "Could not generate listing. Restart the launch server and try again.");
  } finally {
    generateSaleLead.disabled = false;
  }
});

function renderSaleListing(listing) {
  leadMarketGrid.innerHTML = `
    <article class="lead-listing">
      <span class="badge">${escapeHtml(listing.status)}</span>
      <h3>${escapeHtml(listing.title)}</h3>
      <p>${escapeHtml(listing.summary)}</p>
      <div class="listing-meta">
        <strong>${escapeHtml(listing.scoreBand)} score: ${escapeHtml(listing.score)}</strong>
        <strong>Confidence: ${escapeHtml(listing.confidence)}</strong>
      </div>
      <p class="listing-price">$${escapeHtml(listing.price)} ${escapeHtml(listing.currency)}</p>
      <p><strong>Included:</strong> ${escapeHtml(listing.included.join(", "))}</p>
      <p><strong>Excluded:</strong> ${escapeHtml(listing.privateFieldsExcluded.join(", "))}</p>
      <button type="button">${escapeHtml(listing.cta)}</button>
    </article>
  `;
}

function marketListingSkeleton(label, body) {
  return `
    <article class="lead-listing">
      <span class="badge">${escapeHtml(label)}</span>
      <h3>Lead package</h3>
      <p>${escapeHtml(body)}</p>
      <div class="listing-meta">
        <strong>Score pending</strong>
        <strong>Review pending</strong>
      </div>
    </article>
  `;
}
