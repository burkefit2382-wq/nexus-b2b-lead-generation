const form = document.querySelector("#pilotForm");
const note = document.querySelector("#formNote");
const chatForm = document.querySelector("#chatForm");
const chatLog = document.querySelector("#chatLog");
const chatNote = document.querySelector("#chatNote");
const runEnrichment = document.querySelector("#runEnrichment");
const pipelineResults = document.querySelector("#pipelineResults");
const generateSaleLead = document.querySelector("#generateSaleLead");
const leadMarketGrid = document.querySelector("#leadMarketGrid");
const revenueStatus = document.querySelector("#revenueStatus");
const checkoutNote = document.querySelector("#checkoutNote");
const fulfillmentStatus = document.querySelector("#fulfillmentStatus");
const fulfillmentSummary = document.querySelector("#fulfillmentSummary");
const fulfillmentList = document.querySelector("#fulfillmentList");
const testFulfillmentSummary = document.querySelector("#testFulfillmentSummary");
const testFulfillmentList = document.querySelector("#testFulfillmentList");
const osintReportForm = document.querySelector("#osintReportForm");
const osintReportNote = document.querySelector("#osintReportNote");
const osintReportResults = document.querySelector("#osintReportResults");
const nexusApiBaseUrl = (window.NEXUS_API_BASE_URL || "https://nexus-tracking-api.onrender.com").replace(/\/$/, "");

window.addEventListener("hashchange", renderPage);
window.addEventListener("load", () => {
  renderPage();
  loadRevenueStatus();
  loadFulfillmentStatus();
});
renderPage();

function renderPage() {
  const params = new URLSearchParams(window.location.search);
  const page = (params.get("page") || window.location.hash.replace("#", "")).toLowerCase();

  if (page === "dashboard") {
    loadDashboard();
  }
}

function loadDashboard() {
  if (window.location.pathname === "/dashboard" || window.location.pathname.endsWith("/dashboard.html")) {
    return;
  }

  window.location.replace("/dashboard");
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
    await createNexusLead({
      name: email,
      intent: "pilot access request",
      location: "Web launch site",
      email,
      phone: "",
      budget: "",
      notes: "Captured from launch site pilot form.",
    });
  } catch (error) {
    const requests = JSON.parse(localStorage.getItem("leadgenPilotRequests") || "[]");
    requests.push({ email, capturedAt: new Date().toISOString(), fallback: true });
    localStorage.setItem("leadgenPilotRequests", JSON.stringify(requests));
    try {
      await createNexusLead({
        name: email,
        intent: "pilot access request",
        location: "Web launch site",
        email,
        phone: "",
        budget: "",
        notes: "Captured locally after launch waitlist endpoint was unavailable.",
      });
      note.textContent = "Pilot request saved to the Nexus lead API.";
    } catch (leadError) {
      note.textContent = "Saved locally for this prototype. Start the launch server to enable /api/waitlist.";
    }
  } finally {
    button.disabled = false;
  }
}

