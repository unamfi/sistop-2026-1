public class Entrada{
    public String nombre;
    public int clusterInicial;
    public int tamanoBytes;
    //Constructor que convierte los 64 bytes en informacion util
    public Entrada(byte[] datos){
        //Extraemos el nombre
        byte[] n = new byte[14];
        for(int i = 0; i < 14; i++){
            n[i] = datos[i + 1];
        }
        //Convertimos a String y limpiamos basura
        this.nombre = new String(n);
        //Convertimos los bytes de Little Endian a Entero normal
        this.clusterInicial = (datos[16] & 0xFF) | 
                              ((datos[17] & 0xFF) << 8) | 
                              ((datos[18] & 0xFF) << 16) | 
                              ((datos[19] & 0xFF) << 24);   
        this.tamanoBytes = (datos[20] & 0xFF) | 
                           ((datos[21] & 0xFF) << 8) | 
                           ((datos[22] & 0xFF) << 16) | 
                           ((datos[23] & 0xFF) << 24);
    }
    // Verifica si la entrada es un archivo valido
    public boolean esValido(){
        try {
            if(nombre.charAt(0) == 45 || nombre.charAt(0) == 0){
                return false;
            }
            return true;
        } catch(Exception e){
            return false;
        }
    }
    //Formato para imprimir en lista
    public String getDatos(){
        return String.format("Archivo: %-15s | Peso: %-8d bytes", getNombreLimpio(), tamanoBytes);
    }
    //Quita los espacios nulos que ensucian el nombre
    public String getNombreLimpio(){
        try{
            String s = this.nombre.replace((char)0, ' ');
            return s.trim();
        } catch(Exception e){
            return "Desconocido";
        }
    }
}