<h1>QGIS MariaDB Plugin</h1>
This plugin allows users to connect to a MariaDB database, select spatial data, and export it as Shapefiles or GeoPackages. It simplifies the workflow of transferring data from MariaDB into QGIS for further analysis and visualization. With support for various data formats, users can easily integrate their database information into their QGIS projects. <br> <br>

<b> Solution to initial install Error for no python models in QGIS. Specifically for mariadb.</b> <br>
<p><i>Example "No Module called mariadb" </i> </p>

Open QGIS Python console (under Plugins » Python Console) and type:
```{python}
import pip
pip.main(['install', 'my-package-name'])
```
