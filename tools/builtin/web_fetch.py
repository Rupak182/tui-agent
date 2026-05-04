


from urllib.parse import urlparse

import httpx
from pydantic import BaseModel, Field
from tools.base import Tool, ToolInvocation, ToolKind, ToolKind, ToolResult


class WebFetchParams(BaseModel):
    url: str = Field(..., description="URL to fetch (must be http:// or https://)")
    timeout: int = Field(
        30,
        ge=5,
        le=120,
        description="Request timeout in seconds (default: 120)",
    )
# Normal fetched is blocked many a times
class WebFetchTool(Tool):
    name = "web_fetch"
    kind = ToolKind.NETWORK
    description = "Fetch content from a URL. Returns the response body as text"
    schema= WebFetchParams


    async def execute(self, invocation:ToolInvocation)->ToolResult:
        params= WebFetchParams(**invocation.params)
        parsed =urlparse(params.url)

        if not parsed.scheme in ("http", "https"):
            return ToolResult.error_result("Invalid URL scheme. Only http:// and https:// are allowed.")
        

        try:
            async with httpx.AsyncClient(timeout=params.timeout, follow_redirects=True) as client:
                response = await client.get(params.url)
                response.raise_for_status()
                text = response.text
        except httpx.HTTPStatusError as e:
                return ToolResult.error_result(f"HTTP {e.response.status_code}: {e.response.reason_phrase}")
        
        except httpx.TimeoutException:
            return ToolResult.error_result(f"Request timed out after {params.timeout} seconds")
        except Exception as e:
            return ToolResult.error_result(
                f"HTTP {e.response.status_code}: {e.response.reason_phrase}",
            )
        
        if len(text)>1024*100:
            text=text[:1024*100] + "\n\n[Content truncated]"

        
        return ToolResult.success_result(
            text,
            metadata={
                "status_code":  response.status_code,
                "content_length": len(response.content),
            },
        )        
       

        

    
