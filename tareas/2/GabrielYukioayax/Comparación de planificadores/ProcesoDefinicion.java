import java.util.Objects;

public class ProcesoDefinicion{
    public final String id;
    public final int llegada;
    public final int servicio;

    public ProcesoDefinicion(String id, int llegada, int servicio){
        this.id = Objects.requireNonNull(id);
        this.llegada = llegada;
        this.servicio = servicio;
    }

    @Override public String toString(){
        return id + ": " + llegada + ", t=" + servicio;
    }
}
