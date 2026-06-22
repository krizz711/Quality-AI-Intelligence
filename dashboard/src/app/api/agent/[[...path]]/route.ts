// Server-side proxy from the dashboard to the ADK agent service (adk_agent.web:app).
// Keeps the agent call same-origin (no CORS) and lets the agent URL be configured.
const AGENT_URL = (process.env.AGENT_URL || 'http://127.0.0.1:8090').replace(
  'http://localhost:',
  'http://127.0.0.1:'
);

function getTargetUrl(pathSegments: string[] | undefined, search: string) {
  const path = `/agent/${(pathSegments || []).map(encodeURIComponent).join('/')}`;
  return new URL(`${path}${search}`, AGENT_URL);
}

async function proxyRequest(
  request: Request,
  context: { params: Promise<{ path?: string[] }> }
) {
  const params = await context.params;
  const targetUrl = getTargetUrl(params?.path, new URL(request.url).search);
  const method = request.method.toUpperCase();
  const headers = new Headers(request.headers);
  headers.delete('host');
  headers.delete('content-length');
  headers.delete('connection');

  const body = method === 'GET' || method === 'HEAD' ? undefined : await request.arrayBuffer();

  // The /agent/chat endpoint runs the LLM multi-agent system, so allow time.
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 120000);
  try {
    const response = await fetch(targetUrl, { method, headers, body, signal: controller.signal });
    clearTimeout(timeoutId);
    return new Response(response.body, { status: response.status, headers: response.headers });
  } catch (err) {
    clearTimeout(timeoutId);
    const message = err instanceof Error ? err.message : String(err);
    // eslint-disable-next-line no-console
    console.error('agent proxy error', targetUrl.toString(), message);
    return new Response(
      JSON.stringify({ error: `Agent service unreachable at ${AGENT_URL}. Start it with: uvicorn adk_agent.web:app --port 8090` }),
      { status: 502, headers: { 'content-type': 'application/json' } }
    );
  }
}

export const GET = proxyRequest;
export const POST = proxyRequest;
