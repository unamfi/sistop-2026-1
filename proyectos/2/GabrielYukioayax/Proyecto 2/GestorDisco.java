import java.io.RandomAccessFile;
import java.io.File;
import java.io.FileNotFoundException;
import java.util.Scanner;
import java.io.IOException;
import java.io.FileOutputStream;
import java.io.FileInputStream;
public class GestorDisco {
    RandomAccessFile midisco;
    String rutaArchivo;
    public GestorDisco(String r){
        this.rutaArchivo = r;
    }
    public void iniciar(){
        try {
            File f = new File("fiunamfs.img");
            midisco = new RandomAccessFile(f, "rw");
            midisco.seek(0);
            byte[] buff = new byte[8];
            midisco.read(buff);
            String sist = new String(buff);
            System.out.println(sist);
            midisco.seek(10);
            byte[] ver = new byte[4];
            midisco.read(ver);
            String version = new String(ver);
            System.out.println(version);
            midisco.seek(20);
            byte[] et = new byte[16];
            midisco.read(et);
            String etiqueta = new String(et);
            System.out.println(etiqueta);
            midisco.seek(40);
            int tamCluster = midisco.readInt();
            System.out.println(tamCluster);
        } catch(Exception e){
            System.out.println("error al iniciar");
        }
    }
    public void leerContenido(){
        try {
            int inicioDir = 1024;
            midisco.seek(inicioDir);
            for(int i = 0; i < 10; i++){
                byte[] entrada = new byte[64];
                midisco.read(entrada);
                if(entrada[0] != 45){
                    Entrada e = new Entrada(entrada);
                    System.out.println(e.getDatos());
                }
            }
        } catch(Exception e){
            e.printStackTrace();
        }
    }
    public void sacarArchivo(String nombre){
        try {
            midisco.seek(1024);
            for(int i = 0; i < 64; i++){
                byte[] b = new byte[64];
                midisco.read(b);
                if(b[0] != 45){
                    Entrada e = new Entrada(b);
                    if(e.nombre.trim().equals(nombre)){
                        int offset = e.clusterInicial * 1024; 
                        midisco.seek(offset);
                        byte[] data = new byte[e.tamanoBytes];
                        midisco.read(data);
                        FileOutputStream fos = new FileOutputStream(nombre);
                        fos.write(data);
                        fos.close();
                        System.out.println("archivo guardado");
                        return;
                    }
                }
            }
            System.out.println("no encontrado");
        } catch(Exception e){
            System.out.println("error sacar");
        }
    }
    public void meterArchivo(String ruta){
        try {
            File f = new File(ruta);
            FileInputStream fis = new FileInputStream(f);
            byte[] datos = new byte[(int)f.length()];
            fis.read(datos);
            fis.close();
            midisco.seek(1024);
            for(int i = 0; i < 64; i++){
                long p = midisco.getFilePointer();
                byte[] b = new byte[64];
                midisco.read(b);
                if(b[0] == 45){
                    midisco.seek(p);
                    midisco.writeByte(46);
                    midisco.write(f.getName().getBytes());
                    midisco.seek(p + 16);
                    midisco.writeInt(5);
                    midisco.seek(p + 20);
                    midisco.writeInt((int)f.length());
                    midisco.seek(5 * 1024);
                    midisco.write(datos);
                    System.out.println("guardado en cluster 5");
                    return;
                }
            }
        } catch(Exception e){
            System.out.println("error meter");
        }
    }
    public void eliminarArchivo(String nombre){
        try {
            midisco.seek(1024);
            for(int i = 0; i < 64; i++){
                long p = midisco.getFilePointer();
                byte[] b = new byte[64];
                midisco.read(b);
                if(b[0] != 45){
                    Entrada e = new Entrada(b);
                    if(e.nombre.trim().equals(nombre)){
                        midisco.seek(p);
                        midisco.writeByte(45);
                        System.out.println("eliminado");
                        return;
                    }
                }
            }
            System.out.println("no existe");
        } catch(Exception e){
        }
    }
    public void cerrar(){
        try {
            midisco.close();
        } catch(Exception e){
        }
    }
}