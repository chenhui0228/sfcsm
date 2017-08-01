**SfcsmCtrl** is the  server part for **sfcsmAdm** and **sfcsmViz**

At this stage, we use **MongoJuice** which provide a rest-api to read a mongoDb. A more specific server will be written later.

MongoJuice can run in a flask stand alone server or inside a apache server through wsgi

It provides 3 methods:

- *GET host/\<db-name\>/\<collection-name\>?depth=X*

    that returns a json format of all the object inside the given collection. Param *depth* is used to dig inside DBRef and embed the reference object directly inside the response


- *POST host/\<db-name\>/\<collection-name\>?depth=X*

    the body should contains a JSON that is used by the find function of pymongo as "spec" (see [pymongo](http://api.mongodb.org/python/current) docs)

- *POST host/\<db-name\>*

    the body should contains a JSON that is used to execute multiple request to pymongo. The embedded JSON describes the template of the expected response and the commands to execute to fill each field of this template: *{key : \<command\> (, key : \<command\>)\*}*

