export function readableSourceUrl(
  url: string | null | undefined,
  postId?: string | null
): string | null {
  if (!url) return null;

  const hnItemId = hackerNewsItemId(url, postId);
  if (hnItemId) return `https://news.ycombinator.com/item?id=${hnItemId}`;

  return url;
}

function hackerNewsItemId(url: string, postId?: string | null): string | null {
  try {
    const parsed = new URL(url);
    if (parsed.hostname !== 'hn.algolia.com') return null;
  } catch {
    return null;
  }

  const rawId = postId?.includes(':')
    ? postId.split(':').pop()
    : postId;
  const id = rawId?.trim();

  return id && /^\d+$/.test(id) ? id : null;
}
