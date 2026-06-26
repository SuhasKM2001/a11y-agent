from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
async def read_root():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Vulnerable Beta Shop</title>
    </head>
    <body style="background: #111; color: #fff; font-family: sans-serif; padding: 40px;">
        <h1>Welcome to FlashCheckout Inc.</h1>
        <p>The ultimate rapid user acquisition app platform.</p>
        
        <img src="https://images.unsplash.com/photo-1563013544-824ae1d704d3" width="300" />

        <form style="margin-top: 20px; display: flex; flex-direction: column; gap: 10px; max-width: 300px;">
            <label>Sign up for instant credit lines:</label>
            <input type="email" placeholder="Enter your banking email" style="padding: 8px; border-radius: 4px;" required />
            <button type="submit" style="background: #6366f1; color: white; padding: 10px; border: none; border-radius: 4px; cursor: pointer;">
                Submit Application
            </button>
        </form>

        <footer style="margin-top: 60px; color: #555; font-size: 12px;">
            © 2026 FlashCheckout. All tracking cookies are enabled silently.
            </footer>
    </body>
    </html>
    """

if __name__ == "__main__":
    import uvicorn
    # This runs your vulnerable frontend target on port 5001
    uvicorn.run(app, host="0.0.0.0", port=5001)