"""
ALAS — Statistics Panel
Panel de estadísticas con histograma y resumen numérico.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QGroupBox, QFormLayout, QScrollArea
)
from PyQt6.QtCore import Qt

from app.core.layer_manager import LayerManager
from app.core.point_cloud import PointCloudData
from app.core.raster_layer import RasterLayer
from app.config import ASPRS_COLORS
from app.i18n import tr


class StatisticsPanel(QWidget):
    """Panel que muestra estadísticas de la capa activa."""

    def __init__(self, layer_manager: LayerManager, parent=None):
        super().__init__(parent)
        self.layer_manager = layer_manager
        self._setup_ui()
        self.layer_manager.active_layer_changed.connect(self._update)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self._content = QWidget()
        self._layout = QVBoxLayout(self._content)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(self._content)
        layout.addWidget(scroll)

        self._placeholder = QLabel("Sin datos estadísticos")
        self._placeholder.setObjectName("muted")
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._layout.addWidget(self._placeholder)

    def _update(self, index: int):
        self._clear()
        entry = self.layer_manager.get_entry(index)
        if entry is None:
            return

        if entry.is_point_cloud:
            self._show_pc_stats(entry.layer)
        elif entry.is_raster:
            self._show_raster_stats(entry.layer)

    def _clear(self):
        while self._layout.count():
            item = self._layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    _ASPRS_NAMES = {
        0: "Never classified", 1: "Unclassified", 2: "Ground",
        3: "Low vegetation", 4: "Medium vegetation", 5: "High vegetation",
        6: "Building", 7: "Noise", 8: "Reserved", 9: "Water",
        10: "Rail", 11: "Road surface", 12: "Overlap", 13: "Wire guard",
        14: "Wire conductor", 15: "Transmission tower", 16: "Wire connector",
        17: "Bridge deck", 18: "High noise",
    }

    def _show_pc_stats(self, pc: PointCloudData):
        title = QLabel(f"{pc.name}")
        title.setObjectName("subheading")
        self._layout.addWidget(title)

        grp_meta = QGroupBox("Metadata")
        form_m = QFormLayout(grp_meta)
        form_m.addRow("LAS version", QLabel(pc.file_version or "—"))
        form_m.addRow("Point format", QLabel(str(pc.point_format) if pc.point_format is not None else "—"))
        form_m.addRow("CRS (EPSG)", QLabel(str(pc.crs_epsg) if pc.crs_epsg else "—"))
        form_m.addRow("Sensor type", QLabel(pc.sensor_type))
        if pc.system_identifier:
            form_m.addRow("System ID", QLabel(pc.system_identifier))
        if pc.creation_date:
            form_m.addRow("Creation date", QLabel(pc.creation_date))
        dims = ", ".join(pc.available_dimensions)
        form_m.addRow("Dimensions", QLabel(dims))
        self._layout.addWidget(grp_meta)

        stats = pc.height_stats()
        if stats:
            grp = QGroupBox("Altura (Z)")
            form = QFormLayout(grp)
            form.addRow("Mínimo", QLabel(f"{stats['min']:.2f} m"))
            form.addRow("Máximo", QLabel(f"{stats['max']:.2f} m"))
            form.addRow("Media", QLabel(f"{stats['mean']:.2f} m"))
            form.addRow("Mediana", QLabel(f"{stats['median']:.2f} m"))
            form.addRow("Desv. est.", QLabel(f"{stats['std']:.2f} m"))
            form.addRow("Rango", QLabel(f"{stats['max'] - stats['min']:.2f} m"))
            self._layout.addWidget(grp)

        if pc.intensity is not None:
            ity = pc.intensity
            grp_i = QGroupBox("Intensity")
            form_i = QFormLayout(grp_i)
            form_i.addRow("Min", QLabel(f"{int(ity.min())}"))
            form_i.addRow("Max", QLabel(f"{int(ity.max())}"))
            form_i.addRow("Mean", QLabel(f"{ity.mean():.1f}"))
            form_i.addRow("Std Dev", QLabel(f"{ity.std():.1f}"))
            self._layout.addWidget(grp_i)

        if pc.return_number is not None and pc.number_of_returns is not None:
            grp_r = QGroupBox("Returns")
            form_r = QFormLayout(grp_r)
            total = pc.point_count
            first = int((pc.return_number == 1).sum())
            single = int(((pc.return_number == 1) & (pc.number_of_returns == 1)).sum())
            last = int((pc.return_number == pc.number_of_returns).sum())
            form_r.addRow("First returns", QLabel(f"{first:,}  ({first/total*100:.1f}%)"))
            form_r.addRow("Single returns", QLabel(f"{single:,}  ({single/total*100:.1f}%)"))
            form_r.addRow("Last returns", QLabel(f"{last:,}  ({last/total*100:.1f}%)"))
            self._layout.addWidget(grp_r)

        hag = pc.hag_stats()
        if hag:
            grp_hag = QGroupBox("HAG Normalization (Height Above Ground)")
            form_h = QFormLayout(grp_hag)
            form_h.addRow("Min", QLabel(f"{hag['min']:.2f} m"))
            form_h.addRow("Max", QLabel(f"{hag['max']:.2f} m"))
            form_h.addRow("Mean", QLabel(f"{hag['mean']:.2f} m"))
            form_h.addRow("Median", QLabel(f"{hag['median']:.2f} m"))
            form_h.addRow("Std Dev", QLabel(f"{hag['std']:.2f} m"))
            form_h.addRow("Ground pts", QLabel(f"{hag['ground_points']:,}"))
            form_h.addRow("Non-ground pts", QLabel(f"{hag['non_ground_points']:,}"))
            self._layout.addWidget(grp_hag)

        cls_summary = pc.classification_summary()
        if cls_summary:
            grp_cls = QGroupBox("Classification")
            form_cls = QFormLayout(grp_cls)
            total = pc.point_count
            for code, count in sorted(cls_summary.items()):
                label = self._ASPRS_NAMES.get(code, f"Class {code}")
                form_cls.addRow(f"{code} — {label}", QLabel(f"{count:,}  ({count/total*100:.1f}%)"))
            self._layout.addWidget(grp_cls)

        grp_gen = QGroupBox("General")
        form_g = QFormLayout(grp_gen)
        form_g.addRow("Total puntos", QLabel(f"{pc.point_count:,}"))
        if pc.bounds:
            b = pc.bounds
            area = (b[3] - b[0]) * (b[4] - b[1])
            density = pc.point_count / area if area > 0 else 0
            form_g.addRow("Área XY", QLabel(f"{area:,.1f} m²"))
            form_g.addRow("Densidad", QLabel(f"{density:.1f} pts/m²"))
            form_g.addRow("X range", QLabel(f"{b[0]:.2f} — {b[3]:.2f}"))
            form_g.addRow("Y range", QLabel(f"{b[1]:.2f} — {b[4]:.2f}"))
            form_g.addRow("Z range", QLabel(f"{b[2]:.2f} — {b[5]:.2f} m"))
        self._layout.addWidget(grp_gen)

        self._layout.addStretch()

    def _show_raster_stats(self, rl: RasterLayer):
        title = QLabel(f"{rl.name}")
        title.setObjectName("subheading")
        self._layout.addWidget(title)

        grp_meta = QGroupBox("Metadata")
        form_m = QFormLayout(grp_meta)
        form_m.addRow("CRS (EPSG)", QLabel(str(rl.crs_epsg) if rl.crs_epsg else "—"))
        form_m.addRow("Bands", QLabel(str(rl.band_count)))
        if rl.band_names:
            form_m.addRow("Band names", QLabel(", ".join(rl.band_names)))
        form_m.addRow("Data type", QLabel(str(rl.dtype)))
        form_m.addRow("No-data value", QLabel(str(rl.nodata)))
        self._layout.addWidget(grp_meta)

        stats = rl.statistics()
        if stats:
            grp = QGroupBox("Valores")
            form = QFormLayout(grp)
            form.addRow("Mínimo", QLabel(f"{stats['min']:.4f}"))
            form.addRow("Máximo", QLabel(f"{stats['max']:.4f}"))
            form.addRow("Media", QLabel(f"{stats['mean']:.4f}"))
            form.addRow("Mediana", QLabel(f"{stats['median']:.4f}"))
            form.addRow("Desv. est.", QLabel(f"{stats['std']:.4f}"))
            form.addRow("Rango", QLabel(f"{stats['max'] - stats['min']:.4f}"))
            self._layout.addWidget(grp)

        grp_gen = QGroupBox("General")
        form_g = QFormLayout(grp_gen)
        form_g.addRow("Tamaño", QLabel(f"{rl.width} × {rl.height} px"))
        if rl.resolution:
            form_g.addRow("Resolución X", QLabel(f"{rl.resolution[0]:.4f} m"))
            form_g.addRow("Resolución Y", QLabel(f"{rl.resolution[1]:.4f} m"))
        if rl.bounds:
            b = rl.bounds
            area = (b[2] - b[0]) * (b[3] - b[1])
            form_g.addRow("Área", QLabel(f"{area:,.1f} m²"))
            form_g.addRow("X range", QLabel(f"{b[0]:.2f} — {b[2]:.2f}"))
            form_g.addRow("Y range", QLabel(f"{b[1]:.2f} — {b[3]:.2f}"))
        self._layout.addWidget(grp_gen)

        self._layout.addStretch()
