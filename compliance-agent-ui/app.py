import os
import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
from openai import AsyncOpenAI
from dotenv import load_dotenv

# Load secret environment keys from your local hidden .env file
load_dotenv()

app = FastAPI()

# Enable CORS so your vanilla index.html can talk to port 8888 safely
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ScanRequest(BaseModel):
    url: str

# Point explicitly to the live GMI Cloud production endpoint
ai_client = AsyncOpenAI(
    base_url="https://api.gmi-serving.com/v1",
    api_key=os.getenv("GMI_API_KEY")
)

@app.post("/api/scan")
async def scan_website(request: ScanRequest):
    target_url = request.url
    
    if not target_url.startswith("http"):
        target_url = f"http://{target_url}"

    # 1. LIVE LAYOUT CRAWL: Safely fetch the HTML layout of the target site
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(target_url, timeout=5.0)
            html_content = response.text
    except Exception as e:
        return {"error": f"Could not reach or scan target site: {str(e)}"}

    # 2. CONSTRUCT SYSTEM CRITERIA FOR THE OPEN-WEIGHT ENGINE
    system_prompt = (
        "You are an expert Web Regulatory & Accessibility Compliance Agent. Analyze the provided HTML source code "
        "for violations against GDPR, CCPA, and ADA/WCAG 2.2 rules. You must output your analysis in a strict JSON object "
        "matching the user schema keys perfectly."
    )
    
    user_prompt = f"""
    Analyze this website's layout code and pinpoint compliance flaws.
    Target URL: {target_url}

    HTML Code Content:
    \"\"\"
    {html_content}
    \"\"\"

    Return a valid JSON object matching this structural layout exactly:
    {{
        "url": "{target_url}",
        "score": 100,
        "status": "Compliant" or "Moderate Risk" or "Critical Risk",
        "critical_count": 0,
        "warning_count": 0,
        "regulations": [
            {{"name": "GDPR", "region": "Europe", "status": "pass" or "fail", "text": "COMPLIANT" or "FAIL"}},
            {{"name": "ADA / WCAG 2.2", "region": "Global", "status": "pass" or "fail", "text": "COMPLIANT" or "FAIL"}},
            {{"name": "CCPA", "region": "California", "status": "pass" or "warning", "text": "COMPLIANT" or "WARNING"}},
            {{"name": "DPDP", "region": "India", "status": "pass" or "fail", "text": "COMPLIANT" or "FAIL"}}
        ],
        "violations": [
            {{
                "id": 1,
                "severity": "CRITICAL" or "WARNING",
                "title": "Short descriptive title of the violation",
                "impact": "The regulatory act it violates",
                "finding": "Explain exactly what rule was tripped in the HTML markup",
                "fix": "Provide the exact replacement HTML/CSS code snippet fix"
            }}
        ]
    }}
    """

    try:
        # 3. EXECUTE INFERENCE VIA GMI CLOUD HIGH-THROUGHPUT CLUSTER
        completion = await ai_client.chat.completions.create(
            model="meta-llama/Llama-3.3-70B-Instruct",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.2
        )
        
        # Parse the JSON string sent back by Llama 3.3 straight to your frontend
        return json.loads(completion.choices[0].message.content)

    except Exception as e:
        print(f"GMI Pipeline Fallback Triggered: {str(e)}")
        return {
            "url": target_url,
            "score": 50,
            "status": "Inference Error",
            "critical_count": 1,
            "warning_count": 0,
            "regulations": [
                {"name": "ADA / WCAG 2.2", "region": "Global", "status": "fail", "text": "GMI INFERENCE TIMEOUT"}
            ],
            "violations": [
                {
                    "id": 1,
                    "severity": "CRITICAL",
                    "title": "GMI Cluster Connection Lost",
                    "impact": "System Architecture",
                    "finding": f"Failed to successfully get analysis from the GMI endpoint. Raw text error: {str(e)}",
                    "fix": "Verify your GMI_API_KEY environment variable setup."
                }
            ]
        }

if __name__ == "__main__":
    import uvicorn
    # FORCED UNCOMMON PORT FOR HACKATHON SAFETY
    uvicorn.run(app, host="0.0.0.0", port=8888)