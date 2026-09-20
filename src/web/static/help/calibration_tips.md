### Reference Marker Alignment Best Practices

Proper marker placement ensures subpixel stability across lighting variations:

- **Static & Rigid Landmarks**: Select permanent meter landmarks such as dial screws, casing rivets, or fixed logo corners. Never use moving dials or rotating needles.
- **Wide Non-Collinear Triangle**: Spread the 3 points widely across the image (top-left, top-right, bottom-center). A wide triangle maximizes affine alignment stability.
- **Consistent Illumination**: Avoid placing reference markers inside regions prone to specular LED glare or flash hotspots that shift pixel centroids.
- **Subpixel Stability Inspection**: Use the 200% zoom crop view in Step 4 to verify that reference crosshairs remain aligned across repeated snapshots.
