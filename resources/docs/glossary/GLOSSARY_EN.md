# Glossary

Definitions of key terms used in ALAS and LiDAR remote sensing.

---

## 1. A

**Aerial LiDAR**
LiDAR data acquired from an airborne platform (aircraft or drone). Produces dense 3D point clouds of terrain and surface features.

---

## 2. B

---

## 3. C

**CHM — Canopy Height Model**
Raster derived by subtracting the DTM from the DSM. Each pixel represents the height of vegetation or structures above the ground.

**Classification**
The process of labelling each point in a cloud with a semantic category (ground, vegetation, building, water, etc.). ALAS supports rule-based and AI-assisted classification.

**CRS — Coordinate Reference System**
The geodetic framework used to assign real-world coordinates to points. Defined by an EPSG code (e.g. `25830` = ETRS89 UTM 30N).

---

## 4. D

**Decimation**
Reducing the number of points in a cloud while preserving its spatial structure, used to improve viewport performance with large datasets.

**DSM — Digital Surface Model**
Raster representing the elevation of the first surface hit by the laser, including vegetation canopy, buildings, and bare ground.

**DTM — Digital Terrain Model**
Raster representing bare-earth elevation, obtained by using only points classified as ground.

---

## 5. E

**EPSG Code**
A numeric identifier for a coordinate reference system maintained by the EPSG registry (e.g. `4326` = WGS84 geographic, `25830` = ETRS89 UTM 30N).

---

## 6. F

**First Return**
The first pulse echo recorded by the sensor. Usually corresponds to the top of the canopy or the highest surface within the laser footprint.

**Flight Line**
A single pass of the aircraft over the survey area. Multiple overlapping flight lines are combined to produce a seamless point cloud.

---

## 7. G

**Ground Points**
Points classified as bare earth (ASPRS class 2). Used to generate the DTM and as reference for height normalization.

---

## 8. H

**Height Normalization**
Subtracting ground elevation from each point's Z coordinate so that height values represent height above ground rather than elevation above sea level.

---

## 9. I

**Intensity**
The strength of the returned laser pulse, stored as an attribute of each point. Useful for distinguishing surface materials and textures.

---

## 10. J

---

## 11. K

---

## 12. L

**LAS / LAZ**
The standard binary file format for point cloud data (`.las`) and its compressed variant (`.laz`). Stores XYZ coordinates plus attributes like intensity, return number, and classification.

**Last Return**
The last echo of a laser pulse, often penetrating through canopy gaps to reach the ground.

**LiDAR — Light Detection And Ranging**
An active remote sensing technology that emits laser pulses and measures the time-of-flight of the returning echo to compute precise 3D distances.

---

## 13. M

**Multitemporal Analysis**
Comparison of two or more point clouds acquired at different times to detect changes in terrain, vegetation, or structures.

---

## 14. N

**Noise Points**
Erroneous points caused by sensor artefacts, atmospheric particles, or birds. Typically filtered out before analysis.

---

## 15. O

**Overlap**
The area covered by two adjacent flight lines. Higher overlap improves point density and reduces data gaps.

---

## 16. P

**Point Cloud**
A set of data points in 3D space, each with XYZ coordinates and optional attributes. The primary data structure used in LiDAR processing.

**Point Density**
The average number of points per square metre. Higher density enables finer feature detection.

---

## 17. Q

---

## 18. R

**Return Number**
Identifies which echo a point corresponds to when a single laser pulse produces multiple returns (e.g. first, second, last).

---

## 19. S

**Slope**
Rate of change of elevation across the terrain surface, derived from the DTM. Used in geomorphological and hydrological analysis.

---

## 20. T

**Tile**
A spatial subdivision of a large point cloud into manageable rectangular blocks, often used for batch processing.

---

## 21. U

---

## 22. V

**Vegetation Analysis**
Extraction of forest metrics (tree height, crown area, canopy density, etc.) from classified vegetation points and the CHM.

---

## 23. W

---

## 24. X

---

## 25. Y

---

## 26. Z
