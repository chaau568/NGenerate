export async function clientFetch(
  url: string,
  options: RequestInit = {}
) {
  let res = await fetch(url, {
    ...options,
    credentials: "include",
  });

  if (res.status === 401) {
    await fetch("/api/refresh", {
      method: "POST",
    });

    res = await fetch(url, {
      ...options,
      credentials: "include",
    });
  }

  return res;
}