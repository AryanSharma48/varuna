import numpy as np

class LookAlikeClassifier:
    """
    Discriminates genuine mineral oil slicks from marine SAR look-alikes such as:
    - Low-wind calm water zones
    - Biogenic / natural plant & plankton films
    - Ship wakes & turbulence trails
    - Rain cells & downdraft patches
    - Internal oceanic wave packets
    """
    def __init__(self):
        pass

    def classify_slick(self, 
                       slick_patch_vv: np.ndarray, 
                       surrounding_patch_vv: np.ndarray,
                       morphology: dict,
                       ambient_wind_ms: float = 6.5) -> dict:
        """
        Evaluates physical characteristics:
        1. Backscatter Damping Ratio (Oil typically has 6 - 15 dB damping)
        2. Boundary Gradient Sharpness (Oil slick edges are sharp due to surface tension)
        3. Aspect Ratio / Elongation (Mineral spills along shipping corridors are elongated)
        4. Ambient wind context
        """
        slick_mean = float(np.mean(slick_patch_vv)) if slick_patch_vv.size > 0 else -20.0
        bg_mean = float(np.mean(surrounding_patch_vv)) if surrounding_patch_vv.size > 0 else -10.0
        damping_db = abs(bg_mean - slick_mean)
        
        # Calculate edge sharpness via gradient
        if slick_patch_vv.ndim == 2:
            gy, gx = np.gradient(slick_patch_vv)
            gradient_mag = np.sqrt(gx**2 + gy**2)
        elif slick_patch_vv.ndim == 1 and slick_patch_vv.size > 1:
            g = np.gradient(slick_patch_vv)
            gradient_mag = np.abs(g)
        else:
            gradient_mag = np.array([0.0])
        edge_sharpness = float(np.percentile(gradient_mag, 90))
        
        aspect_ratio = morphology.get("aspect_ratio", 3.0)
        area_km2 = morphology.get("area_km2", 5.0)
        
        # Score factors
        oil_score = 0.0
        look_alike_type = None
        reasons = []
        
        # Damping check
        if 5.0 <= damping_db <= 18.0:
            oil_score += 0.35
            reasons.append(f"Backscatter damping ({damping_db:.1f} dB) matches mineral oil suppression")
        elif damping_db < 4.0:
            oil_score += 0.10
            look_alike_type = "BIOGENIC_FILM"
            reasons.append(f"Weak damping ({damping_db:.1f} dB) typical of thin natural biogenic slicks")
        else:
            oil_score += 0.15
            look_alike_type = "LOW_WIND_ZONE"
            reasons.append(f"Extreme damping ({damping_db:.1f} dB) characteristic of calm water sheltering")
            
        # Edge gradient check
        if edge_sharpness > 1.2:
            oil_score += 0.25
            reasons.append("Sharp, distinct perimeter gradients indicating high interfacial surface tension")
        else:
            oil_score += 0.10
            if not look_alike_type:
                look_alike_type = "INTERNAL_WAVES_OR_CURRENT"
            reasons.append("Diffuse boundary gradients characteristic of natural sea surface divergence")
            
        # Morphological elongation check
        if aspect_ratio >= 2.5:
            oil_score += 0.25
            reasons.append(f"Elongated trajectory morphology (aspect ratio {aspect_ratio:.1f}) consistent with moving vessel discharge")
        else:
            oil_score += 0.10
            if not look_alike_type:
                look_alike_type = "RAIN_CELL_OR_PLUME"
            reasons.append("Broad/amorphous shape with low elongation")

        # Wind check
        if 3.5 <= ambient_wind_ms <= 10.5:
            oil_score += 0.15
            reasons.append(f"Moderate ambient wind ({ambient_wind_ms} m/s) rules out low-wind calm sea false positives")
        else:
            oil_score += 0.05
            if ambient_wind_ms < 3.5:
                look_alike_type = "LOW_WIND_ZONE"
                reasons.append("Low ambient wind regime (<3.5 m/s) presents significant look-alike hazard")
                
        oil_score = min(1.0, max(0.0, oil_score))
        
        if oil_score >= 0.70:
            decision = "OIL"
            look_alike_risk = "LOW"
        elif oil_score >= 0.45:
            decision = "UNCERTAIN"
            look_alike_risk = "MEDIUM"
        else:
            decision = "LOOK_ALIKE"
            look_alike_risk = "HIGH"
            
        return {
            "decision": decision,
            "oil_confidence": round(oil_score, 3),
            "look_alike_risk": look_alike_risk,
            "look_alike_type": look_alike_type if decision != "OIL" else None,
            "damping_db": round(damping_db, 2),
            "edge_sharpness": round(edge_sharpness, 2),
            "reasons": reasons
        }
