export async function serverFetch(
  endpoint: string,
  options: RequestInit = {}
) {
  const res = await fetch(
    `${process.env.NEXT_PUBLIC_API_BASE_URL}${endpoint}`,
    {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {}),
      },
    }
  );

  const data = await res.json();

  return { res, data };
}