import java.util.List;

public interface Planificador{
    ResultadoSimulacion simular(List<ProcesoDefinicion> definiciones);
    String nombre();
}
