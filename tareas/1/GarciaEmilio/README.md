------------------------------- El Elevador -------------------------------
En esta tarea voy a resolver el ejercicio del el elevador con python.
    
    El problema que decidieron resolver
El de el elevador
    
    El lenguaje y entorno en que lo desarrollaron.
Mi version de python es 3.12.3 y use las bibliotecas mismas que usted entonces no necesita instalar algo mas solo ejecutarlo
    La estrategia de sincronización (mecanismo / patrón) que emplearon para lograrlo
Utilize el multiplex. Mi decision fue pq el elevador es un recurso limitado compartido haciendo el multiplex una opcion natural para el problema. 
Para usarlo se le asigno al semaphoro el limite de 5 entonces cuando estos 5 lugares se acaben las threads de los usuarios tendran que esperar. La region critica basicamente son mis vars globales ya que el thread del elevador y de los usuarios estan interactuando con ellos. 
    Si están implementando alguno de los refinamientos
Si. El problema es que usuarios se creen constantemente entre dos pisos y monopolizen el elevador. Mi soliucion fue inspirarme en los elevadores viejos, haciendo que el elevador este en un loop constante de ir arriba y abajo. De esta forma las veces que estan en cada piso es igual. Podria mejorar esto con un algoritmo que controle el comportamiento del elevador o un contador por piso para andar checando que no se monopolize pero mi solucion fue la mas sencilla.
    Cualquier duda que tengan. Si notan que algún pedazo de la implementación podría mejorar, si algo no les terminó de quedar bien
Si pudiera resolver este ejercicio en clase se lo agradeceria. Me costo crear el thread del elevador y usuario y no se muy bien si quedaron bien. 

