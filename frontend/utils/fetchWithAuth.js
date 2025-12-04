import { cookies } from 'next/headers';

export async function fetchWithAuth(input, init = {}) {
  const cookieStore = cookies();
  const accessToken = cookieStore.get('access_token')?.value;

  const headers = new Headers(init.headers || {});
  if (accessToken) {
    headers.set('Authorization', `Bearer ${accessToken}`);
  }

  return fetch(input, {
    ...init,
    headers,
  });
}
