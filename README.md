<h1>QGIS MariaDB Plugin</h1>
<b> Solution to initial install Error for no python models in QGIS. Specifically for mariadb.</b> <br><br>
<i></i>Example "No Module called mariadb" </i> <br>

Open QGIS Python console (under Plugins » Python Console) and type:


```{python}
import pip
pip.main(['install', 'my-package-name'])
```
