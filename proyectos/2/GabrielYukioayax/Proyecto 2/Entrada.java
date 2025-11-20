public class Entrada{
    public String nombre;
    public int clusterInicial;
    public int tamanoBytes;
    public String fechaCreacion;
    public String fechaModificacion;
    public Entrada(byte[] datos){
        byte[] n = new byte[14];
        for(int i = 0; i < 14; i++) {
            n[i] = datos[i + 1];
        }
        this.nombre = new String(n);
        this.clusterInicial = (datos[16] & 0xFF) | ((datos[17] & 0xFF) << 8) | ((datos[18] & 0xFF) << 16) | ((datos[19] & 0xFF) << 24);
        this.tamanoBytes = (datos[20] & 0xFF) | ((datos[21] & 0xFF) << 8) | ((datos[22] & 0xFF) << 16) | ((datos[23] & 0xFF) << 24);   
        this.fechaCreacion = "";
        this.fechaModificacion = "";
    }
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
            if(nombre.charAt(0) == '-' || nombre.charAt(0) == 45) {
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
            String s = this.nombre.replace((char)0, ' ');
            this.nombre = s.trim();
        } catch(Exception e) {
        }
    }
}