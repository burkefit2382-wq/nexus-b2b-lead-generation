const MAX_RETRIES = 3;
const RETRY_DELAY_MS = 150;

async function fetchWithRetry(binding, request, retries) {
  for (let attempt = 1; attempt <= retries; attempt++) {
    try {
      const response = await binding.fetch(request.clone());
      if (response.ok || response.status < 500) {
        return response;
      }
      if (attempt === retries) return response;
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