async function createNexusLead(lead) {
  const response = await fetch(`${nexusApiBaseUrl}/leads/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(lead),
  });
  const body = await response.json();
  if (!response.ok) {
    throw new Error(body.detail || body.error || "Unable to create Nexus lead.");
  }
  trackNexusEvent("generate_lead", {
    lead_id: body.id,
    email: lead.email,
    intent: lead.intent,
  });
  return body;
}

function trackNexusEvent(eventName, eventData = {}) {
  fetch(`${nexusApiBaseUrl}/api/event`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      event_name: eventName,
      client_id: getOrCreateClientId(),
      lead_id: eventData.lead_id,
      page_url: window.location.href,
      referrer: document.referrer,
      utm_source: new URLSearchParams(window.location.search).get("utm_source") || "",
      utm_medium: new URLSearchParams(window.location.search).get("utm_medium") || "",
      utm_campaign: new URLSearchParams(window.location.search).get("utm_campaign") || "",
      event_data: eventData,
    }),
  }).catch(() => {});
}

function getOrCreateClientId() {
  const key = "nexusClientId";
  const existing = localStorage.getItem(key);
  if (existing) {
    return existing;
  }
  const value = crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`;
  localStorage.setItem(key, value);
  return value;
}

async function loadRevenueStatus() {
  if (!revenueStatus) {
    return;
  }

  try {
    const response = await fetch("/api/revenue-status", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    const body = await response.json();
    if (!response.ok) {
      throw new Error(body.error || "Unable to check revenue status.");
    }

    const delivery = body.resend.configured ? "Resend delivery verified" : "Resend delivery needs secrets";
    const checkout = body.stripe?.configured ? "Stripe checkout ready" : "Stripe checkout needs secrets";
    revenueStatus.textContent = `${body.leadMarket.status}: ${body.leadMarket.availableCount} ${body.leadMarket.name}. ${checkout}. ${delivery}.`;
  } catch (error) {
    revenueStatus.textContent = "For Sale is on. Resend delivery status unavailable locally.";
  }
}

async function loadFulfillmentStatus() {
  if (!fulfillmentStatus || !fulfillmentSummary || !fulfillmentList) {
    return;
  }

  try {
    const response = await fetch("/api/fulfillment-status", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    const body = await response.json();
    if (!response.ok) {
      throw new Error(body.error || "Unable to load fulfillment status.");
    }

    const stripeMessage = body.stripe?.configured
      ? `Stripe webhook is configured for ${body.stripe.publicBaseUrl}.`
      : `Stripe needs: ${(body.stripe?.missing || ["configuration"]).join(", ")}.`;
    const resendMessage = body.resend.configured
      ? "Resend delivery is configured."
      : `Resend needs: ${body.resend.missing.join(", ")}.`;
    fulfillmentStatus.textContent = `${stripeMessage} ${resendMessage}`;

    fulfillmentSummary.innerHTML = [
      fulfillmentMetric(body.summary.total, "Total orders"),
      fulfillmentMetric(body.summary.delivered, "Delivered"),
      fulfillmentMetric(body.summary.pending, "Pending"),
      fulfillmentMetric(body.summary.revenue, "Logged revenue"),
    ].join("");

    if (!body.recent.length) {
      fulfillmentList.innerHTML = `
        <article>
          <span class="badge warning">Waiting</span>
          <h3>No paid webhook events yet</h3>
          <p>Completed Stripe checkouts will appear here after the webhook receives them.</p>
        </article>
      `;
      renderTestFulfillment(body);
      return;
    }

    fulfillmentList.innerHTML = body.recent.map((record) => `
      <article>
        <span class="badge ${record.status === "delivered" ? "" : "warning"}">${escapeHtml(record.status)}</span>
        <h3>${escapeHtml(record.catalogName)}</h3>
        <p>${escapeHtml(record.amount)} - ${escapeHtml(record.buyerEmail || "buyer email unavailable")}</p>
        <div class="listing-meta">
          <strong>${escapeHtml(record.category)}</strong>
          <strong>${escapeHtml(record.delivery)}</strong>
        </div>
        <p>Session ending ${escapeHtml(record.sessionId || "unknown")}</p>
      </article>
    `).join("");
    renderTestFulfillment(body);
  } catch (error) {
    fulfillmentStatus.textContent = error.message || "Fulfillment status unavailable.";
  }
}

function fulfillmentMetric(value, label) {
  return `<article><strong>${escapeHtml(value)}</strong><span>${escapeHtml(label)}</span></article>`;
}

function renderTestFulfillment(body) {
  if (!testFulfillmentSummary || !testFulfillmentList) {
    return;
  }

  const testSummary = body.testSummary || { total: 0, pending: 0, manual: 0, revenue: "$0.00 USD" };
  const testRecords = body.testRecords || [];
  testFulfillmentSummary.innerHTML = [
    fulfillmentMetric(testSummary.total, "Test records"),
    fulfillmentMetric(testSummary.pending, "Pending tests"),
    fulfillmentMetric(testSummary.manual, "Manual tests"),
    fulfillmentMetric(testSummary.revenue, "Test value"),
  ].join("");

  if (!testRecords.length) {
    testFulfillmentList.innerHTML = `
      <article>
        <span class="badge warning">Clear</span>
        <h3>No test transactions loaded</h3>
        <p>Smoke-test and blocked test records will stay separated from real customer orders.</p>
      </article>
    `;
    return;
  }

  testFulfillmentList.innerHTML = testRecords.map((record) => `
    <article>
      <span class="badge warning">${escapeHtml(record.status)}</span>
      <h3>${escapeHtml(record.catalogName)}</h3>
      <p>${escapeHtml(record.amount)} - ${escapeHtml(record.buyerEmail || "buyer email unavailable")}</p>
      <div class="listing-meta">
        <strong>${escapeHtml(record.category)}</strong>
        <strong>${escapeHtml(record.delivery)}</strong>
      </div>
      <p>${escapeHtml(record.deliveryResult || "No delivery detail recorded.")}</p>
      <p>Session ending ${escapeHtml(record.sessionId || "unknown")}</p>
    </article>
  `).join("");
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

osintReportForm?.addEventListener("submit", async (event) => {
  event.preventDefault();

  const data = new FormData(osintReportForm);
  const payload = {
    reportType: String(data.get("reportType") || ""),
    subject: String(data.get("subject") || "").trim(),
    requesterEmail: String(data.get("requesterEmail") || "").trim(),
    useCase: String(data.get("useCase") || "").trim(),
    publicUrls: String(data.get("publicUrls") || "").trim(),
    scopeNotes: String(data.get("scopeNotes") || "").trim(),
    authorized: data.get("authorized") === "on",
  };
  const button = osintReportForm.querySelector("button");
  button.disabled = true;
  osintReportNote.textContent = "Generating authorized OSINT preview...";
  osintReportResults.innerHTML = resultCard("Running", "OSINT preview in progress", "Validating authorization, scope, source notes, and buyer-safe reporting rules.");

  try {
    const response = await fetch("/api/osint-report", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const body = await response.json();
    if (!response.ok) {
      throw new Error(body.error || "OSINT report intake failed.");
    }
    renderOsintReport(body.report);
    osintReportNote.textContent = `${body.message} Notification: ${body.notification}.`;
  } catch (error) {
    osintReportResults.innerHTML = resultCard("Blocked", "OSINT request not queued", error.message || "Check the authorization and report scope.");
    osintReportNote.textContent = error.message || "Unable to queue OSINT report.";
  } finally {
    button.disabled = false;
  }
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

function renderOsintReport(report) {
  const focus = Array.isArray(report.focusAreas) ? report.focusAreas.join(", ") : "Review required";
  const sources = Array.isArray(report.providedSources) && report.providedSources.length
    ? report.providedSources.join(", ")
    : "No public sources supplied yet";
  const rules = Array.isArray(report.buyerSafeRules) ? report.buyerSafeRules.join(" ") : "";

  osintReportResults.innerHTML = [
    resultCard("Queued", report.title, report.summary),
    resultCard("Score", `${report.confidence} confidence: ${report.opportunityScore}`, `Focus: ${focus}.`),
    resultCard("Sources", "Public-source plan", sources),
    resultCard("Safety", "Buyer-safe rules", rules),
    resultCard("Next action", report.status, report.nextAction),
  ].join("");
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

leadMarketGrid?.addEventListener("click", async (event) => {
  const button = event.target.closest(".buy-lead-package");
  if (!button) {
    return;
  }

  const quantity = Number(button.dataset.quantity || 0);
  const price = Number(button.dataset.price || 0);
  const email = window.prompt(`Delivery email for ${quantity} HQ Florida leads ($${price}):`);
  if (!email) {
    return;
  }

  button.disabled = true;
  const originalText = button.textContent;
  button.textContent = "Submitting...";

  try {
    const response = await fetch("/api/lead-package-request", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, quantity }),
    });
    const body = await response.json();
    if (!response.ok) {
      throw new Error(body.error || "Unable to submit package request.");
    }
    button.textContent = "Request received";
    revenueStatus.textContent = `${body.message} Resend: ${body.notification}.`;
  } catch (error) {
    button.textContent = originalText;
    revenueStatus.textContent = error.message || "Unable to submit package request.";
  } finally {
    button.disabled = false;
  }
});

document.addEventListener("click", async (event) => {
  const button = event.target.closest(".checkout-button");
  if (!button) {
    return;
  }

  const priceId = button.dataset.priceId || "";
  const originalText = button.textContent;
  button.disabled = true;
  button.textContent = "Opening checkout...";
  setCheckoutNote("Connecting to Stripe checkout...");

  try {
    const response = await fetch("/api/checkout", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ priceId }),
    });
    const body = await response.json();

    if (body.url) {
      window.location.href = body.url;
      return;
    }

    if (body.setupNeeded) {
      throw new Error(`${body.error} Missing: ${body.missing.join(", ")}.`);
    }

    throw new Error(body.error || "Checkout is unavailable.");
  } catch (error) {
    button.textContent = originalText;
    setCheckoutNote(error.message || "Checkout is unavailable. Configure Stripe and try again.");
  } finally {
    button.disabled = false;
  }
});

function setCheckoutNote(message) {
  if (checkoutNote) {
    checkoutNote.textContent = message;
  } else if (revenueStatus) {
    revenueStatus.textContent = message;
  }
}

function renderSaleListing(listing) {
  const tiers = Array.isArray(listing.pricing) ? listing.pricing : [
    { quantity: 10, price: listing.price, currency: listing.currency || "USD", priceId: listing.priceId },
  ];
  const available = listing.inventory?.availableCount || "Available";
  const inventoryName = listing.inventory?.name || "HQ Florida leads";

  leadMarketGrid.innerHTML = `
    ${tiers.map((tier) => `
      <article class="lead-listing">
        <span class="badge">${escapeHtml(listing.status)}</span>
        <h3>${escapeHtml(inventoryName)} - ${escapeHtml(tier.quantity)} AI-enriched leads</h3>
        <p>${escapeHtml(listing.summary)}</p>
        <div class="listing-meta">
          <strong>${escapeHtml(tier.quantity)} leads</strong>
          <strong>${escapeHtml(available)} available</strong>
        </div>
        <p class="listing-price">$${escapeHtml(tier.price)} ${escapeHtml(tier.currency || listing.currency)}</p>
        <p><strong>Included:</strong> ${escapeHtml(listing.included.join(", "))}</p>
        <p><strong>Excluded:</strong> ${escapeHtml(listing.privateFieldsExcluded.join(", "))}</p>
        <button type="button" class="checkout-button" data-price-id="${escapeHtml(tier.priceId || "")}">Buy ${escapeHtml(tier.quantity)} leads - $${escapeHtml(tier.price)}</button>
      </article>
    `).join("")}
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
