"""
ALAS — Statistics Panel
Statistics panel with histogram and numeric summary.
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
    """Panel that shows statistics of the active layer."""

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

        self._placeholder = QLabel(tr("stat.no_data"))
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
        0: tr("asprs.never_classified"), 1: tr("asprs.unclassified"), 2: tr("prop.ground"),
        3: tr("asprs.low_vegetation"), 4: tr("asprs.medium_vegetation"), 5: tr("asprs.high_vegetation"),
        6: tr("asprs.building"), 7: tr("asprs.noise"), 8: tr("asprs.reserved"), 9: tr("asprs.water"),
        10: tr("asprs.rail"), 11: tr("asprs.road_surface"), 12: tr("asprs.overlap"), 13: tr("asprs.wire_guard"),
        14: tr("asprs.wire_conductor"), 15: tr("asprs.transmission_tower"), 16: tr("asprs.wire_connector"),
        17: tr("asprs.bridge_deck"), 18: tr("asprs.high_noise"),
    }

    def _show_pc_stats(self, pc: PointCloudData):
        title = QLabel(f"{pc.name}")
        title.setObjectName("subheading")
        self._layout.addWidget(title)

        grp_meta = QGroupBox(tr("stat.metadata"))
        form_m = QFormLayout(grp_meta)
        form_m.addRow(tr("stat.las_version"), QLabel(pc.file_version or "—"))
        form_m.addRow(tr("stat.point_format"), QLabel(str(pc.point_format) if pc.point_format is not None else "—"))
        form_m.addRow(tr("stat.crs_epsg"), QLabel(str(pc.crs_epsg) if pc.crs_epsg else "—"))
        form_m.addRow(tr("stat.sensor_type"), QLabel(pc.sensor_type))
        if pc.system_identifier:
            form_m.addRow(tr("stat.system_id"), QLabel(pc.system_identifier))
        if pc.creation_date:
            form_m.addRow(tr("stat.creation_date"), QLabel(pc.creation_date))
        dims = ", ".join(pc.available_dimensions)
        form_m.addRow(tr("stat.dimensions"), QLabel(dims))
        self._layout.addWidget(grp_meta)

        stats = pc.height_stats()
        if stats:
            grp = QGroupBox(tr("stat.height_z"))
            form = QFormLayout(grp)
            form.addRow(tr("stat.minimum"), QLabel(f"{stats['min']:.2f} m"))
            form.addRow(tr("stat.maximum"), QLabel(f"{stats['max']:.2f} m"))
            form.addRow(tr("stat.mean"), QLabel(f"{stats['mean']:.2f} m"))
            form.addRow(tr("stat.median"), QLabel(f"{stats['median']:.2f} m"))
            form.addRow(tr("stat.std_dev"), QLabel(f"{stats['std']:.2f} m"))
            form.addRow(tr("stat.range"), QLabel(f"{stats['max'] - stats['min']:.2f} m"))
            self._layout.addWidget(grp)

        if pc.intensity is not None:
            ity = pc.intensity
            grp_i = QGroupBox(tr("stat.intensity"))
            form_i = QFormLayout(grp_i)
            form_i.addRow(tr("stat.minimum"), QLabel(f"{int(ity.min())}"))
            form_i.addRow(tr("stat.maximum"), QLabel(f"{int(ity.max())}"))
            form_i.addRow(tr("stat.mean"), QLabel(f"{ity.mean():.1f}"))
            form_i.addRow(tr("stat.std_dev"), QLabel(f"{ity.std():.1f}"))
            self._layout.addWidget(grp_i)

        if pc.return_number is not None and pc.number_of_returns is not None:
            grp_r = QGroupBox(tr("stat.returns"))
            form_r = QFormLayout(grp_r)
            total = pc.point_count
            first = int((pc.return_number == 1).sum())
            single = int(((pc.return_number == 1) & (pc.number_of_returns == 1)).sum())
            last = int((pc.return_number == pc.number_of_returns).sum())
            form_r.addRow(tr("stat.first_returns"), QLabel(f"{first:,}  ({first/total*100:.1f}%)"))
            form_r.addRow(tr("stat.single_returns"), QLabel(f"{single:,}  ({single/total*100:.1f}%)"))
            form_r.addRow(tr("stat.last_returns"), QLabel(f"{last:,}  ({last/total*100:.1f}%)"))
            self._layout.addWidget(grp_r)

        hag = pc.hag_stats()
        if hag:
            grp_hag = QGroupBox(tr("stat.hag_normalization"))
            form_h = QFormLayout(grp_hag)
            form_h.addRow(tr("stat.minimum"), QLabel(f"{hag['min']:.2f} m"))
            form_h.addRow(tr("stat.maximum"), QLabel(f"{hag['max']:.2f} m"))
            form_h.addRow(tr("stat.mean"), QLabel(f"{hag['mean']:.2f} m"))
            form_h.addRow(tr("stat.median"), QLabel(f"{hag['median']:.2f} m"))
            form_h.addRow(tr("stat.std_dev"), QLabel(f"{hag['std']:.2f} m"))
            form_h.addRow(tr("stat.ground_pts"), QLabel(f"{hag['ground_points']:,}"))
            form_h.addRow(tr("stat.non_ground_pts"), QLabel(f"{hag['non_ground_points']:,}"))
            self._layout.addWidget(grp_hag)

        cls_summary = pc.classification_summary()
        if cls_summary:
            grp_cls = QGroupBox(tr("stat.classification"))
            form_cls = QFormLayout(grp_cls)
            total = pc.point_count
            for code, count in sorted(cls_summary.items()):
                label = self._ASPRS_NAMES.get(code, f"Class {code}")
                form_cls.addRow(f"{code} — {label}", QLabel(f"{count:,}  ({count/total*100:.1f}%)"))
            self._layout.addWidget(grp_cls)

        grp_gen = QGroupBox(tr("stat.general"))
        form_g = QFormLayout(grp_gen)
        form_g.addRow(tr("stat.total_points"), QLabel(f"{pc.point_count:,}"))
        if pc.bounds:
            b = pc.bounds
            area = (b[3] - b[0]) * (b[4] - b[1])
            density = pc.point_count / area if area > 0 else 0
            form_g.addRow(tr("stat.xy_area"), QLabel(f"{area:,.1f} m²"))
            form_g.addRow(tr("stat.density"), QLabel(f"{density:.1f} pts/m²"))
            form_g.addRow(tr("stat.x_range"), QLabel(f"{b[0]:.2f} — {b[3]:.2f}"))
            form_g.addRow(tr("stat.y_range"), QLabel(f"{b[1]:.2f} — {b[4]:.2f}"))
            form_g.addRow(tr("stat.z_range"), QLabel(f"{b[2]:.2f} — {b[5]:.2f} m"))
        self._layout.addWidget(grp_gen)

        self._layout.addStretch()

    def _show_raster_stats(self, rl: RasterLayer):
        title = QLabel(f"{rl.name}")
        title.setObjectName("subheading")
        self._layout.addWidget(title)

        grp_meta = QGroupBox(tr("stat.metadata"))
        form_m = QFormLayout(grp_meta)
        form_m.addRow(tr("stat.crs_epsg"), QLabel(str(rl.crs_epsg) if rl.crs_epsg else "—"))
        form_m.addRow(tr("stat.bands"), QLabel(str(rl.band_count)))
        if rl.band_names:
            form_m.addRow(tr("stat.band_names"), QLabel(", ".join(rl.band_names)))
        form_m.addRow(tr("stat.data_type"), QLabel(str(rl.dtype)))
        form_m.addRow(tr("stat.nodata_value"), QLabel(str(rl.nodata)))
        self._layout.addWidget(grp_meta)

        stats = rl.statistics()
        if stats:
            grp = QGroupBox(tr("stat.values"))
            form = QFormLayout(grp)
            form.addRow(tr("stat.minimum"), QLabel(f"{stats['min']:.4f}"))
            form.addRow(tr("stat.maximum"), QLabel(f"{stats['max']:.4f}"))
            form.addRow(tr("stat.mean"), QLabel(f"{stats['mean']:.4f}"))
            form.addRow(tr("stat.median"), QLabel(f"{stats['median']:.4f}"))
            form.addRow(tr("stat.std_dev"), QLabel(f"{stats['std']:.4f}"))
            form.addRow(tr("stat.range"), QLabel(f"{stats['max'] - stats['min']:.4f}"))
            self._layout.addWidget(grp)

        grp_gen = QGroupBox(tr("stat.general"))
        form_g = QFormLayout(grp_gen)
        form_g.addRow(tr("stat.size"), QLabel(f"{rl.width} × {rl.height} px"))
        if rl.resolution:
            form_g.addRow(tr("stat.resolution_x"), QLabel(f"{rl.resolution[0]:.4f} m"))
            form_g.addRow(tr("stat.resolution_y"), QLabel(f"{rl.resolution[1]:.4f} m"))
        if rl.bounds:
            b = rl.bounds
            area = (b[2] - b[0]) * (b[3] - b[1])
            form_g.addRow(tr("stat.area"), QLabel(f"{area:,.1f} m²"))
            form_g.addRow(tr("stat.x_range"), QLabel(f"{b[0]:.2f} — {b[2]:.2f}"))
            form_g.addRow(tr("stat.y_range"), QLabel(f"{b[1]:.2f} — {b[3]:.2f}"))
        self._layout.addWidget(grp_gen)

        self._layout.addStretch()
