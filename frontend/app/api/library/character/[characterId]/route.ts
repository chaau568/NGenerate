import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { serverFetch } from "@/lib/server-api";

type Context = {
  params: { characterId: string };
};

export async function DELETE(request: Request, context: Context) {
  const { characterId } = context.params;

  const cookieStore = await cookies();
  const accessToken = cookieStore.get("access")?.value;

  if (!accessToken) {
    return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });
  }

  const { res } = await serverFetch(
    `/character/${characterId}/`,
    {
      method: "DELETE",
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    }
  );

  return NextResponse.json({}, { status: res.status });
}