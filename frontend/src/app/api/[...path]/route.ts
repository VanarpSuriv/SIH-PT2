import { NextRequest, NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

const HOP_BY_HOP_HEADERS = new Set([
  'host',
  'connection',
  'content-length',
  'accept-encoding',
  'transfer-encoding',
]);

async function proxyToBackend(request: NextRequest, params: { path: string[] }) {
  const backendBaseUrl = process.env.BACKEND_URL;
  if (!backendBaseUrl) {
    return NextResponse.json(
      { detail: 'Backend service unavailable: BACKEND_URL is not configured.' },
      { status: 503 }
    );
  }

  const backendPath = `/${params.path.join('/')}`;
  const url = new URL(backendPath + request.nextUrl.search, backendBaseUrl);

  const headers = new Headers();
  request.headers.forEach((value, key) => {
    if (HOP_BY_HOP_HEADERS.has(key)) {
      return;
    }
    headers.set(key, value);
  });

  let body: BodyInit | undefined;
  const hasBody = request.method !== 'GET' && request.method !== 'HEAD';
  if (hasBody) {
    const contentType = request.headers.get('content-type') || '';
    body = contentType.includes('multipart/form-data')
      ? await request.formData()
      : await request.arrayBuffer();
  }

  const upstream = await fetch(url, {
    method: request.method,
    headers,
    body,
    cache: 'no-store',
  });

  const upstreamBody = await upstream.arrayBuffer();
  return new NextResponse(upstreamBody, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers: { 'content-type': upstream.headers.get('content-type') || 'application/json' },
  });
}

export async function GET(request: NextRequest, { params }: { params: { path: string[] } }) {
  try {
    return await proxyToBackend(request, params);
  } catch {
    return NextResponse.json({ detail: 'Backend service request failed.' }, { status: 502 });
  }
}

export async function POST(request: NextRequest, { params }: { params: { path: string[] } }) {
  try {
    return await proxyToBackend(request, params);
  } catch {
    return NextResponse.json({ detail: 'Backend service request failed.' }, { status: 502 });
  }
}
