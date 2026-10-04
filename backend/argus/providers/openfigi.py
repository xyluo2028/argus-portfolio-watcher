"""OpenFIGI adapter: map ISINs/CUSIPs (as N-PORT lists them) to exchange tickers, free.

Without an API key OpenFIGI allows 25 requests a minute of 10 identifiers each; with one
(OPENFIGI_API_KEY) 25 per 6 seconds of 100 each. A security trades on many venues, so the
listing is picked by the currency the fund holds it in, then converted to Yahoo's symbol.
"""

from __future__ import annotations

import httpx

from argus.providers.base import ProviderError

MAPPING_URL = "https://api.openfigi.com/v3/mapping"

# Bloomberg composite exchange code -> Yahoo suffix ("" = US listing).
YAHOO_SUFFIX = {
    "US": "", "JP": ".T", "LN": ".L", "NA": ".AS", "FP": ".PA", "GR": ".DE", "GY": ".DE", "SW": ".SW", "SE": ".SW",
    "HK": ".HK", "KS": ".KS", "KQ": ".KQ", "TT": ".TW", "CN": ".TO", "CT": ".TO", "AU": ".AX", "AT": ".AX",
    "IM": ".MI", "SM": ".MC", "SQ": ".MC", "SS": ".ST", "DC": ".CO", "FH": ".HE", "NO": ".OL", "BB": ".BR",
    "ID": ".IR", "AV": ".VI", "PL": ".LS", "SP": ".SI", "NZ": ".NZ", "IN": ".NS", "IS": ".NS", "IB": ".BO",
    "BZ": ".SA", "MM": ".MX", "SJ": ".JO", "IT": ".TA", "TB": ".BK", "IJ": ".JK", "MK": ".KL", "PM": ".PS",
    "CG": ".SS", "CS": ".SZ", "TI": ".IS", "PW": ".WA", "AB": ".SR", "CI": ".SN", "QD": ".QA", "UH": ".AE",
}
# Where a holding in this currency most likely trades.
CURRENCY_EXCH = {
    "USD": "US", "JPY": "JP", "GBP": "LN", "GBX": "LN", "CHF": "SW", "HKD": "HK", "KRW": "KS", "TWD": "TT",
    "CAD": "CN", "AUD": "AU", "SEK": "SS", "DKK": "DC", "NOK": "NO", "SGD": "SP", "NZD": "NZ", "INR": "IN",
    "BRL": "BZ", "MXN": "MM", "ZAR": "SJ", "ILS": "IT", "THB": "TB", "IDR": "IJ", "MYR": "MK", "PHP": "PM",
    "TRY": "TI", "PLN": "PW", "SAR": "AB", "CLP": "CI", "QAR": "QD", "AED": "UH",
}
EURO_EXCH = {"NL": "NA", "FR": "FP", "DE": "GR", "IT": "IM", "ES": "SM", "FI": "FH", "BE": "BB", "IE": "ID",
             "AT": "AV", "PT": "PL"}
# Fallback order when the currency gives no hint: the home country's exchange, then a US listing.
COUNTRY_EXCH = {**EURO_EXCH, "US": "US", "JP": "JP", "GB": "LN", "CH": "SW", "HK": "HK", "KR": "KS", "TW": "TT",
                "CA": "CN", "AU": "AU", "SE": "SS", "DK": "DC", "NO": "NO", "SG": "SP", "NZ": "NZ", "IN": "IN",
                "BR": "BZ", "MX": "MM", "ZA": "SJ", "IL": "IT", "CN": "CG"}


def preferred_exchange(currency: str | None, country: str | None) -> str | None:
    if currency == "EUR":
        return EURO_EXCH.get(country or "")
    return CURRENCY_EXCH.get(currency or "") or COUNTRY_EXCH.get(country or "")


def yahoo_symbol(ticker: str, exch: str) -> str | None:
    """Bloomberg ticker on an exchange -> Yahoo symbol (BRK/B US -> BRK.B, 700 HK -> 0700.HK)."""
    suffix = YAHOO_SUFFIX.get(exch)
    if suffix is None or not ticker:
        return None
    t = ticker.rstrip("/")
    if exch == "US":
        return t.replace("/", ".")
    if exch == "HK":
        t = t.zfill(4)
    return t.replace("/", "-").replace(" ", "-") + suffix


def pick_listing(listings: list[dict], currency: str | None, country: str | None,
                 isin: str | None = None) -> tuple[str, str] | None:
    """(ticker, exchange) of the listing a fund most likely holds: the currency's exchange, the home
    country's (as filed, then the ISIN's), else a US one."""
    usable = [(x.get("ticker"), (x.get("exchCode") or "").split(" ")[0]) for x in listings
              if x.get("ticker") and x.get("marketSector") in (None, "Equity")]
    for want in (preferred_exchange(currency, country), COUNTRY_EXCH.get(country or ""),
                 COUNTRY_EXCH.get((isin or "")[:2]), "US"):
        for t, e in usable:
            if want and e == want:
                return t, e
    return None


class OpenFigiProvider:
    name = "openfigi"

    def __init__(self, api_key: str | None = None, client: httpx.Client | None = None):
        self._key = api_key
        self._client = client or httpx.Client(timeout=30.0)
        self.batch = 100 if api_key else 10

    def map(self, items: list[dict]) -> dict[str, tuple[str, str] | None]:
        """items: {"id_type": "ID_ISIN"|"ID_CUSIP"|"ID_CINS", "id", "currency", "country", "isin"} (at
        most `batch`). A CUSIP starting with a letter is a CINS (non-US issuer), e.g. Linde's G54950103.
        Returns id -> (ticker, exchange), or None when OpenFIGI knows no usable listing."""
        jobs = [{"idType": i["id_type"], "idValue": i["id"], "marketSecDes": "Equity"} for i in items]
        headers = {"X-OPENFIGI-APIKEY": self._key} if self._key else {}
        try:
            r = self._client.post(MAPPING_URL, json=jobs, headers=headers)
        except httpx.HTTPError as e:
            raise ProviderError(f"openfigi: {e}") from e
        if r.status_code == 429:
            raise ProviderError("openfigi: rate limited")
        if r.status_code != 200:
            raise ProviderError(f"openfigi: HTTP {r.status_code}")
        out = {}
        for item, res in zip(items, r.json()):
            out[item["id"]] = pick_listing(res.get("data") or [], item.get("currency"), item.get("country"),
                                           item.get("isin"))
        return out
