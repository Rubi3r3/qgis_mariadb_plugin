"""
Initializes the plugin, making it known to QGIS.
"""

def classFactory(iface):
    from .qgis_mariadb_plugin import QGISMariaDBPlugin
    return QGISMariaDBPlugin(iface)