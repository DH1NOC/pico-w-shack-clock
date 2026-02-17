"""
QTH Locator (Maidenhead Grid Square) calculator for amateur radio applications
"""


class QTHLocator:
    """Calculate Maidenhead Grid Square locator from GPS coordinates"""
    
    FIELD_LON_SIZE = 20
    FIELD_LAT_SIZE = 10
    SQUARE_LON_SIZE = 2
    SQUARE_LAT_SIZE = 1
    
    @staticmethod
    def calculate(latitude, longitude):
        """Convert GPS coordinates to 6-character Maidenhead locator
        
        Args:
            latitude: Decimal degrees (-90 to +90)
            longitude: Decimal degrees (-180 to +180)
        
        Returns:
            str: 6-character QTH locator (e.g., 'JO62qm') or '------' if invalid
        """
        if not QTHLocator._is_valid_coordinate(latitude, longitude):
            return "------"
        
        normalized_lon = longitude + 180
        normalized_lat = latitude + 90
        
        field = QTHLocator._calculate_field(normalized_lon, normalized_lat)
        square = QTHLocator._calculate_square(normalized_lon, normalized_lat, field)
        subsquare = QTHLocator._calculate_subsquare(normalized_lon, normalized_lat, field, square)
        
        return field + square + subsquare
    
    @staticmethod
    def _is_valid_coordinate(latitude, longitude):
        """Validate coordinate ranges"""
        return -90 <= latitude <= 90 and -180 <= longitude <= 180
    
    @staticmethod
    def _calculate_field(lon, lat):
        """Calculate field (first 2 characters, uppercase)"""
        field_lon = int(lon / QTHLocator.FIELD_LON_SIZE)
        field_lat = int(lat / QTHLocator.FIELD_LAT_SIZE)
        return chr(ord('A') + field_lon) + chr(ord('A') + field_lat)
    
    @staticmethod
    def _calculate_square(lon, lat, field):
        """Calculate square (middle 2 characters, digits)"""
        field_lon_idx = ord(field[0]) - ord('A')
        field_lat_idx = ord(field[1]) - ord('A')
        
        lon_remainder = lon - (field_lon_idx * QTHLocator.FIELD_LON_SIZE)
        lat_remainder = lat - (field_lat_idx * QTHLocator.FIELD_LAT_SIZE)
        
        square_lon = int(lon_remainder / QTHLocator.SQUARE_LON_SIZE)
        square_lat = int(lat_remainder / QTHLocator.SQUARE_LAT_SIZE)
        
        return str(square_lon) + str(square_lat)
    
    @staticmethod
    def _calculate_subsquare(lon, lat, field, square):
        """Calculate subsquare (last 2 characters, lowercase)"""
        field_lon_idx = ord(field[0]) - ord('A')
        field_lat_idx = ord(field[1]) - ord('A')
        square_lon_idx = int(square[0])
        square_lat_idx = int(square[1])
        
        base_lon = (field_lon_idx * QTHLocator.FIELD_LON_SIZE) + (square_lon_idx * QTHLocator.SQUARE_LON_SIZE)
        base_lat = (field_lat_idx * QTHLocator.FIELD_LAT_SIZE) + (square_lat_idx * QTHLocator.SQUARE_LAT_SIZE)
        
        subsquare_lon = int((lon - base_lon) * 12)
        subsquare_lat = int((lat - base_lat) * 24)
        
        return chr(ord('a') + subsquare_lon) + chr(ord('a') + subsquare_lat)
