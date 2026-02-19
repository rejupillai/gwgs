import streamlit as st
import streamlit.components.v1 as components
from google import genai
from google.genai import types

# Initialize the Gemini Client
client = genai.Client()

st.set_page_config(page_title="Gemini Grounding & Citations", layout="centered")
st.title("🔍 Gemini Grounding with Citations")

def add_inline_citations(response):
    """
    Extracts grounding chunks and safely inserts clickable Markdown 
    citations into the text using reverse byte-index insertion.
    """
    if not response.candidates or not response.candidates[0].grounding_metadata:
        return response.text
        
    metadata = response.candidates[0].grounding_metadata
    supports = metadata.grounding_supports
    chunks = metadata.grounding_chunks
    
    if not supports or not chunks:
        return response.text

    # FIX 1: Convert text to UTF-8 bytes because API indices are byte-based
    text_bytes = response.text.encode('utf-8')

    # Sort supports by end_index in descending order
    sorted_supports = sorted(supports, key=lambda s: s.segment.end_index, reverse=True)

    for support in sorted_supports:
        end_index = support.segment.end_index
        
        if support.grounding_chunk_indices:
            citation_links = []
            for i in support.grounding_chunk_indices:
                if i < len(chunks):
                    uri = chunks[i].web.uri
                    
                    # FIX 2: Replace spaces with %20 to prevent Markdown parser breakage
                    safe_uri = uri.replace(" ", "%20")
                    citation_links.append(f"[[{i + 1}]]({safe_uri})")
            
            if citation_links:
                citation_string = " " + " ".join(citation_links)
                
                # Slice and insert using the byte array instead of the string
                text_bytes = text_bytes[:end_index] + citation_string.encode('utf-8') + text_bytes[end_index:]

    # Decode back to a Python string
    return text_bytes.decode('utf-8')

# UI Input
user_prompt = st.text_input("Ask a question about recent events:", placeholder="What is the weather in Palo Alto today?")

if st.button("Generate Answer") and user_prompt:
    with st.spinner("Searching the web and generating response..."):
        try:
            search_tool = types.Tool(google_search=types.GoogleSearch())
            config = types.GenerateContentConfig(
                tools=[search_tool],
                temperature=0.0 
            )

            response = client.models.generate_content(
                model="gemini-2.5-flash", 
                contents=user_prompt,
                config=config
            )

            # Process and Display the Text with Inline Citations
            cited_text = add_inline_citations(response)
            
            st.markdown("### Answer")
            st.markdown(cited_text)

            st.divider()

            # Display the Search Entry Point (Strict Compliance Requirement)
            metadata = response.candidates[0].grounding_metadata
            if metadata and metadata.search_entry_point:
                rendered_html = metadata.search_entry_point.rendered_content
                
                st.markdown("### Explore Further")
                components.html(rendered_html, height=100)
                
            # Optional: Display a bibliography of sources at the bottom
            if metadata and metadata.grounding_chunks:
                with st.expander("View Source Bibliography"):
                    for i, chunk in enumerate(metadata.grounding_chunks):
                        safe_chunk_uri = chunk.web.uri.replace(" ", "%20")
                        st.markdown(f"**[{i + 1}]** [{chunk.web.title}]({safe_chunk_uri})")

        except Exception as e:
            st.error(f"An error occurred: {e}")