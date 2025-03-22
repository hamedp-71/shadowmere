import logging

import requests
from django.core.cache import cache
from django.utils.timezone import now
from requests.exceptions import InvalidJSONError

from shadowmere import settings
from shadowmere.settings import CACHE_LOCATION_SECONDS

log = logging.getLogger("django")


class ShadowtestError(Exception):
    pass


def get_proxy_location(proxy_url):
    # Return the cached result if it exists
    # This should make t easier for the testing mechanism by avoiding double testing
    cache_key = f"proxy_location:{proxy_url}"
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        return cached_result

    r = requests.post(settings.SHADOWTEST_URL, data={"address": proxy_url})

    if r.status_code == 500:
        raise ShadowtestError()

    if r.status_code != 200:
        return None
    try:
        output = r.json()
        if "YourFuckingLocation" not in output:
            return None
    except InvalidJSONError:
        return None

    cache.set(cache_key, output, CACHE_LOCATION_SECONDS)
    return output


def update_proxy_status(proxy) -> None:
    try:
        ip_information = get_proxy_location(proxy_url=proxy.url)
    except ShadowtestError:
        log.error(f"Shadowtest is experiencing issues. Skipping updating {proxy.id}")
        return

    if ip_information:
        proxy.is_active = True
        proxy.ip_address = ip_information.get("YourFuckingIPAddress")
        proxy.last_active = now()
        proxy.times_check_succeeded = proxy.times_check_succeeded + 1
        if (
            proxy.location != ip_information.get("YourFuckingLocation")
            or proxy.location_country == ""
        ):
            proxy.location = ip_information.get("YourFuckingLocation")
            proxy.location_country_code = ip_information.get("YourFuckingCountryCode")
            proxy.location_country = ip_information.get("YourFuckingCountry")
    else:
        proxy.is_active = False
        proxy.location = "unknown"
        proxy.location_country = ""
        proxy.location_country_code = ""

    proxy.times_checked = proxy.times_checked + 1
