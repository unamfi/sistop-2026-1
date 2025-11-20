import java.io.RandomAccessFile;
import java.io.File;
import java.io.FileNotFoundException;
import java.util.Scanner;
import java.io.IOException;


public class GestorDisco {
    RandomAccessFile  midisco;
    String  rutaArchivo;


    public GestorDisco( String r ){
        
        this.rutaArchivo = r;
        
    }


    public void iniciar(){
        try {
            
            File f = new File( "fiunamfs.img" );
            
            midisco = new RandomAccessFile( f , "rw" );
            
            
            midisco.seek( 0 );
            
            byte[] buff = new byte[ 8 ];
            midisco.read( buff );
            
            String sist = new String( buff );
            System.out.println( sist );


            midisco.seek( 10 );
            byte[] ver = new byte[ 4 ];
            midisco.read( ver );
            
            String version = new String( ver );
            System.out.println( version );


            midisco.seek( 20 );
            
            byte[] et = new byte[ 16 ];
            midisco.read( et );
            
            String etiqueta = new String( et );
            System.out.println( etiqueta );


            midisco.seek( 40 );
            
            int tamCluster = midisco.readInt();
            
            System.out.println( tamCluster );


        } catch(Exception e){
            System.out.println( "error al iniciar" );
        }
    }


    public void leerContenido(){
        try {
            
            int inicioDir = 1024;
            
            midisco.seek( inicioDir );


            for( int i = 0; i < 10; i++ ){
                
                byte[] entrada = new byte[ 64 ];
                
                midisco.read( entrada );
                
                
                if( entrada[0] != 45 ){
                    
                    byte[] name = new byte[ 14 ];
                    
                    for( int j = 0; j < 14; j++ ){
                        
                        name[j] = entrada[ j + 1 ];
                        
                    }
                    
                    String nombreArchivo = new String( name );
                    System.out.println( nombreArchivo );


                    int clusInit = entrada[ 16 ];
                    System.out.println( clusInit );
                    
                    int size = entrada[ 20 ];
                    System.out.println( size );
                    
                }
                
            }


        } catch(Exception e){
            e.printStackTrace();
        }
    }


    public void cerrar(){
        try {
            
            midisco.close();
            
        } catch(Exception e){
            
        }
    }

}