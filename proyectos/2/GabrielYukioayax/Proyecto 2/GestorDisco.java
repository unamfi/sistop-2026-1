import java.io.*;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
public class GestorDisco{
    RandomAccessFile midisco;
    String rutaArchivo;
    int tamanoCluster;
    public GestorDisco(String r){
        this.rutaArchivo = r;
    }
    public boolean iniciar(){
        try{
            File f = new File(rutaArchivo);
            if(!f.exists()) return false; 
            midisco = new RandomAccessFile(f, "rw");
            //Leemos el tamaño del cluster del Superbloque
            midisco.seek(40);
            byte[] b = new byte[4];
            midisco.read(b);
            //Correccion Little Endian
            tamanoCluster = ByteBuffer.wrap(b).order(ByteOrder.LITTLE_ENDIAN).getInt();
            return true;
        } catch(Exception e){
            return false;
        }
    }
    public void leerContenido(){
        try{
            //El directorio siempre esta despues del superbloque
            int inicioDir = tamanoCluster * 1;
            midisco.seek(inicioDir);
            //Leemos varias entradas
            for(int i = 0; i < 64; i++){
                byte[] entrada = new byte[64];
                midisco.read(entrada);
                //Si el primer byte no es guion ni cero, es un archivo valido
                if(entrada[0] != 45 && entrada[0] != 0){
                    Entrada e = new Entrada(entrada);
                    //Imprimimos usando el formato limpio de la clase Entrada
                    System.out.println(e.getDatos());
                }
            }
        } catch(Exception e){
            e.printStackTrace();
        }
    }
    public String sacarArchivo(String nombre){
        try{
            midisco.seek(tamanoCluster); // Inicio directorio
            for(int i = 0; i < 64; i++){
                byte[] b = new byte[64];
                midisco.read(b);
                if(b[0] != 45 && b[0] != 0){
                    Entrada e = new Entrada(b);
                    //Comparamos nombres
                    if(e.getNombreLimpio().equals(nombre)){
                        //Calculamos la posicion exacta
                        int offset = e.clusterInicial * tamanoCluster;
                        midisco.seek(offset);
                        byte[] data = new byte[e.tamanoBytes];
                        midisco.read(data);
                        // Escribimos el archivo en la PC
                        FileOutputStream fos = new FileOutputStream(nombre);
                        fos.write(data);
                        fos.close();
                        return "Exito: Archivo descargado correctamente";
                    }
                }
            }
            return "Error: Archivo no encontrado";
        } catch(Exception e) {
            return "Error critico al sacar archivo";
        }
    }
    public String meterArchivo(String ruta) {
        try {
            File f = new File(ruta);
            if(!f.exists()) return "Error: El archivo origen no existe";
            //Leemos el archivo de la PC a memoria
            FileInputStream fis = new FileInputStream(f);
            byte[] datos = new byte[(int)f.length()];
            fis.read(datos);
            fis.close();
            //Buscar hueco en el directorio
            midisco.seek(tamanoCluster);
            long posicionDirectorio = -1;
            int ultimoClusterOcupado = 4; //Los datos empiezan en el cluster 5
            for(int i = 0; i < 64; i++){
                long p = midisco.getFilePointer();
                byte[] b = new byte[64];
                midisco.read(b);
                //Si es un archivo valido vemos donde termina para no sobrescribirlo
                if(b[0] != 45 && b[0] != 0) {
                    Entrada e = new Entrada(b);
                    //Calculamos cuantos clusters ocupa este archivo
                    int clustersUsados = (int)Math.ceil((double)e.tamanoBytes / tamanoCluster);
                    int finArchivo = e.clusterInicial + clustersUsados;
                    if(finArchivo > ultimoClusterOcupado) {
                        ultimoClusterOcupado = finArchivo;
                    }
                } 
                //Si encontramos un hueco vacio y aun no tenemos donde guardar
                else if(posicionDirectorio == -1) {
                    posicionDirectorio = p;
                }
            }
            if(posicionDirectorio != -1){
                //El nuevo archivo ira despues del ultimo ocupado
                int clusterDestino = ultimoClusterOcupado + 1; 
                midisco.seek(posicionDirectorio);
                midisco.writeByte(46);
                //Preparamos nombre
                byte[] nombreBytes = new byte[14];
                byte[] nombreOriginal = f.getName().getBytes();
                for(int k=0; k<14; k++) {
                    if(k < nombreOriginal.length) nombreBytes[k] = nombreOriginal[k];
                    else nombreBytes[k] = 0; //Rellenar con nulos
                }
                midisco.write(nombreBytes);
                //Escribimos direccion y tamano
                midisco.seek(posicionDirectorio + 16);
                ByteBuffer bb = ByteBuffer.allocate(8).order(ByteOrder.LITTLE_ENDIAN);
                bb.putInt(clusterDestino);
                bb.putInt((int)f.length());
                midisco.write(bb.array());
                //Escribimos los datos reales
                midisco.seek(clusterDestino * tamanoCluster);
                midisco.write(datos);
                return "Exito: Guardado en cluster " + clusterDestino;
            }
            return "Error: Directorio lleno";
        } catch(Exception e){
            return "Error al intentar guardar";
        }
    }
    public String eliminarArchivo(String nombre){
        try{
            midisco.seek(tamanoCluster);
            for(int i = 0; i < 64; i++){
                long p = midisco.getFilePointer();
                byte[] b = new byte[64];
                midisco.read(b);
                if(b[0] != 45 && b[0] != 0){
                    Entrada e = new Entrada(b);
                    if(e.getNombreLimpio().equals(nombre)){
                        midisco.seek(p);
                        midisco.writeByte(45); 
                        return "Archivo eliminado";
                    }
                }
            }
            return "Error: No se encontro el archivo";
        } catch(Exception e) {
            return "Error al eliminar";
        }
    }
    public void cerrar(){
        try{ 
            midisco.close(); 
        } catch(Exception e){
        }
    }
}