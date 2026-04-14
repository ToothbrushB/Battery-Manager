(function () {
    function csrfToken() {
        return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
    }

    async function sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    async function request(url, options = {}) {
        const {
            retries = 0,
            retryDelayMs = 250,
            expectedJson = true,
            ...fetchOptions
        } = options;

        const headers = {
            ...(fetchOptions.headers || {}),
            'X-CSRFToken': csrfToken(),
        };

        let attempt = 0;
        while (true) {
            try {
                const response = await fetch(url, { ...fetchOptions, headers });
                if (!response.ok && attempt < retries && response.status >= 500) {
                    attempt += 1;
                    await sleep(retryDelayMs * attempt);
                    continue;
                }

                if (!expectedJson) {
                    return { response, data: null };
                }

                let data = null;
                try {
                    data = await response.json();
                } catch (e) {
                    data = null;
                }

                return { response, data };
            } catch (error) {
                if (attempt >= retries) {
                    throw error;
                }
                attempt += 1;
                await sleep(retryDelayMs * attempt);
            }
        }
    }

    async function get(url, options = {}) {
        return request(url, { method: 'GET', ...options });
    }

    async function post(url, body, options = {}) {
        return request(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...(options.headers || {}),
            },
            body: body == null ? undefined : JSON.stringify(body),
            ...options,
        });
    }

    window.ApiClient = {
        request,
        get,
        post,
    };
})();
