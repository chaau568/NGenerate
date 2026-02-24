export async function clientFetch(
  url: string,
  options: RequestInit = {}
) {
  const makeRequest = () =>
    fetch(url, {
      ...options,
      credentials: "include",
    });

  let res = await makeRequest();

  if (res.status === 401) {
    const refreshRes = await fetch("/api/refresh", {
      method: "POST",
      credentials: "include",
    });

    if (!refreshRes.ok) {
      return refreshRes;
    }

    res = await makeRequest();
  }

  return res;
}