import os
import mariadb
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from PyQt5.QtWidgets import QFileDialog, QMessageBox
from qgis.core import QgsProject, QgsVectorLayer
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
from qgis.PyQt.QtWidgets import QAction, QDialog
from .qgis_mariadb_plugin_dialog import QGISMariaDBPluginDialog


class QGISMariaDBPlugin:
    def __init__(self, iface):
        """Constructor."""
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.dlg = None
        self.actions = []
        self.menu = self.tr("&MariaDB to QGIS")
        self.toolbar = self.iface.addToolBar(self.tr("MariaDB to QGIS"))
        self.toolbar.setObjectName("MariaDB to QGIS")

    def tr(self, message):
        return QCoreApplication.translate("QGISMariaDBPlugin", message)

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""
        icon_path = "icon.png"  # Replace with your plugin icon path
        self.add_action(
            icon_path,
            text=self.tr("MariaDB to QGIS"),
            callback=self.run,
            parent=self.iface.mainWindow(),
        )

    def unload(self):
        """Remove the plugin menu item and icon."""
        for action in self.actions:
            self.iface.removePluginMenu(self.tr("&MariaDB to QGIS"), action)
            self.iface.removeToolBarIcon(action)
        del self.toolbar

    def add_action(
        self, icon_path, text, callback, parent=None, add_to_toolbar=True
    ):
        """Add a toolbar icon to the toolbar."""
        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        self.iface.addPluginToMenu(self.tr("&MariaDB to QGIS"), action)
        if add_to_toolbar:
            self.toolbar.addAction(action)
        self.actions.append(action)
        return action

    def run(self):
        """Run method that performs all the real work."""
        if not self.dlg:
            self.dlg = QGISMariaDBPluginDialog()
            self.dlg.buttonFetchData.clicked.connect(self.on_fetch_data_clicked)
            self.dlg.buttonBrowse.clicked.connect(self.on_browse_clicked)
        self.dlg.show()
        self.dlg.exec_()

    def on_browse_clicked(self):
        directory = QFileDialog.getExistingDirectory(
            self.dlg, "Select Output Directory"
        )
        self.dlg.lineEditOutputDir.setText(directory)

    def on_fetch_data_clicked(self):
        host = self.dlg.lineEditHost.text()
        user = self.dlg.lineEditUser.text()
        password = self.dlg.lineEditPassword.text()
        database = self.dlg.lineEditDatabase.text()
        #query = self.dlg.plainTextEditQuery.toPlainText()
        table = self.dlg.lineEditTable.text()
        x = self.dlg.lineEditX.text()
        y = self.dlg.lineEditY.text()
        output_dir = self.dlg.lineEditOutputDir.text()
        save_as_shapefile = self.dlg.checkBoxShapefile.isChecked()
        save_as_geopackage = self.dlg.checkBoxGeoPackage.isChecked()
        
        query = f"SELECT *, {x} as x, {y} as y FROM {table} WHERE {x} IS NOT NULL;"

        if not (host and user and password and database and query and output_dir):
            QMessageBox.warning(
                self.dlg,
                "Input Error",
                "Please fill in all fields and try again.",
            )
            return

        

        db_config = {
            "host": host,
            "user": user,
            "password": password,
            "database": database,
        }

        df = self.fetch_data_from_mariadb(db_config, query)

        if df is not None:
            gdf = self.convert_to_geodataframe(df)

            if gdf is not None:
                if save_as_shapefile:
                    self.write_shapefile(gdf, os.path.join(output_dir, "output.shp"))

                if save_as_geopackage:
                    self.write_geopackage(gdf, os.path.join(output_dir, "output.gpkg"))

                # Load the data into QGIS
                self.load_data_into_qgis(output_dir, save_as_shapefile, save_as_geopackage)

    def fetch_data_from_mariadb(self, config, query):
        """Fetches data from MariaDB and returns it as a pandas DataFrame."""
        try:
            connection = mariadb.connect(
                host=config["host"],
                user=config["user"],
                password=config["password"],
                database=config["database"],
            )
            cursor = connection.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()
            column_names = [desc[0] for desc in cursor.description]
            df = pd.DataFrame(rows, columns=column_names)
            return df
        except mariadb.Error as err:
            QMessageBox.critical(self.dlg, "Database Error", str(err))
            return None
        finally:
            if connection:
                connection.close()

    def convert_to_geodataframe(self, df):
        """Converts a DataFrame with x and y coordinates into a GeoDataFrame."""
        if df is None or df.empty:
            QMessageBox.warning(self.dlg, "Conversion Error", "No data available to convert.")
            return None

        if 'x' not in df.columns or 'y' not in df.columns:
            QMessageBox.warning(self.dlg, "Conversion Error", "DataFrame must contain 'x' and 'y' columns.")
            return None

        df["geometry"] = df.apply(lambda row: Point(row["x"], row["y"]), axis=1)
        gdf = gpd.GeoDataFrame(df, geometry="geometry")
        gdf.set_crs(epsg=4326, inplace=True)
        return gdf

    def write_shapefile(self, gdf, output_path):
        """Writes a GeoDataFrame to a shapefile."""
        if gdf is None or gdf.empty:
            QMessageBox.warning(self.dlg, "Shapefile Error", "No data available to write to shapefile.")
            return
        gdf.set_crs(epsg=4326, inplace=True)
        gdf.to_file(output_path, driver="ESRI Shapefile")
        QMessageBox.information(self.dlg, "Success", f"Shapefile written to {output_path}")

    def write_geopackage(self, gdf, output_geopackage_path, layer_name="points"):
        try:
            gdf.to_file(output_geopackage_path, layer=layer_name, driver="GPKG")
            QMessageBox.information(self.dlg, "Success", f"GeoDataFrame successfully written to GeoPackage at {output_geopackage_path}")
        except Exception as e:
            QMessageBox.critical(self.dlg, "GeoPackage Error", str(e))

    def load_data_into_qgis(self, output_dir, save_as_shapefile, save_as_geopackage):
        if save_as_shapefile:
            shapefile_path = os.path.join(output_dir, "output.shp")
            layer = QgsVectorLayer(shapefile_path, "MariaDB Shapefile", "ogr")
            if not layer.isValid():
                QMessageBox.critical(self.dlg, "Loading Error", "Failed to load shapefile into QGIS.")
            else:
                QgsProject.instance().addMapLayer(layer)

        if save_as_geopackage:
            geopackage_path = os.path.join(output_dir, "output.gpkg")
            layer = QgsVectorLayer(f"{geopackage_path}|layername=points", "MariaDB GeoPackage", "ogr")
            if not layer.isValid():
                QMessageBox.critical(self.dlg, "Loading Error", "Failed to load GeoPackage into QGIS.")
            else:
                QgsProject.instance().addMapLayer(layer)
