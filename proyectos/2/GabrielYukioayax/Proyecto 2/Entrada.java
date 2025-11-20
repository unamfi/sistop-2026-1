public class Entrada {

    public String nombre;
    public int clusterInicial;
    public int tamanoBytes;
    public String fechaCreacion;
    public String fechaModificacion;

    public Entrada(String n, int c, int t, String fc, String fm){
        this.nombre = n;
        this.clusterInicial = c;
        this.tamanoBytes = t;
        this.fechaCreacion = fc;
        this.fechaModificacion = fm;
    }

    public Entrada(){

    }

    public boolean esValido(){
        try {
            if(nombre.charAt(0) == '-'){
                return false;
            }
            return true;
        } catch(Exception e){
            return false;
        }
    }

    public String getDatos(){
        return "Archivo: " + nombre + " | Cluster: " + clusterInicial + " | Tam: " + tamanoBytes;
    }

    public void limpiarNombre(){
        try {
            this.nombre = this.nombre.trim();
        } catch(Exception e){
            
        }
    }

}