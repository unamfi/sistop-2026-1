import java.util.*;

public class PlanificadorRR implements Planificador{
    private final int quantum;
    public PlanificadorRR(int quantum){ this.quantum = quantum; }

    @Override public String nombre(){ return "RR"+quantum; }

    @Override public ResultadoSimulacion simular(List<ProcesoDefinicion> defs){
        List<Proceso> ps = Utilidades.clonar(defs);
        Deque<Proceso> listos = new ArrayDeque<>();
        StringBuilder linea = new StringBuilder();
        int t=0; Proceso ejecutando=null; int qRestante=0;

        while(!Utilidades.todosTerminados(ps)){
            Utilidades.encolarLlegadas(ps,t,listos);

            if(ejecutando==null){ ejecutando = listos.pollFirst(); qRestante = quantum; }

            if(ejecutando==null){
                linea.append("-");
            }else{
                linea.append(ejecutando.id);
                ejecutando.restante -= 1;
                qRestante -= 1;
            }

            t += 1;

            if(ejecutando!=null && ejecutando.restante==0){
                Utilidades.establecerFinalizado(ejecutando,t);
                ejecutando = null;
            }else if(ejecutando!=null && qRestante==0){
                listos.addLast(ejecutando);
                ejecutando = null;
            }
        }
        return Utilidades.metricas(ps,linea.toString());
    }
}
