<h1>QGIS MariaDB Plugin</h1>
<b> Solution to Initial Install Error for no models in QGIS</b>
Example "No Module called mariadb" <br>

Open QGIS Python console (under Plugins » Python Console) and type:


```{python}
import pip
pip.main(['install', 'my-package-name'])
```
