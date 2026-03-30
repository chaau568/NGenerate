import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { serverFetch } from "@/lib/server-api";

type Context = {
  params: Promise<{ characterId: string }>;
};

export async function DELETE(request: Request, context: Context) {
  const { characterId } = await context.params;

  const cookieStore = await cookies();
  const accessToken = cookieStore.get("access")?.value;

  if (!accessToken) {
    return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });
  }

  const { res } = await serverFetch(
    `/session/character/${characterId}/`,
    {
      method: "DELETE",
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    }
  );

  if (res.status === 204) {
    return new NextResponse(null, { status: 204 });
  }

  return NextResponse.json({}, { status: res.status });
}