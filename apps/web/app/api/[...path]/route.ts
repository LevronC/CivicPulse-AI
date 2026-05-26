import { NextRequest } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const BACKEND_URL = (
  process.env.API_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://localhost:8000"
).replace(/\/$/, "");

function buildTargetUrl(path: string[], search: string): string {
  const suffix = path.join("/");
  const qs = search ? `?${search}` : "";
  return `${BACKEND_URL}/${suffix}${qs}`;
}

async function proxy(req: NextRequest, path: string[]): Promise<Response> {
  const target = buildTargetUrl(path, req.nextUrl.searchParams.toString());
  const headers = new Headers();

  const contentType = req.headers.get("content-type");
  if (contentType) {
    headers.set("content-type", contentType);
  }

  const apiKey = process.env.API_KEY;
  if (apiKey && !req.headers.get("x-api-key")) {
    headers.set("x-api-key", apiKey);
  }

  const accept = req.headers.get("accept");
  if (accept) {
    headers.set("accept", accept);
  }

  const init: RequestInit & { duplex?: "half" } = {
    method: req.method,
    headers,
    cache: "no-store",
  };

  if (req.method !== "GET" && req.method !== "HEAD") {
    init.body = req.body;
    init.duplex = "half";
  }

  const upstream = await fetch(target, init);

  return new Response(upstream.body, {
    status: upstream.status,
    headers: {
      "content-type": upstream.headers.get("content-type") || "application/json",
      "cache-control": "no-cache",
    },
  });
}

type RouteContext = { params: { path: string[] } };

export async function GET(req: NextRequest, ctx: RouteContext) {
  return proxy(req, ctx.params.path);
}

export async function POST(req: NextRequest, ctx: RouteContext) {
  return proxy(req, ctx.params.path);
}

export async function PUT(req: NextRequest, ctx: RouteContext) {
  return proxy(req, ctx.params.path);
}

export async function PATCH(req: NextRequest, ctx: RouteContext) {
  return proxy(req, ctx.params.path);
}

export async function DELETE(req: NextRequest, ctx: RouteContext) {
  return proxy(req, ctx.params.path);
}
