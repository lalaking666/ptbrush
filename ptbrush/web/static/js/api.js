async function request(method, path, body) {
    const init = { method, headers: { Accept: 'application/json' } };
    if (body !== undefined) {
        init.headers['Content-Type'] = 'application/json';
        init.body = JSON.stringify(body);
    }
    const res = await fetch(path, init);
    if (res.status === 401) {
        const from = encodeURIComponent(location.pathname + location.search);
        window.location.href = `/login?from=${from}`;
        throw new Error('未登录');
    }
    const ct = res.headers.get('content-type') || '';
    const data = ct.includes('application/json') ? await res.json() : null;
    if (!res.ok) {
        const err = new Error(data?.error || data?.message || `请求失败 (${res.status})`);
        err.status = res.status;
        err.details = data?.details;
        throw err;
    }
    return data;
}

export const api = {
    get: (p) => request('GET', p),
    put: (p, b) => request('PUT', p, b),
    post: (p, b) => request('POST', p, b),
    delete: (p) => request('DELETE', p),
};
