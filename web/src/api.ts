import type { ReviewDetail, ReviewListItem } from "./types";

const API_BASE =
  (import.meta.env.VITE_API_BASE as string | undefined)?.replace(/\/$/, "") ??
  (import.meta.env.DEV ? "http://127.0.0.1:8000" : "");

async function get<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return (await response.json()) as T;
}

export function fetchReviews(): Promise<ReviewListItem[]> {
  return get<ReviewListItem[]>("/reviews?limit=50");
}

export function fetchReview(id: string): Promise<ReviewDetail> {
  return get<ReviewDetail>(`/reviews/${id}`);
}
