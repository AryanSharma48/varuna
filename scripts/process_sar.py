import argparse
import sys
import os
import json
from pathlib import Path

# Add project root to sys.path so we can import services
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from services.satellite.processor import (
    discover_polarizations,
    validate_compatibility,
    extract_metadata_stats,
    generate_previews
)

def main():
    parser = argparse.ArgumentParser(description="Process and validate Sentinel-1 SAR imagery.")
    parser.add_argument("--input-dir", type=str, required=True, help="Directory containing SAR TIFFs")
    parser.add_argument("--output-dir", type=str, required=True, help="Directory to save generated artifacts")
    args = parser.parse_args()

    print(f"--- Sentinel-1 Pipeline ---")
    print(f"Input Directory: {args.input_dir}")
    print(f"Output Directory: {args.output_dir}\n")

    # 1. Discover Polarizations
    print("1. Discovering Polarizations...")
    try:
        vv_path, vh_path = discover_polarizations(args.input_dir)
        if not vv_path or not vh_path:
            print("Error: Could not find both VV and VH polarizations.")
            sys.exit(1)
            
        print(f"  [+] Identified VV: {vv_path}")
        print(f"  [+] Identified VH: {vh_path}\n")
    except Exception as e:
        print(f"Error during discovery: {e}")
        sys.exit(1)

    # 2. Validate Compatibility
    print("2. Validating Spatial Compatibility...")
    try:
        compat_results = validate_compatibility(vv_path, vh_path)
        if compat_results["is_compatible"]:
            print("  [+] Validation PASS: Dimensions, CRS, Transform, Bounds, and GCPs match perfectly.\n")
        else:
            print("  [-] Validation FAIL: Mismatches detected.")
            print(json.dumps(compat_results, indent=2))
            sys.exit(1)
    except Exception as e:
        print(f"Error during validation: {e}")
        sys.exit(1)

    # 3. Extract Metadata & Stats
    print("3. Extracting Metadata and Geolocation...")
    try:
        stats = extract_metadata_stats(vv_path)
        
        print("\n  [Geolocation Metadata (Authoritative GCP Transformation)]")
        geo = stats.get("geographic_metadata")
        if geo:
            print(f"    VV GCP Count: {compat_results['gcps']['vv_count']}")
            print(f"    VH GCP Count: {compat_results['gcps']['vh_count']}")
            print(f"    GCP CRS: {geo['crs']}")
            print(f"    Geographic Center: {geo['center_lonlat']}")
            print("    Geographic Corners:")
            for corner, coords in geo['corners_lonlat'].items():
                print(f"      {corner}: {coords}")
            print(f"    Approximate Geographic Bounds: {geo['approximate_geographic_bounds']}")
            if geo.get("approximate_affine_transform"):
                print(f"    (APPROXIMATE) Affine Transform: {geo['approximate_affine_transform']}")
            
            print(f"    VV/VH Geolocation Agrees: {compat_results['gcps']['match']}")
        else:
            print("    No Geographic GCP Metadata found in file.")

        print("\n  [Pixel Metadata]")
        print(f"    Dimensions: {stats['dimensions']}")
        print(f"    Pixel CRS: {stats['pixel_crs']}")
        
        print("\n  [Exact Statistics (Block-wise)]")
        print(f"    Exact Min: {stats['exact_min']:.4f}")
        print(f"    Exact Max: {stats['exact_max']:.4f}")
        
        print("\n  [Estimated Statistics (Decimated Sample)]")
        print(f"    Estimated P2: {stats['estimated_p2']:.4f}")
        print(f"    Estimated P98: {stats['estimated_p98']:.4f}")
        print(f"    Estimated Mean: {stats['estimated_mean']:.4f}")
        print(f"    Estimated Std: {stats['estimated_std']:.4f}\n")
    except Exception as e:
        print(f"Error during metadata extraction: {e}")
        sys.exit(1)

    # 4. Generate Previews
    print("4. Generating Lightweight Previews (Decimated Reads)...")
    try:
        previews = generate_previews(vv_path, vh_path, args.output_dir)
        print("  [+] Previews generated successfully:")
        print(f"    VV: {previews['vv_preview']}")
        print(f"    VH: {previews['vh_preview']}")
        print(f"    Combined: {previews['combined_preview']}\n")
    except Exception as e:
        print(f"Error generating previews: {e}")
        sys.exit(1)

    print("--- Pipeline Execution Complete ---")

if __name__ == "__main__":
    main()
