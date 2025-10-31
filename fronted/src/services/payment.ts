const API_BASE =
    import.meta.env.VITE_API_BASE_URL?.replace(/\/+$/, '') ||
    (window.location.origin.includes('5173')
        ? 'http://localhost:8000' // dev default
        : window.location.origin);

const API_PREFIX = '/v1';

async function http<T>(path: string, init?: RequestInit): Promise<T> {
    const res = await fetch(`${API_BASE}${API_PREFIX}${path}`, {
        headers: {
            'Content-Type': 'application/json',
            // Optional: if you set API_KEY in backend
            ...(import.meta.env.VITE_API_KEY ? {'x-api-key': import.meta.env.VITE_API_KEY} : {}),
        },
        ...init,
    });
    if (!res.ok) {
        const text = await res.text();
        throw new Error(`API ${res.status}: ${text}`);
    }
    return res.json() as Promise<T>;
}
