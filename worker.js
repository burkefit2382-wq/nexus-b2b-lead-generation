const MAX_RETRIES = 3;
const RETRY_DELAY_MS = 150;
const DEFAULT_BACKEND_ORIGIN = "https://nexus-b2b-lead-generation.onrender.com";

async function fetchWithRetry(binding, request, retries) {
  let lastResponse;
  for (let attempt = 1; attempt <= retries; attempt++) {
    try {
      const response = await binding.fetch(request.clone());
      if (response.ok || response.status < 500) {
        const headers = new Headers(response.headers);
        if (attempt > 1) {
          headers.set("X-Retry-Count", String(attempt - 1));
        }
        return new Response(response.body, { status: response.status, headers });
      }
      lastResponse = response;
      if (attempt === retries) {
        const headers = new Headers(lastResponse.headers);
        headers.set("X-Retry-Count", String(attempt));
        return new Response(lastResponse.body, { status: lastResponse.status, headers });
      }
    } catch (err) {
      if (attempt === retries) throw err;
    }
    await new Promise((resolve) => setTimeout(resolve, RETRY_DELAY_MS * attempt));
  }
}

async function fetchNetworkWithRetry(request, retries) {
  let lastResponse;
  for (let attempt = 1; attempt <= retries; attempt++) {
    try {
      const response = await fetch(request.clone());
      if (response.ok || response.status < 500) {
        const headers = new Headers(response.headers);
        if (attempt > 1) {
          headers.set("X-Retry-Count", String(attempt - 1));
        }
        return new Response(response.body, { status: response.status, headers });
      }
      lastResponse = response;
      if (attempt === retries) {
        const headers = new Headers(lastResponse.headers);
        headers.set("X-Retry-Count", String(attempt));
        return new Response(lastResponse.body, { status: lastResponse.status, headers });
      }
    } catch (err) {
      if (attempt === retries) throw err;
    }
    await new Promise((resolve) => setTimeout(resolve, RETRY_DELAY_MS * attempt));
  }
}

function buildBackendRequest(request, publicUrl, backendOrigin) {
  const target = new URL(publicUrl.pathname + publicUrl.search, backendOrigin);
  const headers = new Headers(request.headers);
  headers.set("X-Forwarded-Host", publicUrl.host);
  headers.set("X-Forwarded-Proto", publicUrl.protocol.replace(":", ""));
  return new Request(target, {
    method: request.method,
    headers,
    body: request.body,
    redirect: request.redirect,
  });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const backendOrigin = env.BACKEND_ORIGIN || DEFAULT_BACKEND_ORIGIN;

    if (url.pathname.startsWith("/api/") || url.pathname === "/stripe/webhook") {
      return fetchNetworkWithRetry(buildBackendRequest(request, url, backendOrigin), MAX_RETRIES);
    }

    if (url.pathname === "/dashboard" || url.pathname === "/dashboard/") {
      url.pathname = "/dashboard.html";
      return fetchWithRetry(env.ASSETS, new Request(url, request), MAX_RETRIES);
    }

    if (url.pathname === "/lead-control-center" || url.pathname === "/control-center" || url.pathname === "/control") {
      url.pathname = "/lead-control-center.html";
      return fetchWithRetry(env.ASSETS, new Request(url, request), MAX_RETRIES);
    }

    if (url.pathname === "/workflow" || url.pathname === "/workflow/" || url.pathname === "/workflow-demo" || url.pathname === "/workflow-demo/") {
      url.pathname = "/workflow-demo.html";
      return fetchWithRetry(env.ASSETS, new Request(url, request), MAX_RETRIES);
    }

    return fetchWithRetry(env.ASSETS, request, MAX_RETRIES);
  },
};
