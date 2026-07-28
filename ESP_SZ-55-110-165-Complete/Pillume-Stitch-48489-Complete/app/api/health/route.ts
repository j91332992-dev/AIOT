export function GET() {
  return Response.json({
    ok: true,
    service: "pillume-dashboard",
    time: new Date().toISOString(),
  });
}
