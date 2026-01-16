// Helper to read cookie value
// Utility: Get cookie value
export function getCookie(name) {
    const match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
    return match ? match[2] : null;
}

// Utility: Set cookie value
export function setCookie(name, value, days = 30) {
    const expires = new Date(Date.now() + days * 864e5).toUTCString();
    document.cookie = `${name}=${value}; expires=${expires}; path=/`;
}

export function removeCookie(name, path = "/") {
    if (!name) return;

    // Build cookie string
    let cookie = `${encodeURIComponent(name)}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=${path};`;

    document.cookie = cookie;
}

export function getAccessTokenFromCookie() {
    const cookies = document.cookie.split(';');
    for (const cookie of cookies) {
        const [name, value] = cookie.trim().split('=');
        if (name === 'access_token') {
            return decodeURIComponent(value);
        }
    }
    return null;
}

export function getSessionIdFromCookie() {
    const cookies = document.cookie.split(';');
    for (const cookie of cookies) {
        const [name, value] = cookie.trim().split('=');
        if (name === 'session_id') {
            return decodeURIComponent(value);
        }
    }
    return null;
}

export function setSessionCookies(access_token, session_id, expiresInDays = 30) {
    setCookie('access_token', access_token, expiresInDays);
    setCookie('session_id', session_id, expiresInDays);
}

export function clearSessionCookies() {
    removeCookie('access_token', '/');
    removeCookie('session_id', '/');
}