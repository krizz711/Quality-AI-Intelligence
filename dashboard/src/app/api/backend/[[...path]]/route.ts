const BACKEND_URL = (process.env.API_URL || 'http://127.0.0.1:8000').replace(
  'http://localhost:8000',
  'http://127.0.0.1:8000'
);
const API_AUTH_KEY = process.env.API_AUTH_KEY || '';

function getTargetUrl(pathSegments: string[] | undefined, search: string) {
  const path = `/${(pathSegments || []).map(encodeURIComponent).join('/')}`;
  return new URL(`${path}${search}`, BACKEND_URL);
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

  if (API_AUTH_KEY) {
    headers.set('x-api-key', API_AUTH_KEY);
  }

  const body = method === 'GET' || method === 'HEAD' ? undefined : await request.arrayBuffer();

  // Add a timeout and error logging to help debug proxy issues.
  // Analysis endpoints can run long (statistics + AI narrative + alert dispatch).
  const controller = new AbortController();
  const timeoutMs = 90000; // 90s
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(targetUrl, {
      method,
      headers,
      body,
      redirect: 'manual',
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    return new Response(response.body, {
      status: response.status,
      headers: response.headers,
    });
  } catch (err) {
    clearTimeout(timeoutId);
    // Log detailed error server-side for debugging
    // eslint-disable-next-line no-console
    console.error('proxyRequest error fetching', targetUrl.toString(), err);
    const message = err instanceof Error ? err.message : String(err);
    return new Response(message, {
      status: 502,
      headers: { 'content-type': 'text/plain' },
    });
  }
}

export const GET = proxyRequest;
export const POST = proxyRequest;
export const PATCH = proxyRequest;
export const PUT = proxyRequest;
export const DELETE = proxyRequest;
export const HEAD = proxyRequest;
export const OPTIONS = proxyRequest;
