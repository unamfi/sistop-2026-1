import java.util.Scanner;
import java.io.File;

public class Main {

    public static void main(String[] args) {
        
        System.out.println("--- INICIANDO SISTEMA ---");
        
        GestorDisco g = new GestorDisco("fiunamfs.img");
        g.iniciar();
        
        Scanner teclado = new Scanner(System.in);
        boolean salir = false;
        
        while(!salir){
            System.out.println("\n\nSelecciona una opcion:");
            System.out.println("1. Listar archivos");
            System.out.println("2. Copiar archivo sacar");
            System.out.println("3. Copiar archivo meter");
            System.out.println("4. Eliminar");
            System.out.println("5. Salir");
            
            System.out.print("Opcion: ");
            int op = teclado.nextInt();
            
            if(op == 1){
                Thread t = new Thread(new Runnable(){
                    public void run(){
                        System.out.println("Leyendo disco...");
                        g.leerContenido();
                    }
                });
                t.start();
            } 
            else if(op == 2){
                System.out.println("Escribe el nombre del archivo:");
                String nombre = teclado.nextLine();
                // funcion copiar sacar
            }
            else if(op == 3){
                // funcion copiar meter
            }
            else if(op == 4){
                // funcion eliminar
            }
            else if(op == 5){
                salir = true;
                g.cerrar();
                System.out.println("Adios");
            }
            else {
                System.out.println("Opcion no valida");
            }
            
            try{
                Thread.sleep(500);
            } catch(Exception e){}
        }
    }
}