import java.util.*;

public class PlanificadorFCFS implements Planificador{

    @Override public String nombre(){ return "FCFS"; }

    @Override public ResultadoSimulacion simular(List<ProcesoDefinicion> defs){
        List<Proceso> ps = Utilidades.clonar(defs);
        Deque<Proceso> listos = new ArrayDeque<>();
        StringBuilder linea = new StringBuilder();
        int t=0; Proceso ejecutando=null;

        while(!Utilidades.todosTerminados(ps)){
            Utilidades.encolarLlegadas(ps,t,listos);

            if(ejecutando==null) ejecutando = listos.pollFirst();

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
