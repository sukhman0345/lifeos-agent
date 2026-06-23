import asyncio
import logging
from google.adk.models.google_llm import Gemini

logger = logging.getLogger(__name__)

class FallbackGemini(Gemini):
    async def generate_content_async(self, llm_request, stream=False):
        current_model = "gemini-2.5-flash"
        llm_request.model = current_model
        
        attempts = 0
        while True:
            try:
                chunks = []
                async for chunk in super().generate_content_async(llm_request, stream=stream):
                    chunks.append(chunk)
                
                for chunk in chunks:
                    yield chunk
                return
                
            except Exception as e:
                code = getattr(e, 'code', None)
                if code is None:
                    err_str = str(e).lower()
                    if "503" in err_str:
                        code = 503
                    elif "429" in err_str:
                        code = 429
                
                if current_model == "gemini-2.5-flash":
                    if code == 503:
                        if attempts < 1:  # wait 5 sec -> retry
                            attempts += 1
                            logger.warning(f"Got 503 error on gemini-2.5-flash. Waiting 5 seconds before retrying (attempt {attempts})...")
                            await asyncio.sleep(5)
                            continue
                        else:
                            # 503 persists -> fallback to gemini-2.0-flash
                            logger.warning("Got 503 error on gemini-2.5-flash after retry. Falling back to gemini-2.0-flash...")
                            current_model = "gemini-2.0-flash"
                            llm_request.model = current_model
                            attempts = 0
                            continue
                    elif code == 429:
                        # 429 -> switch to gemini-2.0-flash immediately
                        logger.warning("Got 429 error on gemini-2.5-flash. Switching to gemini-2.0-flash immediately...")
                        current_model = "gemini-2.0-flash"
                        llm_request.model = current_model
                        attempts = 0
                        continue
                
                raise e
