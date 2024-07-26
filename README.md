<h1>QGIS MariaDB Plugin</h1>
<h2> Solution to Initial Install Error for no models in QGIS</h2>
Example "No Module called mariadb" <br> <br>

Open QGIS Python console (under Plugins » Python Console) and type:


```{python}
import pip
pip.main(['install', 'my-package-name'])
```
