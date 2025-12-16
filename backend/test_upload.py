"""
Simple test script to verify upload endpoint works
Run this while your backend is running to test the upload
"""

import requests
import os

# Configuration
API_URL = "http://localhost:5001/systematic-review/upload"
TEST_PDF = "test.pdf"  # Put a test PDF in the same folder as this script

def test_upload():
    print("=" * 60)
    print("Testing Upload Endpoint")
    print("=" * 60)
    
    # Check if test file exists
    if not os.path.exists(TEST_PDF):
        print(f"❌ Test PDF not found: {TEST_PDF}")
        print(f"Please place a PDF file named '{TEST_PDF}' in this folder")
        return
    
    print(f"✓ Found test file: {TEST_PDF}")
    
    # Prepare the upload
    session_id = "test_session_123"
    
    with open(TEST_PDF, 'rb') as f:
        files = {'files': (TEST_PDF, f, 'application/pdf')}
        data = {'session_id': session_id}
        
        print(f"\n📤 Uploading to: {API_URL}")
        print(f"Session ID: {session_id}")
        
        try:
            response = requests.post(API_URL, files=files, data=data, timeout=120)
            
            print(f"\n📥 Response Status: {response.status_code}")
            print(f"Response Headers: {response.headers}")
            print(f"\nResponse Body:")
            print(response.text)
            
            if response.status_code == 200:
                print("\n✅ Upload successful!")
                result = response.json()
                print(f"\n📊 Results:")
                print(f"  - Papers processed: {result.get('total_papers')}")
                print(f"  - Chunks: {result.get('token_usage', {}).get('total_chunks')}")
                print(f"  - Tokens: {result.get('token_usage', {}).get('embedding_tokens')}")
                print(f"  - Cost: ${result.get('token_usage', {}).get('embedding_cost_usd')}")
            else:
                print(f"\n❌ Upload failed: {response.status_code}")
                
        except requests.exceptions.Timeout:
            print("\n❌ Request timed out (>120 seconds)")
        except Exception as e:
            print(f"\n❌ Error: {e}")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    test_upload()