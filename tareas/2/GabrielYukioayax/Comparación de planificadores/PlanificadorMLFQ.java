import java.util.*;
import java.util.stream.Collectors;

public class PlanificadorMLFQ implements Planificador{

    public static final class Config{
        public final int[] quanta;
        public final boolean preemptOnHigherLevelArrival;
        public final int agingTicks;

        public Config(int[] quanta, boolean preemptOnHigherLevelArrival, int agingTicks){
            if(quanta==null || quanta.length==0) throw new IllegalArgumentException("MLFQ: al menos un nivel");
            this.quanta = Arrays.copyOf(quanta, quanta.length);
            this.preemptOnHigherLevelArrival = preemptOnHigherLevelArrival;
            this.agingTicks = Math.max(0, agingTicks);
        }
    }

    private final Config cfg;

    public PlanificadorMLFQ(Config cfg){ this.cfg = cfg; }

    @Override public String nombre(){
        String qs = Arrays.stream(cfg.quanta).mapToObj(q -> q<0? "∞" : String.valueOf(q)).collect(Collectors.joining(","));
        return "MLFQ[q="+qs+";aging="+cfg.agingTicks+";preempt="+(cfg.preemptOnHigherLevelArrival?"on":"off")+"]";
    }

    @Override public ResultadoSimulacion simular(List<ProcesoDefinicion> defs){
        List<Proceso> ps = Utilidades.clonar(defs);
        @SuppressWarnings("unchecked")
        Deque<Proceso>[] colas = new Deque[cfg.quanta.length];
        for(int i=0;i<colas.length;i++) colas[i] = new ArrayDeque<>();
        Map<Proceso,Integer> espera = new IdentityHashMap<>();

        StringBuilder linea = new StringBuilder();
        int t=0; Proceso ejecutando=null; int nivel=-1; int qRestante=0; boolean qInf=false;

        while(!Utilidades.todosTerminados(ps)){

            Utilidades.encolarLlegadas(ps,t, colas[0]);
            for(Deque<Proceso> q: colas) for(Proceso p: q) espera.putIfAbsent(p,0);


            if(cfg.agingTicks>0){
                for(int lv=1; lv<colas.length; lv++){
                    if(colas[lv].isEmpty()) continue;
                    Deque<Proceso> nueva = new ArrayDeque<>();
                    while(!colas[lv].isEmpty()){
                        Proceso p = colas[lv].pollFirst();
                        int w = espera.getOrDefault(p,0);
                        if(w >= cfg.agingTicks){ espera.put(p,0); colas[lv-1].addLast(p); }
                        else nueva.addLast(p);
                    }
                    colas[lv] = nueva;
                }
            }

  
            if(ejecutando==null){
                for(int lv=0; lv<colas.length; lv++){
                    if(!colas[lv].isEmpty()){
                        ejecutando = colas[lv].pollFirst();
                        nivel = lv;
                        int q = cfg.quanta[nivel];
                        qInf = (q<0); qRestante = qInf? Integer.MAX_VALUE : q;
                        espera.remove(ejecutando);
                        break;
                    }
                }
            }


            
            if(ejecutando==null){ linea.append("-"); }
            else { linea.append(ejecutando.id); ejecutando.restante -= 1; if(!qInf) qRestante -= 1; }

            for(Deque<Proceso> q: colas) for(Proceso p: q) espera.put(p, espera.getOrDefault(p,0)+1);

            t += 1;

            boolean termino = (ejecutando!=null && ejecutando.restante==0);
            if(termino) Utilidades.establecerFinalizado(ejecutando,t);

            boolean hayMayor = false;
            if(cfg.preemptOnHigherLevelArrival && ejecutando!=null){
                for(int lv=0; lv<nivel; lv++){ if(!colas[lv].isEmpty()){ hayMayor=true; break; } }
            }

            if(ejecutando!=null){
                if(termino){
                    ejecutando=null; nivel=-1;
                }else if(hayMayor){
                    colas[nivel].addLast(ejecutando); espera.put(ejecutando,0); ejecutando=null; nivel=-1;
                }else if(!qInf && qRestante==0){
                    int dest = Math.min(nivel+1, colas.length-1);
                    colas[dest].addLast(ejecutando); espera.put(ejecutando,0); ejecutando=null; nivel=-1;
                }
            }
        }
        return Utilidades.metricas(ps, linea.toString());
    }
}
