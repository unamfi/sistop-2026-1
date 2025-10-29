import java.util.*;

public class PlanificadorSPN implements Planificador{

    @Override public String nombre(){ return "SPN"; }

    @Override public ResultadoSimulacion simular(List<ProcesoDefinicion> defs){
        List<Proceso> ps = Utilidades.clonar(defs);
        List<Proceso> listos = new ArrayList<>();
        StringBuilder linea = new StringBuilder();
        int t=0; Proceso ejecutando=null;

        while(!Utilidades.todosTerminados(ps)){
            for(Proceso p: ps) if(p.llegada==t) listos.add(p);

            if(ejecutando==null && !listos.isEmpty()){
                listos.sort(Comparator.<Proceso>comparingInt(p -> p.servicio).thenComparing(Utilidades.porId()));
                ejecutando = listos.remove(0);
            }

            if(ejecutando==null){
                linea.append("-");
            }else{
                linea.append(ejecutando.id);
                ejecutando.restante -= 1;
            }

            t += 1;

            if(ejecutando!=null && ejecutando.restante==0){
                Utilidades.establecerFinalizado(ejecutando,t);
                ejecutando = null;
            }
        }
        return Utilidades.metricas(ps,linea.toString());
    }
}
