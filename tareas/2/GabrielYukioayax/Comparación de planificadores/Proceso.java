public class Proceso{
    public final String id;
    public final int llegada;
    public final int servicio;
    public int restante;
    public Integer completado;
    
    public Proceso(ProcesoDefinicion d){
        this.id = d.id;
        this.llegada = d.llegada;
        this.servicio = d.servicio;
        this.restante = d.servicio;
        this.completado = null;
    }
}
