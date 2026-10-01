from app.services.geocoding import reverse_geocode

def test_reverse_geocode_service():
    # Bengaluru coordinates (Indiranagar / MG Road area)
    lat = 12.9716
    lng = 77.5946

    loc_name, loc_address = reverse_geocode(lat, lng, "Swiggy")
    assert loc_name is not None
    assert len(loc_name) > 0
    assert "Bengaluru" in loc_name or "Bangalore" in loc_name or "Karnataka" in str(loc_address) or "Near" in loc_name
