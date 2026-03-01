export async function serverFetch(
  endpoint: string,
  options: RequestInit & { raw?: boolean } = {}
) {
  const { raw, ...fetchOptions } = options;

  const isFormData = fetchOptions.body instanceof FormData;

  const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;

  if (!baseUrl) {
    throw new Error("NEXT_PUBLIC_API_BASE_URL is not defined");
  }

  const res = await fetch(`${baseUrl}${endpoint}`, {
    ...fetchOptions,
    headers: {
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
      ...(fetchOptions.headers || {}),
    },
  });

  if (raw) {
    return { res };
  }

  let data = null;

  try {
    data = await res.json();
  } catch {
    data = null;
  }

  return { res, data };
}