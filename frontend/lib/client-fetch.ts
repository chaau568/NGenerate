export async function clientFetch(
  url: string,
  options: RequestInit = {}
) {
  let res = await fetch(url, {
    ...options,
    credentials: "include",
  });

  if (res.status === 401) {
    const refreshRes = await fetch("/api/refresh", {
      method: "POST",
      credentials: "include",
    });

    if (!refreshRes.ok) {
      return refreshRes; 
    }

    res = await fetch(url, {
      ...options,
      credentials: "include",
    });
  }

  return res;
}