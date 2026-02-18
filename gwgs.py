import json
import requests
from google import genai
from google.genai import types

# 1. Setup Client
# PRO TIP: Use an environment variable for security: os.environ.get("GOOGLE_API_KEY")
API_KEY = "AIzaSyAyWSzpjCqlFaXJJJoZgIaJcX15WuamhWo" 
client = genai.Client(api_key=API_KEY)

# 2. Configure Grounding
grounding_tool = types.Tool(
    google_search=types.GoogleSearch()
)

config = types.GenerateContentConfig(
    tools=[grounding_tool],
    response_modalities=["TEXT"]
)

# --- Helper Function to Resolve Redirects ---
def get_actual_url(redirect_url):
    try:
        # Using a HEAD request to follow redirects efficiently
        response = requests.head(redirect_url, allow_redirects=True, timeout=5)
        return response.url
    except Exception:
        return redirect_url

# 3. Generate Content
user_prompt = "weather in Palo Alto today"
response = client.models.generate_content(
    model="gemini-2.5-flash", # Updated to the standard model name format
    contents=user_prompt,
    config=config,
)

# 4. Extract Response, Metadata, and Resolve URLs mapping
grounded_segments = []
ai_answer = response.text

if response.candidates and response.candidates[0].grounding_metadata:
    metadata = response.candidates[0].grounding_metadata
    chunks = metadata.grounding_chunks
    supports = metadata.grounding_supports
    
    # Loop through the supports to get the text snippet and its chunk indices
    if supports and chunks:
        for support in supports:
            # Extract the actual text snippet the AI generated
            snippet_text = support.segment.text
            
            segment_sources = []
            # Use the indices to find the matching sources for this specific snippet
            for idx in support.grounding_chunk_indices:
                chunk = chunks[idx]
                if chunk.web:
                    clean_url = get_actual_url(chunk.web.uri)
                    segment_sources.append({
                        "title": chunk.web.title,
                        "url": clean_url
                    })
            
            # Group the snippet with its specific sources
            grounded_segments.append({
                "snippet": snippet_text,
                "sources": segment_sources
            })

# 5. Final Output Assembly
output_json = {
    "full_answer": ai_answer,
    "grounding_details": grounded_segments
}

print(json.dumps(output_json, indent=2))