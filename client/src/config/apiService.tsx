interface ApiServiceConfig {
    url: {
        API_URL: string;
    };
}

const getApiUrl = () => {
    // Prefer explicit override if provided
    if (import.meta.env.VITE_API_URL) {
        return import.meta.env.VITE_API_URL as string;
    }

    // Vite dev server hint
    if (import.meta.env.DEV) {
        // Default dev backend if none provided
        return 'http://localhost:5001/api';
    }

    // Production: same-origin /api
    const protocol = window.location.protocol;
    const host = window.location.host;
    return `${protocol}//${host}/api`;
};

const config: ApiServiceConfig = {
    url: {
        API_URL: getApiUrl(),
    }
};



export default config;
