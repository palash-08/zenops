import httpx


class OpenClawError(Exception):
    # Raised when communication with an OpenClaw Gateway fails.
    pass


class OpenClawClient:
    
   # Handles all HTTP communication with an OpenClaw Gateway.

    

    def __init__(self, gateway_url: str, gateway_token: str):
        self.gateway_url = gateway_url.rstrip("/")

        self.client = httpx.AsyncClient(
            base_url=self.gateway_url,
            timeout=30.0,
            headers={
                "Authorization": f"Bearer {gateway_token}",
                "Content-Type": "application/json",
            },
        )

    async def create_response(self, payload: dict) -> dict:
        
       # Sends a request to the OpenClaw Responses API.

        # Args:
          #  payload: JSON payload expected by POST /v1/responses

        # Returns:
        #    Parsed JSON response from the Gateway.
        

        try:
            response = await self.client.post(
                "/v1/responses",
                json=payload,
            )

            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            if e.response.status_code in (401, 403):
                raise OpenClawError("Authentication with OpenClaw Gateway failed.")

            raise OpenClawError(
                f"Gateway returned HTTP {e.response.status_code}: {e.response.text}"
            )

        except httpx.ConnectError:
            raise OpenClawError(
                "Unable to connect to the OpenClaw Gateway."
            )

        except httpx.TimeoutException:
            raise OpenClawError(
                "The request to the OpenClaw Gateway timed out."
            )

        except httpx.RequestError as e:
            raise OpenClawError(
                f"Failed to communicate with the OpenClaw Gateway: {e}"
            )

    async def close(self):
        # Closes the underlying HTTP client.
        await self.client.aclose()