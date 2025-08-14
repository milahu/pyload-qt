https://chat.deepseek.com/a/chat/s/166b19ea-783b-4488-b07d-635c32f214cf

create a pyload qt interface in python.

use "pyside" as qt library.
use PySide.QtNetwork.QNetworkAccessManager as http client.

1. login:
you have to send your credentials username and password as POST parameter to http://localhost:8000/api/login.
the default username is "pyload".
the default password is "pyload".
the session id is stored in a cookie.

2. show the pyload download queue a table of packages.
columns: name, progress, size.
get the list of packages with
http://localhost:8000/api/getQueue
this returns a json list of objects like

```json
{
  "pid": 281,
  "name": "Helge K\u00f6nig - Ich bleib dann mal zu Hause (Ungek\u00fcrzt)",
  "linksdone": 1,
  "sizedone": 282899481,
  "sizetotal": 282899481,
  "linkstotal": 1
}
```

"pid" is the package id.

3. in the bottom half of the main window,
show the contents of the currently selected package.
get the package contents from
http://localhost:8000/api/getPackageData/12345
for the package id 12345.

the json response looks like

```json
{
  "pid": 12345,
  "name": "Helge K\u00f6nig - Ich bleib dann mal zu Hause (Ungek\u00fcrzt)",
  "links": [
    {
      "fid": 2436,
      "url": "https://rapidgator.net/file/4422d0c496ae113ca11819ffae939a1f",
      "name": "Helge_K\u00f6nig_-_Ich_bleib_dann_mal_zu_Hause_(Ungek\u00fcrzt).rar",
      "plugin": "RapidgatorNet",
      "size": 282899481,
      "format_size": "269.79 MiB",
      "status": 0,
      "statusmsg": "finished",
      "error": ""
    }
  ]
}
```

so the bottom half should show a table of package links.
in this example, there is only one link.
table columns: filename, statusmsg, error.

4. let me add a package:
let me enter the package name, and a free-form textarea for package links.
parse http links from the free-form text input into an array of links.
send a GET request to
http://localhost:8000/api/addPackage?name={name}&links={links}
the values are json-formatted strings like
http://pyload-core/api/addPackage?name="some_name"&links=["link1","link2"]

---

move the "add package" widget to a separate popup window, which can be opened by menubar -> file -> add package
