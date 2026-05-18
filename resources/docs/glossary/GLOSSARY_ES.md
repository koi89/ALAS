# Glosario

Definiciones de los términos clave utilizados en ALAS y en teledetección LiDAR.

---

## 1. A

**Altitud sobre el suelo**
Coordenada Z de un punto tras la normalización de altura; representa la altura real por encima del terreno, no la elevación sobre el nivel del mar.

---

## 2. B

---

## 3. C

**Clasificación**
Proceso de asignar a cada punto de la nube una categoría semántica (suelo, vegetación, edificio, agua, etc.). ALAS admite clasificación basada en reglas y asistida por IA.

**CRS — Sistema de Referencia de Coordenadas**
Marco geodésico que asigna coordenadas reales a los puntos. Se define mediante un código EPSG (p. ej. `25830` = ETRS89 UTM 30N).

---

## 4. D

**Decimación**
Reducción del número de puntos de una nube preservando su estructura espacial. Se usa para mejorar el rendimiento del visor con conjuntos de datos grandes.

**Densidad de puntos**
Número medio de puntos por metro cuadrado. Una mayor densidad permite detectar elementos más pequeños.

---

## 5. E

**EPSG (código)**
Identificador numérico de un sistema de referencia de coordenadas mantenido por el registro EPSG (p. ej. `4326` = WGS84 geográfico, `25830` = ETRS89 UTM 30N).

---

## 6. F

**Línea de vuelo**
Cada pasada del avión sobre el área de estudio. Varias líneas de vuelo con solapamiento se combinan para obtener una nube de puntos continua.

---

## 7. G

**Puntos de suelo**
Puntos clasificados como terreno desnudo (clase ASPRS 2). Se usan para generar el MDT y como referencia para la normalización de alturas.

---

## 8. H

---

## 9. I

**Intensidad**
Potencia del pulso láser retornado, almacenada como atributo de cada punto. Útil para distinguir materiales y texturas superficiales.

---

## 10. J

---

## 11. K

---

## 12. L

**LAS / LAZ**
Formato de archivo binario estándar para datos de nubes de puntos (`.las`) y su variante comprimida (`.laz`). Almacena coordenadas XYZ y atributos como intensidad, número de retorno y clasificación.

**LiDAR — Detección y Medición por Luz**
Tecnología de teledetección activa que emite pulsos láser y mide el tiempo de vuelo del eco retornado para calcular distancias 3D precisas.

---

## 13. M

**MCA — Modelo de Canopia de Altura (CHM)**
Ráster obtenido restando el MDT al MDS. Cada píxel representa la altura de la vegetación o estructuras sobre el suelo.

**MDS — Modelo Digital de Superficie (DSM)**
Ráster que representa la elevación de la primera superficie alcanzada por el láser, incluyendo copa de árboles, edificios y terreno desnudo.

**MDT — Modelo Digital del Terreno (DTM)**
Ráster que representa la elevación del terreno desnudo, obtenido usando únicamente los puntos clasificados como suelo.

**Multitemporal (análisis)**
Comparación de dos o más nubes de puntos adquiridas en diferentes momentos para detectar cambios en el terreno, la vegetación o las estructuras.

---

## 14. N

**Normalización de altura**
Resta de la elevación del suelo a la coordenada Z de cada punto, de modo que los valores representan altura sobre el suelo y no elevación sobre el nivel del mar.

**Nube de puntos**
Conjunto de puntos en el espacio 3D, cada uno con coordenadas XYZ y atributos opcionales. Es la estructura de datos principal del procesamiento LiDAR.

**Puntos de ruido**
Puntos erróneos causados por artefactos del sensor, partículas atmosféricas o aves. Se filtran antes del análisis.

---

## 15. O

---

## 16. P

**Primera retorno**
Primer eco del pulso registrado por el sensor. Suele corresponder a la cima de la copa o a la superficie más alta dentro de la huella del láser.

---

## 17. Q

---

## 18. R

**Número de retorno**
Identifica a qué eco corresponde un punto cuando un pulso láser produce múltiples retornos (p. ej. primero, segundo, último).

---

## 19. S

**Solapamiento**
Área cubierta por dos líneas de vuelo adyacentes. Mayor solapamiento mejora la densidad de puntos y reduce vacíos en los datos.

---

## 20. T

**Tesela (tile)**
Subdivisión espacial de una nube de puntos grande en bloques rectangulares manejables, frecuentemente usada en procesamiento por lotes.

---

## 21. U

---

## 22. V

**Análisis de vegetación**
Extracción de métricas forestales (altura del árbol, área de copa, densidad de dosel, etc.) a partir de puntos de vegetación clasificados y del MCA.

---

## 23. W

---

## 24. X

---

## 25. Y

---

## 26. Z
