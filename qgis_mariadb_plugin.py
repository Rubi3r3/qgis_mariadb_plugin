import os
import mariadb
import psycopg2
import pandas as pd
import geopandas as gpd
import datetime
import time
from sqlalchemy import create_engine
from shapely.geometry import Point
from PyQt5.QtWidgets import QFileDialog, QMessageBox
from qgis.core import QgsProject, QgsVectorLayer
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
from qgis.PyQt.QtWidgets import QAction, QDialog
from .qgis_mariadb_plugin_dialog import QGISMariaDBPluginDialog
from .install_dependencies import install_dependencies


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
        icon_path = os.path.join(self.plugin_dir,"icon.png")  # Replace with your plugin icon path
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

    def run(self):
        install_dependencies()

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
        port = int(self.dlg.lineEditPort.text())
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
        query_null = f"SELECT *, {x} as x, {y} as y FROM {table} WHERE {x} IS NULL;"
  
        if not (host and user and password and database and query and output_dir):
            QMessageBox.warning(
                self.dlg,
                "Input Error",
                "Please fill in all fields and try again.",
            )
            return

        db_config = {
            "host": host,
            "port": port,
            "user": user,
            "password": password,
            "database": database,
        }

        df = self.fetch_data_from_mariadb(db_config, query)
        df_null = self.fetch_data_from_mariadb(db_config, query_null)

        if df is not None:
            gdf = self.convert_to_geodataframe(df)

            if gdf is not None:
                if save_as_shapefile:
                    self.write_shapefile(gdf, os.path.join(output_dir, f"{table}.shp"))
                    if df_null is not None and not df_null.empty:
                        self.write_csv(df_null, os.path.join(output_dir, f"{table}_null.csv"))

                if save_as_geopackage:
                    self.write_geopackage(gdf, os.path.join(output_dir, f"{table}.gpkg"))
                    if df_null is not None and not df_null.empty:
                        self.write_null_to_geopackage(df_null, os.path.join(output_dir, f"{table}.gpkg"))

                # Load the data into QGIS
                self.load_data_into_qgis(output_dir, save_as_shapefile, save_as_geopackage)

    def fetch_data_from_mariadb(self, config, query):
        """Fetches data from MariaDB and returns it as a pandas DataFrame."""
        try:
            connection = mariadb.connect(
                host=config["host"],
                port=config["port"],
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

        user = self.dlg.lineEditUser.text()

        df["geometry"] = df.apply(lambda row: Point(row["x"], row["y"]), axis=1)
        gdf = gpd.GeoDataFrame(df, geometry="geometry")
        gdf.set_crs(epsg=4326, inplace=True)
        gdf = gdf.drop(columns=["x", "y"])
        gdf["exported_by"] = user
        gdf["exported_date"] = datetime.datetime.now().date()
        return gdf


    def write_csv(self, df, output_path):
        table = self.dlg.lineEditTable.text()
        user = self.dlg.lineEditUser.text()

        df = df.drop(columns=['x', 'y'])

        df['exported_by'] = user
        df['exported_date'] = datetime.datetime.now().date()

        """Writes a DataFrame to a CSV file."""
        df.to_csv(output_path, index=False)
        QMessageBox.information(self.dlg, "Success", f"{table} with no geom written to {output_path}")

    def write_null_to_geopackage(self, df_null, output_geopackage_path):
        
        table = self.dlg.lineEditTable.text()
        user = self.dlg.lineEditUser.text()

        """Writes DataFrame with null coordinates to a GeoPackage."""
        if df_null is None or df_null.empty:
            QMessageBox.warning(self.dlg, "GeoPackage Error", "No null data available to write.")
            return

        table_name = f"{table}_null_geom"

        try:

            # Drop the 'x' and 'y' columns if they exist
            df_null = df_null.drop(columns=['x', 'y'], errors='ignore')

            # Add 'exported_by' and 'exported_date' columns
            df_null['exported_by'] = user  # Replace 'user' with actual username if needed
            df_null['exported_date'] = datetime.datetime.now().date()

            # Create a SQLAlchemy engine for the GeoPackage
            engine = create_engine(f"sqlite:///{output_geopackage_path}")
        
            # Write the DataFrame to the GeoPackage as a table
            df_null.to_sql(table_name, engine, if_exists='replace', index=False)
        
            QMessageBox.information(self.dlg, "Success", f"{table} with no geometry successfully written to GeoPackage at {output_geopackage_path} as table '{table_name}'")
        except Exception as e:
            QMessageBox.critical(self.dlg, "GeoPackage Error", str(e))

    def write_shapefile(self, gdf, output_path):
        """Writes a GeoDataFrame to a shapefile."""
        table = self.dlg.lineEditTable.text()

        try: 
            # Check if the shapefile exists and remove it
            if os.path.exists(output_path):
                os.remove(output_path)

            if gdf is None or gdf.empty:
                QMessageBox.warning(self.dlg, "Shapefile Error", "No data available to write to shapefile.")
                return
            gdf.set_crs(epsg=4326, inplace=True)
            gdf.to_file(output_path, driver="ESRI Shapefile")
            QMessageBox.information(self.dlg, "Success", f"{table} written to {output_path}")
        finally:
            time.sleep(1)
  

    def write_geopackage(self, gdf, output_geopackage_path):
        table = self.dlg.lineEditTable.text()
        layer_name = f"{table}_points"

        try:
            gdf.to_file(output_geopackage_path, layer=layer_name, driver="GPKG")
            QMessageBox.information(self.dlg, "Success", f"{table} successfully written to GeoPackage at {output_geopackage_path}")
        except Exception as e:
            QMessageBox.critical(self.dlg, "GeoPackage Error", str(e))

    def load_data_into_qgis(self, output_dir, save_as_shapefile, save_as_geopackage):
        table = self.dlg.lineEditTable.text()

        if save_as_shapefile:
            shapefile_path = os.path.join(output_dir, f"{table}.shp")
            
            # Check if the shapefile exists
            if os.path.exists(shapefile_path):
                # Define the layer name
                layer_name = f"{table} Geometry"

                # Remove existing layer with the same name if it exists
                existing_layers = QgsProject.instance().mapLayersByName(layer_name)
                for layer in existing_layers:
                    QgsProject.instance().removeMapLayer(layer.id())

                layer = QgsVectorLayer(shapefile_path, f"{table} Geometry", "ogr")
                if not layer.isValid():
                    QMessageBox.critical(self.dlg, "Loading Error", "Failed to load shapefile into QGIS.")
                else:
                    QgsProject.instance().addMapLayer(layer)
        
        # Load the CSV file as a table
        csv_path = os.path.join(output_dir, f"{table}_null.csv")
        if os.path.exists(csv_path):
            
            # Define the layer name
            layer_name = f"{table} No Geometry"
            existing_layers = QgsProject.instance().mapLayersByName(layer_name)
            for layer in existing_layers:
                QgsProject.instance().removeMapLayer(layer.id())

            csv_layer = QgsVectorLayer(f"file:///{csv_path}?delimiter=,", f"{table} No Geometry", "delimitedtext")
            if not csv_layer.isValid():
                QMessageBox.critical(self.dlg, "Loading Error", f"Failed to load {table} No Geometry into QGIS.")
            else:
                QgsProject.instance().addMapLayer(csv_layer)

        if save_as_geopackage:
            geopackage_path = os.path.join(output_dir, f"{table}.gpkg")
            layer = QgsVectorLayer(f"{geopackage_path}|layername={table}_points", f"{table} Geometry", "ogr")
            if not layer.isValid():
                QMessageBox.critical(self.dlg, "Loading Error", "Failed to load GeoPackage into QGIS.")
            else:
                QgsProject.instance().addMapLayer(layer)
            
            # Load the {table}_null_geom table (without geometry)
            null_layer = QgsVectorLayer(f"{geopackage_path}|layername={table}_null_geom", f"{table} No Geometry", "ogr")
            if null_layer.isValid():
                QgsProject.instance().addMapLayer(null_layer)
            else:
                QMessageBox.critical(self.dlg, "Loading Error", "Failed to load {table}_null_geom table into QGIS.")
