import { clientFetch } from "@/lib/client-fetch";

export type Profile = {
  user_id: number;
  email: string;
  username: string;
  role: string;
  package: string;
  credits: number;
};

export const fetchProfile = async (): Promise<Profile> => {
  const res = await clientFetch("/api/profile");
  if (!res.ok) throw new Error("Failed to fetch profile");

  return res.json();
};