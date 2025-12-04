/** @type {import('next').NextConfig} */
const nextConfig = {
    env: {
        RUNTIME_ENV: process.env.RUNTIME_ENV || 'production',
        API_HOST: process.env.API_HOST,
        WS_HOST: process.env.WS_HOST,
        STRIPE_CLIENT_ID: process.env.STRIPE_CLIENT_ID,
        GOOGLE_CLIENT_ID: process.env.GOOGLE_CLIENT_ID,
        MS_CLIENT_ID: process.env.MS_CLIENT_ID,
        XERO_CLIENT_ID: process.env.XERO_CLIENT_ID,
        QUICKBOOKS_CLIENT_ID: process.env.QUICKBOOKS_CLIENT_ID,
        NEXT_PUBLIC_BASE_URL: process.env.NEXT_PUBLIC_BASE_URL,
        HOST_URL: process.env.HOST_URL,
    },
};

export default nextConfig;
