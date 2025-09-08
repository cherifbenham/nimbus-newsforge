interface ApiServiceConfig {
    url: {
        API_URL: string;
    };
}

const getApiUrl = () => {
    if (process.env.NODE_ENV === 'development') {
        return import.meta.env.VITE_API_URL || 'http://localhost:3000/api'; //Use dev URL in dev env
    } else {
        // Get current domain in production
        const protocol = window.location.protocol;
        const host = window.location.host;
        return `${protocol}//${host}/api`;  //Append /api to production URL
    }
};

const config: ApiServiceConfig = {
    url: {
        API_URL: getApiUrl(),
    }
};



export default config;