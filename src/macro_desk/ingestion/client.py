from __future__ import annotations

import logging
import urllib.error
import urllib.request
from dataclasses import dataclass

logger = logging.getLogger(__name__)

NON_RETRYABLE_STATUS = {401, 403, 404, 418, 429}


class FeedFetchError(Exception):
    """Raised when the official RSS feed cannot be retrieved legitimately."""


@dataclass(frozen=True)
class FeedClient:
    timeout_seconds: float
    user_agent: str

    def fetch(self, url: str) -> bytes:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": self.user_agent,
                "Accept": "application/rss+xml, application/xml, text/xml;q=0.9, */*;q=0.8",
            },
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                status = getattr(response, "status", 200)
                if status in NON_RETRYABLE_STATUS:
                    raise FeedFetchError(
                        "Refusing to continue after HTTP {} from {}".format(status, url)
                    )
                if status >= 400:
                    raise FeedFetchError("Feed request failed with HTTP {} from {}".format(status, url))
                return response.read()
        except FeedFetchError:
            raise
        except urllib.error.HTTPError as exc:
            logger.error("HTTP error fetching %s: %s", url, exc)
            raise FeedFetchError("HTTP error {} fetching {}".format(exc.code, url)) from exc
        except urllib.error.URLError as exc:
            logger.error("Network error fetching %s: %s", url, exc)
            raise FeedFetchError("Network error fetching {}".format(url)) from exc
        except TimeoutError as exc:
            logger.error("Timeout fetching %s after %ss", url, self.timeout_seconds)
            raise FeedFetchError("Timeout fetching {}".format(url)) from exc
