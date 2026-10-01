import json
import urllib.request
import urllib.parse
from typing import Tuple, Optional
from app.core.config import settings

_GEOCODE_CACHE = {}

def reverse_geocode(lat: float, lng: float, merchant_raw: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
    """
    Performs reverse geocoding & venue lookup to resolve GPS coordinates into human-readable place names.
    Supports Google Places API if GOOGLE_PLACES_API_KEY is set, with OpenStreetMap Nominatim fallback.
    Returns (location_name, location_address).
    """
    if not lat or not lng:
        return None, None

    cache_key = (round(lat, 4), round(lng, 4), (merchant_raw or "").lower())
    if cache_key in _GEOCODE_CACHE:
        return _GEOCODE_CACHE[cache_key]

    # Provider 1: Google Places Nearby Search (High accuracy for commercial venue names)
    if settings.GOOGLE_PLACES_API_KEY:
        google_res = _query_google_places(lat, lng, merchant_raw, settings.GOOGLE_PLACES_API_KEY)
        if google_res and google_res[0]:
            _GEOCODE_CACHE[cache_key] = google_res
            return google_res

    # Provider 2: OpenStreetMap Nominatim (Free, zero-config default)
    osm_res = _query_osm_nominatim(lat, lng)
    if osm_res and osm_res[0]:
        _GEOCODE_CACHE[cache_key] = osm_res
        return osm_res

    fallback_name = f"Near {lat:.3f}, {lng:.3f}"
    return fallback_name, None


def _query_google_places(lat: float, lng: float, merchant_raw: Optional[str], api_key: str) -> Tuple[Optional[str], Optional[str]]:
    try:
        if merchant_raw:
            query_str = urllib.parse.quote(merchant_raw)
            url = f"https://maps.googleapis.com/maps/api/place/nearbysearch/json?location={lat},{lng}&radius=200&keyword={query_str}&key={api_key}"
        else:
            url = f"https://maps.googleapis.com/maps/api/place/nearbysearch/json?location={lat},{lng}&radius=100&key={api_key}"

        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=3) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode('utf-8'))
                results = data.get("results", [])
                if results:
                    best = results[0]
                    place_name = best.get("name")
                    vicinity = best.get("vicinity") or best.get("formatted_address")
                    loc_name = f"{place_name}, {vicinity}" if vicinity else place_name
                    return loc_name, vicinity
    except Exception:
        pass
    return None, None


def _query_osm_nominatim(lat: float, lng: float) -> Tuple[Optional[str], Optional[str]]:
    url = f"https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat={lat}&lon={lng}"
    headers = {"User-Agent": "AdultMoneyPersonalExpenseIntelligence/1.0"}

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=3) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode('utf-8'))
                address_dict = data.get("address", {})
                
                locality = (
                    address_dict.get("suburb") or 
                    address_dict.get("neighbourhood") or 
                    address_dict.get("residential") or
                    address_dict.get("road")
                )
                city = (
                    address_dict.get("city") or 
                    address_dict.get("town") or 
                    address_dict.get("municipality") or
                    address_dict.get("state_district")
                )

                if locality and city:
                    loc_name = f"{locality}, {city}"
                elif city:
                    loc_name = city
                elif locality:
                    loc_name = locality
                else:
                    loc_name = data.get("display_name", "").split(",")[0]

                full_address = data.get("display_name")
                return loc_name, full_address
    except Exception:
        pass
    return None, None
