from PyQt5 import uic
from PyQt5.QtWidgets import QDialog
import os

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'forms/qgis_mariadb_plugin_dialog_base.ui'))


class QGISMariaDBPluginDialog(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        super(QGISMariaDBPluginDialog, self).__init__(parent)
        self.setupUi(self)
