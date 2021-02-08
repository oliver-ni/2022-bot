from authlib.common.encoding import to_unicode
from authlib.integrations.httpx_client import AsyncOAuth1Client


class AsyncSchoologyOAuth1Client(AsyncOAuth1Client):
    async def _fetch_token(self, url, **kwargs):
        resp = await self.get(url, **kwargs)
        text = await resp.aread()
        token = self.parse_response_token(resp.status_code, to_unicode(text))
        self.token = token
        return token
