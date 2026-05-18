# ALAS — Tutorial de usuario

**Aerial LiDAR Analysis Software** · v1.0.0

---

## Tabla de contenidos

1. [Primeros pasos](#1-primeros-pasos)
2. [Carga de datos](#2-carga-de-datos)
3. [Visor 3D](#3-visor-3d)
4. [Panel de capas](#4-panel-de-capas)
5. [Clasificación](#5-clasificación)
6. [Modelos digitales (MDT / MDS / MCA)](#6-modelos-digitales-mdt--mds--mca)
7. [Módulos de análisis](#7-módulos-de-análisis)
   - [7.1 Geomorfología](#geomorfología)
   - [7.2 Hidrología](#hidrología)
   - [7.3 Vegetación](#vegetación)
   - [7.4 Análisis multitemporal](#análisis-multitemporal)
   - [7.5 Mis informes](#mis-informes)
8. [Herramientas de medición](#8-herramientas-de-medición)
9. [Procesamiento por lotes](#9-procesamiento-por-lotes)
10. [Exportación](#10-exportación)
11. [Proyectos](#11-proyectos)
12. [Atajos de teclado](#12-atajos-de-teclado)

---

## 1. Primeros pasos

### 1.1 Instalación

```bash
conda env create -f environment.yml
conda activate alas
python main.py
```

### 1.2 Inicio de sesión / Registro

Al iniciar, ALAS muestra una pantalla de inicio de sesión. Crea una cuenta o inicia sesión con tus credenciales. La sesión se almacena localmente, por lo que no necesitarás iniciar sesión cada vez.

---

## 2. Carga de datos

ALAS trabaja con archivos de nube de puntos `.las` y `.laz`.

### 2.1 Archivo único

**Archivo → Abrir** (`Ctrl+O`) — abre un selector de archivos. Tras la carga, la nube aparece en el visor 3D y se añade una nueva capa al panel de capas.

### 2.2 Múltiples archivos / teselas

**Archivo → Abrir múltiples** (`Ctrl+Shift+O`) — selecciona varios archivos a la vez. Cada archivo se convierte en su propia capa. Usa **Procesamiento → Fusionar teselas** después para combinarlos en una única nube.

### 2.3 Archivos grandes

Los archivos con más de ~1 millón de puntos se decimizan automáticamente en la importación para mantener el visor fluido. Los datos originales se conservan en disco; la versión decimada solo se utiliza para visualización y análisis interactivo.

### 2.4 Sistema de referencia de coordenadas

ALAS lee el CRS de la cabecera LAS/LAZ. Si no se encuentra ninguno, un diálogo te pedirá que introduzcas un código EPSG (p. ej. `25830` para ETRS89 UTM zona 30N España).

---

## 3. Visor 3D

El panel central es una vista 3D interactiva basada en PyVista/VTK.

### 3.1 Navegación

| Acción | Control |
|--------|---------|
| Rotar | Arrastrar con botón izquierdo |
| Desplazar | Arrastrar con botón central |
| Zoom | Rueda del ratón |
| Restablecer vista | `R` |

### 3.2 Vistas predefinidas

| Vista | Atajo |
|-------|-------|
| Superior (planta) | `T` |
| Frontal | `F` |
| Lateral | `S` |

### 3.3 Modos de colorización

Abre el panel **Propiedades** (lado derecho) para cambiar cómo se colorean los puntos:

- **Altura (Z)** — gradiente de elevación, útil para una visión general del terreno
- **Intensidad** — intensidad de retorno LiDAR, resalta tejados y superficies de carretera
- **Clasificación** — color por código de clase (suelo, vegetación, edificio…)
- **Número de retorno** — primero / último retorno
- **RGB original** — color real cuando el archivo lleva canales RGB
- **Color sólido** — color uniforme con tamaño de punto ajustable

### 3.4 Tamaño de punto

Arrastra el deslizador **Tamaño de punto** en el panel de Propiedades para aumentar o reducir el tamaño de renderizado de los puntos.

---

## 4. Panel de capas

El panel **Capas** (lado izquierdo) lista todas las nubes de puntos cargadas y los rásters generados.

| Control | Acción |
|---------|--------|
| Casilla de verificación | Activar/desactivar visibilidad de la capa |
| Doble clic en el nombre | Renombrar la capa |
| Clic derecho | Menú contextual: Zoom, Exportar, Eliminar |

Las capas ráster generadas por análisis (MDT, mapas de pendiente, etc.) aparecen debajo de las nubes de puntos y pueden activarse de forma independiente.

---

## 5. Clasificación

**Procesamiento → Clasificar** abre el diálogo de clasificación.

### 5.1 Algoritmos disponibles

| Algoritmo | Recomendado para |
|-----------|-----------------|
| **SMRF** (Filtro Morfológico Simple) | Terreno abierto, vegetación escasa |
| **CSF** (Filtro de Simulación de Tela) | Pendientes pronunciadas, terreno complejo |
| **PMF** (Filtro Morfológico Progresivo) | Zonas urbanas |
| **IA** (Red Neuronal) | Escenas mixtas — requiere un archivo `.pt` en `resources/models/` |

### 5.2 Opciones

- **Post-proceso: vegetación** — clasifica vegetación baja / media / alta tras la separación del suelo
- **Post-proceso: edificios** — intenta extraer tejados de edificios

### 5.3 Flujo de trabajo

1. Selecciona la capa de destino en el panel de capas.
2. Abre **Procesamiento → Clasificar**.
3. Elige el algoritmo y ajusta los parámetros.
4. Haz clic en **Ejecutar**. Aparece una barra de progreso; el visor se actualiza al terminar.
5. Cambia la colorización a **Clasificación** para inspeccionar los resultados.

### 5.4 Historial de clasificaciones

**Procesamiento → Historial de clasificaciones** (`Ctrl+Shift+H`) muestra un registro de todas las ejecuciones con parámetros y conteo de puntos por clase. Útil para comparar configuraciones de algoritmos.

---

## 6. Modelos digitales (MDT / MDS / MCA)

**Procesamiento → Generar modelo digital** abre el diálogo de generación de rásters.

| Modelo | Descripción |
|--------|-------------|
| **MDT** | Modelo Digital del Terreno — solo puntos de suelo |
| **MDS** | Modelo Digital de Superficie — retorno más alto por celda |
| **MCA** | Modelo de Altura del Dosel — MDS menos MDT |

### 6.1 Métodos de interpolación

- **IDW** — Ponderación por Distancia Inversa, resultados suaves, bueno para datos dispersos
- **TIN** — Red Irregular Triangulada (Delaunay), preserva líneas de ruptura
- **Vecino más cercano** — más rápido, bueno para nubes densas y uniformes

### 6.2 Pasos

1. Asegúrate de que la nube de puntos está clasificada (la clase suelo debe estar presente para MDT/MCA).
2. Abre **Procesamiento → Generar modelo digital**.
3. Selecciona el tipo de modelo, la resolución de celda (metros) y el método de interpolación.
4. Haz clic en **Generar**. El ráster se añade como nueva capa y se exporta automáticamente como GeoTIFF.

---

## 7. Módulos de análisis

Todos los módulos se encuentran en el menú **Análisis**. Cada uno requiere al menos una capa seleccionada.

### 7.1 Geomorfología

**Análisis → Geomorfología** calcula derivadas del terreno a partir de un MDT:

- **Pendiente** — gradiente en grados
- **Aspecto** — dirección cardinal de la cara de la pendiente
- **Curvatura** — curvatura de perfil y planta
- **Rugosidad** — variabilidad local de la superficie
- **Sombreado de colinas** — relieve sombreado para visualización
- **Clasificación morfométrica** — clases de formas del terreno (crestas, valles, llanuras…)

Selecciona las salidas deseadas, establece la capa MDT y haz clic en **Ejecutar**. Cada salida se convierte en una capa ráster independiente.

### 7.2 Hidrología

**Análisis → Hidrología** modela el flujo de agua sobre el terreno:

- **Dirección de flujo (D8)** — enrutamiento de flujo en una sola dirección
- **Acumulación de flujo** — área de aportación aguas arriba por celda
- **Zonas de encharcamiento** — depresiones que retienen agua
- **Simulación de lluvia** — simula un evento de lluvia y traza la escorrentía
- **Simulación de inundación** — inundación a un nivel de agua dado

Establece la capa MDT y las salidas deseadas, luego haz clic en **Ejecutar**.

### 7.3 Vegetación

**Análisis → Vegetación** trabaja con nubes de puntos clasificadas con clases de vegetación:

- **Detección de árboles** — identifica ubicaciones de árboles individuales
- **Segmentación de copas** — delimita las copas de los árboles individuales
- **Mapa de densidad** — ráster de densidad de puntos por celda

Los resultados se exportan como capas ráster y opcionalmente como archivos vectoriales.

### 7.4 Análisis multitemporal

**Análisis → Multitemporal** compara dos MDT de fechas distintas:

- **Diferencia de MDT (DoD)** — cambio de elevación celda por celda
- **Clasificación de cambios** — zonas de erosión / deposición / estables
- **Detección de deforestación** — pérdida de dosel entre épocas

Pasos:
1. Carga los MDT de dos fechas distintas (o genéralos a partir de nubes clasificadas).
2. Abre **Análisis → Multitemporal**.
3. Asigna las capas MDT *antes* y *después*.
4. Selecciona las salidas y haz clic en **Ejecutar**.

### 7.5 Mis informes

**Análisis → Mis informes** (`Ctrl+Shift+R`) lista todos los informes PDF generados en sesiones anteriores. Haz clic en cualquier entrada para abrirla o volver a exportarla.

---

## 8. Herramientas de medición

Todas las herramientas están en el menú **Herramientas**. Activa una herramienta, interactúa con el visor y los resultados aparecerán en el panel **Mediciones**.

### 8.1 Perfil topográfico

**Herramientas → Perfil** — haz clic en dos puntos del visor para trazar una sección transversal. Un gráfico muestra la elevación a lo largo del transecto.

### 8.2 Distancia

**Herramientas → Distancia** — haz clic en dos puntos para medir la distancia 3D en línea recta y su proyección horizontal (2D).

### 8.3 Área

**Herramientas → Área** — haz clic en los vértices para definir un polígono y luego haz clic derecho para cerrarlo. Muestra el área planimétrica (plana) y el área superficial (calculada a partir del MDT subyacente).

### 8.4 Volumen

**Herramientas → Volumen** — define un polígono como antes y luego establece una elevación de referencia. Muestra los volúmenes de corte y relleno respecto a ese plano.

### 8.5 Historial de mediciones

**Herramientas → Historial de mediciones** (`Ctrl+H`) muestra todas las mediciones de la sesión actual. Las filas individuales se pueden copiar o exportar a CSV.

Pulsa `Esc` para cancelar cualquier herramienta de medición activa.

---

## 9. Procesamiento por lotes

**Procesamiento → Por lotes** (`Ctrl+B`) permite ejecutar el mismo flujo de trabajo en una carpeta de archivos LAS/LAZ sin cargar cada uno manualmente.

### 9.1 Flujo de trabajo

1. Abre **Procesamiento → Por lotes**.
2. Establece la **Carpeta de entrada** que contiene tus archivos `.las`/`.laz`.
3. Establece la **Carpeta de salida** para los resultados.
4. Construye el pipeline activando los pasos en orden:
   - Preprocesado (filtro de ruido, decimación)
   - Clasificación (elige el algoritmo)
   - Generación de modelos digitales (elige el tipo y la resolución)
   - Análisis (geomorfología, hidrología, vegetación)
   - Exportación (GeoTIFF, informe PDF)
5. Haz clic en **Iniciar**. Una barra de progreso rastrea el avance archivo por archivo y paso por paso.

Los procesos por lotes pueden pausarse y los resultados se guardan de forma incremental, por lo que un fallo no reinicia toda la cola.

---

## 10. Exportación

**Archivo → Exportar** (`Ctrl+E`) abre el diálogo de exportación para la capa seleccionada.

### 10.1 Formatos de nube de puntos

| Formato | Notas |
|---------|-------|
| **LAZ** | LAS comprimido, recomendado para archivar |
| **LAS** | Sin comprimir, máxima compatibilidad |

### 10.2 Ráster

- **GeoTIFF** — ráster georreferenciado estándar, compatible con QGIS, ArcGIS, GDAL

### 10.3 Malla 3D

- **OBJ** — malla triangulada derivada de la nube de puntos, utilizable en Blender, MeshLab

### 10.4 Informe

- **PDF** — informe resumen con estadísticas, renders colorizados y resultados de análisis. Los informes generados se guardan en la nube y son accesibles desde **Análisis → Mis informes**.

---

## 11. Proyectos

Guarda tu espacio de trabajo completo — capas cargadas, resultados de clasificación, rásters generados y mediciones — en un único archivo `.alas`.

| Acción | Menú / Atajo |
|--------|-------------|
| Guardar proyecto | **Archivo → Guardar proyecto** (`Ctrl+S`) |
| Cargar proyecto | **Archivo → Cargar proyecto** (`Ctrl+Shift+S`) |

Al abrir un archivo `.alas` se restauran todas las capas y sus configuraciones exactamente como las dejaste.

---

## 12. Atajos de teclado

### 12.1 Archivo

| Acción | Atajo |
|--------|-------|
| Abrir archivo | `Ctrl+O` |
| Abrir múltiples | `Ctrl+Shift+O` |
| Guardar proyecto | `Ctrl+S` |
| Cargar proyecto | `Ctrl+Shift+S` |
| Exportar | `Ctrl+E` |
| Salir | `Ctrl+Q` |

### 12.2 Vista

| Acción | Atajo |
|--------|-------|
| Restablecer cámara | `R` |
| Vista superior | `T` |
| Vista frontal | `F` |
| Vista lateral | `S` |

### 12.3 Procesamiento

| Acción | Atajo |
|--------|-------|
| Clasificar | *(menú)* |
| Historial de clasificaciones | `Ctrl+Shift+H` |
| Procesamiento por lotes | `Ctrl+B` |

### 12.4 Análisis

| Acción | Atajo |
|--------|-------|
| Mis informes | `Ctrl+Shift+R` |

### 12.5 Herramientas

| Acción | Atajo |
|--------|-------|
| Historial de mediciones | `Ctrl+H` |
| Cancelar herramienta activa | `Esc` |

### 12.6 Aplicación

| Acción | Atajo |
|--------|-------|
| Configuración | `Ctrl+,` |

---

## Consejos

- **Orden de trabajo:** Cargar → Preprocesar → Clasificar → Generar MDT → Analizar. Seguir este orden evita que falten entradas en los pasos posteriores.
- **Proyectos grandes:** Usa el Procesamiento por lotes en lugar de cargar todas las teselas de forma interactiva. Es significativamente más rápido y usa menos RAM.
- **El CRS importa:** Verifica siempre el código EPSG en la importación. Un CRS incorrecto desplazará los datos y corromperá las mediciones.
- **Clasificación IA:** Coloca tu archivo `.pt` en `resources/models/` antes de abrir el diálogo de Clasificación; de lo contrario, la opción IA aparecerá desactivada.
- **Informes PDF:** Los informes se almacenan en el servidor. Son accesibles desde cualquier máquina tras iniciar sesión en **Análisis → Mis informes**.
