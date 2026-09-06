import numpy as np

class ImageQualityGate:
    """
    Evaluates Sentinel-1 SAR scene quality before ML segmentation to prevent false detections
    and explicitly output quality status (HIGH, MEDIUM, LOW, INSUFFICIENT_EVIDENCE).
    """
    def __init__(self, 
                 max_missing_ratio: float = 0.15, 
                 min_dynamic_range_db: float = 8.0,
                 optimal_wind_min_ms: float = 3.0,
                 optimal_wind_max_ms: float = 12.0):
        self.max_missing_ratio = max_missing_ratio
        self.min_dynamic_range_db = min_dynamic_range_db
        self.optimal_wind_min_ms = optimal_wind_min_ms
        self.optimal_wind_max_ms = optimal_wind_max_ms

    def evaluate(self, 
                 sar_array: np.ndarray, 
                 wind_speed_ms: float = 6.5, 
                 coastal_distance_km: float = 15.0) -> dict:
        """
        sar_array: 2D or 3D numpy array representing SAR backscatter (dB or linear)
        wind_speed_ms: ambient wind speed in m/s
        coastal_distance_km: distance from nearest coastline in km
        """
        # 1. Missing / invalid pixels
        total_pixels = sar_array.size
        invalid_mask = np.isnan(sar_array) | np.isinf(sar_array) | (sar_array == 0)
        missing_count = np.sum(invalid_mask)
        missing_ratio = float(missing_count / total_pixels)
        
        valid_pixels = sar_array[~invalid_mask] if np.any(~invalid_mask) else np.array([0.0])
        
        # 2. Dynamic range & Contrast
        p5, p95 = np.percentile(valid_pixels, [5, 95])
        dynamic_range = float(p95 - p5)
        contrast_score = min(1.0, max(0.0, dynamic_range / 20.0))
        
        # 3. Environmental suitability (Wind speed criteria)
        # Optimal SAR oil detection wind range: 3 - 12 m/s
        if wind_speed_ms < self.optimal_wind_min_ms:
            wind_status = "LOW_WIND_RISK"  # Leads to natural calm water dark patches
            wind_suitability = 0.4
        elif wind_speed_ms > self.optimal_wind_max_ms:
            wind_status = "HIGH_WIND_DISPERSION_RISK" # Rapid wave mixing
            wind_suitability = 0.5
        else:
            wind_status = "OPTIMAL_WIND"
            wind_suitability = 1.0
            
        # 4. Coastal interference
        coastal_suitability = min(1.0, max(0.3, coastal_distance_km / 10.0))
        
        # Overall quality score calculation
        quality_metric = (
            (1.0 - min(1.0, missing_ratio / self.max_missing_ratio)) * 0.35 +
            contrast_score * 0.30 +
            wind_suitability * 0.25 +
            coastal_suitability * 0.10
        )
        
        reasons = []
        if missing_ratio > self.max_missing_ratio:
            reasons.append(f"High missing pixel ratio ({missing_ratio*100:.1f}%)")
        if dynamic_range < self.min_dynamic_range_db:
            reasons.append(f"Low SAR contrast dynamic range ({dynamic_range:.1f} dB)")
        if wind_speed_ms < self.optimal_wind_min_ms:
            reasons.append(f"Low ambient wind ({wind_speed_ms} m/s) increases natural look-alike probability")
        if coastal_distance_km < 3.0:
            reasons.append(f"Near-shore region ({coastal_distance_km} km) has coastal land interference")
            
        if quality_metric >= 0.75 and missing_ratio <= 0.05:
            quality_grade = "HIGH"
            is_acceptable = True
        elif quality_metric >= 0.50 and missing_ratio <= self.max_missing_ratio:
            quality_grade = "MEDIUM"
            is_acceptable = True
        elif quality_metric >= 0.30:
            quality_grade = "LOW"
            is_acceptable = False
        else:
            quality_grade = "INSUFFICIENT_EVIDENCE"
            is_acceptable = False

        return {
            "quality_grade": quality_grade,
            "quality_score": round(quality_metric, 3),
            "is_acceptable": is_acceptable,
            "missing_pixel_ratio": round(missing_ratio, 4),
            "dynamic_range_db": round(dynamic_range, 2),
            "wind_status": wind_status,
            "wind_speed_ms": wind_speed_ms,
            "coastal_distance_km": coastal_distance_km,
            "reasons": reasons
        }
