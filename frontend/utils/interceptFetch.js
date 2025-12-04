// lib/interceptFetch.js
// this will insert Authorization header to all the client fetch requests
import { getAccessTokenFromCookie } from "@/utils/cookie";

(function () {

    if (typeof window === 'undefined') return;

    const originalFetch = window.fetch;

    window.fetch = async function (input, init = {}) {
        const accessToken = getAccessTokenFromCookie();

        const headers = new Headers(init.headers || {});
        if (accessToken) {
            headers.set('Authorization', `Bearer ${accessToken}`);
        }

        return originalFetch(input, {
            ...init,
            headers,
        });
    };
})();
