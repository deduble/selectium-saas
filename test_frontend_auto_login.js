#!/usr/bin/env node
/**
 * Test script to verify frontend auto-login functionality
 */

const axios = require('axios');

const FRONTEND_URL = 'http://localhost:3000';
const API_URL = 'http://localhost:8000';

async function testFrontendEnvironment() {
    console.log('🧪 Testing Frontend Auto-Login Environment');
    console.log('=====================================');
    
    try {
        // Test 1: Check if frontend is serving pages
        console.log('\n1. Testing frontend accessibility...');
        const frontendResponse = await axios.get(FRONTEND_URL, { timeout: 5000 });
        console.log('✅ Frontend is accessible');
        
        // Test 2: Check if we can find environment variable references in the page
        const pageContent = frontendResponse.data;
        if (pageContent.includes('NEXT_PUBLIC_DEV_AUTO_LOGIN')) {
            console.log('✅ Environment variable reference found in page');
        } else {
            console.log('⚠️  Environment variable reference not found in initial page');
        }
        
        // Test 3: Test the backend endpoint directly (should work)
        console.log('\n2. Testing backend dev-login endpoint...');
        const backendResponse = await axios.post(`${API_URL}/api/v1/auth/dev/login`);
        if (backendResponse.status === 200 && backendResponse.data.access_token) {
            console.log('✅ Backend dev-login endpoint working');
            console.log(`   User: ${backendResponse.data.user.email}`);
            console.log(`   Tier: ${backendResponse.data.user.subscription_tier}`);
        } else {
            console.log('❌ Backend dev-login endpoint failed');
        }
        
        // Test 4: Check Next.js environment
        console.log('\n3. Checking Next.js environment...');
        try {
            const healthResponse = await axios.get(`${FRONTEND_URL}/api/health`);
            console.log('✅ Next.js API routes working');
        } catch (error) {
            console.log('⚠️  Next.js API routes may not be working');
        }
        
        console.log('\n📋 Summary:');
        console.log('- Backend: Working ✅');
        console.log('- Frontend: Accessible ✅');
        console.log('- Auto-login issue: Likely environment variable or client-side error');
        
        console.log('\n🔍 Next steps:');
        console.log('1. Check browser console for detailed error logs');
        console.log('2. Verify NEXT_PUBLIC_DEV_AUTO_LOGIN is set to "true"');
        console.log('3. Verify NODE_ENV is set to "development"');
        console.log('4. Check for any React/Next.js errors preventing the useEffect from running');
        
    } catch (error) {
        console.error('❌ Test failed:', error.message);
        if (error.response) {
            console.error('   Status:', error.response.status);
            console.error('   Data:', error.response.data);
        }
    }
}

// Add a simple function to test just the dev login endpoint
async function testDevLoginEndpoint() {
    console.log('\n🔧 Direct Dev Login Test');
    console.log('========================');
    
    try {
        const response = await axios.post(`${API_URL}/api/v1/auth/dev/login`);
        console.log('✅ Dev login successful!');
        console.log('Response:');
        console.log(`  - Token: ${response.data.access_token.substring(0, 20)}...`);
        console.log(`  - User: ${response.data.user.email}`);
        console.log(`  - Subscription: ${response.data.user.subscription_tier}`);
        console.log(`  - Compute Units: ${response.data.user.compute_units_remaining}`);
        
        // Test using the token
        console.log('\n🔐 Testing token with protected endpoint...');
        const userResponse = await axios.get(`${API_URL}/api/v1/auth/me`, {
            headers: {
                'Authorization': `Bearer ${response.data.access_token}`
            }
        });
        
        if (userResponse.status === 200) {
            console.log('✅ Token works with protected endpoints');
            console.log(`   Retrieved user: ${userResponse.data.email}`);
        }
        
    } catch (error) {
        console.error('❌ Dev login test failed:', error.message);
        if (error.response) {
            console.error('   Status:', error.response.status);
            console.error('   Data:', error.response.data);
        }
    }
}

async function main() {
    await testDevLoginEndpoint();
    await testFrontendEnvironment();
}

if (require.main === module) {
    main();
}