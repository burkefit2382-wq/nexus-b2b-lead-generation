const MAX_RETRIES = 3;
const RETRY_DELAY_MS = 150;
const SECURITY_HEADERS = {
  "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
  "X-Content-Type-Options": "nosniff",
  "X-Frame-Options": "DENY",
  "Referrer-Policy": "strict-origin-when-cross-origin",
  "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
  "Cross-Origin-Opener-Policy": "same-origin",
  "Cross-Origin-Resource-Policy": "same-origin",
};
const HTML_CSP =
  "default-src 'self'; img-src 'self' data:; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'; upgrade-insecure-requests";

function withSecurityHeaders(response) {
  const headers = new Headers(response.headers);
  for (const [name, value] of Object.entries(SECURITY_HEADERS)) {
    headers.set(name, value);
  }
  const contentType = headers.get("content-type") || "";
  if (contentType.includes("text/html")) {
    headers.set("Content-Security-Policy", HTML_CSP);
    headers.set("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0");
  }
  return new Response(response.body, { status: response.status, headers });
}

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
        return withSecurityHeaders(new Response(response.body, { status: response.status, headers }));
      }
      lastResponse = response;
      if (attempt === retries) {
        const headers = new Headers(lastResponse.headers);
        headers.set("X-Retry-Count", String(attempt));
        return withSecurityHeaders(new Response(lastResponse.body, { status: lastResponse.status, headers }));
      }
    } catch (err) {
      if (attempt === retries) throw err;
    }
    await new Promise((resolve) => setTimeout(resolve, RETRY_DELAY_MS * attempt));
  }
}

export default {
  async fetch(request, env) {
    return fetchWithRetry(env.ASSETS, request, MAX_RETRIES);
  },
};
