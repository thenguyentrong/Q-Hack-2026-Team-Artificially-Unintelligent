import asyncio
import httpx
import json

async def test_api():
    input_data = {
        "schema_version": "1.0",
        "company_id": 1,
        "company_name": "company_name",
        "RM_id": "RM_Id",
        "RM_sku": "RM-C56-citric-acid-d55c874f"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://127.0.0.1:8000/api/v1/preprocess", 
            json=input_data,
            timeout=30.0
        )
        print(f"Status Code: {response.status_code}")
        print(json.dumps(response.json(), indent=2))

if __name__ == "__main__":
    asyncio.run(test_api())
