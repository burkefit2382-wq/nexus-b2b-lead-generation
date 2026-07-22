const checks = [
  {
    name: "Public storefront",
    url: "https://nexuscloud.sh/",
    expect: [200],
  },
  {
    name: "Command center",
    url: "https://nexuscloud.sh/dashboard",
    expect: [200],
  },
  {
    name: "Public workflow demo",
    url: "https://nexuscloud.sh/workflow-demo",
    expect: [200],
  },
  {
    name: "Public API health",
    url: "https://nexuscloud.sh/api/health",
    expect: [200],
    bodyIncludes: "healthy",
  },
  {
    name: "Backend direct health",
    url: "https://nexus-b2b-lead-generation.onrender.com/api/health",
    expect: [200],
    bodyIncludes: "healthy",
  },
  {
    name: "Checkout route",
    url: "https://nexuscloud.sh/api/checkout",
    expect: [200, 405],
  },
  {
    name: "HubSpot status route",
    url: "https://nexuscloud.sh/api/hubspot-status",
    expect: [200],
    bodyIncludes: '"hubspot"',
  },
  {
    name: "Stripe webhook route reachable",
    url: "https://nexuscloud.sh/api/stripe-webhook",
    method: "POST",
    expect: [400, 503],
  },
];

const timeoutMs = Number(process.env.UPTIME_TIMEOUT_MS || 15000);

async function fetchWithTimeout(url, options = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } finally {
    clearTimeout(timeout);
  }
}

const failures = [];

for (const check of checks) {
  const response = await fetchWithTimeout(check.url, {
    method: check.method || "GET",
    headers: check.method === "POST" ? { "content-type": "application/json" } : undefined,
    body: check.method === "POST" ? "{}" : undefined,
  });
  const text = await response.text();
  const statusOk = check.expect.includes(response.status);
  const bodyOk = check.bodyIncludes ? text.includes(check.bodyIncludes) : true;
  const icon = statusOk && bodyOk ? "PASS" : "FAIL";
  console.log(`${icon} ${check.name}: ${response.status} ${check.url}`);
  if (!statusOk || !bodyOk) {
    failures.push({
      name: check.name,
      status: response.status,
      expected: check.expect,
      bodyIncludes: check.bodyIncludes,
    });
  }
}

if (failures.length) {
  console.error(JSON.stringify({ failures }, null, 2));
  process.exit(1);
}
